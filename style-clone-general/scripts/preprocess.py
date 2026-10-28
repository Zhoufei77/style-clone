#!/usr/bin/env python3
"""Conservative local corpus preparation. Python 3.9+, standard library only."""

from __future__ import annotations

import argparse
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys


EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm", ".srt", ".vtt"}
MODES = ("auto", "transcript", "markdown", "html", "plain")
REPORT_MARKER = "<!-- style-clone-general:metrics-report -->"
STAMP = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?"
CUE_RE = re.compile(r"^\s*" + STAMP + r"\s*-->\s*" + STAMP + r"(?:\s+.*)?$")
SPEAKER_RE = re.compile(r"^\s*(?:说话人\s*\d+|Speaker\s+\d+)\s*[:：]?\s*[\[(（]?" + STAMP + r"[\])）]?\s*[:：]?\s*", re.I)
PREFIX_STAMP_RE = re.compile(r"^\s*(?:[\[(（]" + STAMP + r"[\])）]\s*|" + STAMP + r"\s+)")


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def collect_paths(inputs, excluded=()) -> list[Path]:
    """Traverse only explicitly supplied roots; skip hidden paths and symlinks."""
    exclusions = [Path(value).resolve() for value in excluded]
    found = {}

    def omit(path: Path) -> bool:
        return path.is_symlink() or path.name.startswith(".") or any(inside(path, root) for root in exclusions)

    for value in inputs:
        root = Path(value).absolute()
        if not root.exists() or root.is_symlink() or root.name.startswith("."):
            raise ValueError("输入不存在，或是隐藏路径、符号链接。")
        if root.is_file():
            if root.suffix.lower() not in EXTENSIONS:
                raise ValueError("不支持的文件类型。支持 TXT、Markdown、HTML、SRT、VTT。")
            if not omit(root):
                found[str(root.resolve())] = root
        elif root.is_dir():
            if omit(root):
                continue
            for folder, directories, names in os.walk(root, followlinks=False):
                base = Path(folder)
                directories[:] = sorted(name for name in directories if not omit(base / name))
                for name in sorted(names):
                    candidate = base / name
                    if candidate.suffix.lower() in EXTENSIONS and not omit(candidate):
                        found[str(candidate.resolve())] = candidate
        else:
            raise ValueError("输入必须是普通文件或目录。")
    return sorted(found.values(), key=lambda path: str(path.resolve()))


def read_utf8(path: Path) -> str:
    text = path.read_bytes().decode("utf-8-sig")
    if any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise ValueError("输入含不支持的控制字符，请提供 UTF-8 文本。")
    return text.replace("\r\n", "\n").replace("\r", "\n")


class VisibleHTML(HTMLParser):
    BLOCKS = {"p", "div", "article", "section", "main", "header", "footer", "li", "ul", "ol", "blockquote", "pre", "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
    HIDDEN = {"script", "style", "head", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden.append(tag)
        if self.hidden:
            return
        if tag in self.BLOCKS:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.HIDDEN:
            if tag in self.hidden:
                self.hidden = self.hidden[:len(self.hidden) - self.hidden[::-1].index(tag) - 1]
            return
        if not self.hidden and tag in self.BLOCKS:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def tidy(text: str) -> str:
    lines = [line.strip() for line in text.replace("\xa0", " ").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def clean_html(text: str) -> str:
    parser = VisibleHTML()
    parser.feed(text)
    parser.close()
    return tidy("".join(parser.parts))


def clean_markdown(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        closing = next((index for index in range(1, len(lines)) if lines[index].strip() in {"---", "..."}), None)
        if closing is not None:
            lines = lines[closing + 1:]
    output = []
    fence = None
    for line in lines:
        if fence is not None:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*", line):
                fence = None
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
            fence = (opening.group(1)[0], len(opening.group(1)))
            continue
        if re.match(r"^ {0,3}\[[^\]]+\]:\s*\S", line) or re.fullmatch(r"\s*(?:[-*_]\s*){3,}|\s*=+\s*", line):
            continue
        line = re.sub(r"^\s{0,3}(?:>\s*)+", "", line)
        line = re.sub(r"^\s{0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$", r"\1", line)
        line = re.sub(r"^\s*(?:[-+*]\s+|\d+[.)]\s+)", "", line)
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"(`+)(.+?)\1", r"\2", line)
        line = re.sub(r"(\*\*|__)(.+?)\1", r"\2", line)
        line = re.sub(r"(?<!\w)([*_])([^*_]+)\1(?!\w)", r"\2", line)
        output.append(line)
    return tidy("\n".join(output))


def clean_transcript(text: str) -> str:
    lines = text.splitlines()
    output = []
    subtitle = any(CUE_RE.match(line) for line in lines)
    in_vtt_metadata = False
    for index, line in enumerate(lines):
        value = line.strip()
        if in_vtt_metadata:
            if not value:
                in_vtt_metadata = False
            continue
        if subtitle and re.match(r"^(?:NOTE(?:\s|$)|STYLE$|REGION$)", value):
            in_vtt_metadata = True
            continue
        if subtitle and (value.startswith("WEBVTT") or re.match(r"^(?:Kind|Language):", value)):
            continue
        if CUE_RE.match(value):
            continue
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if CUE_RE.match(next_line) and (value.isdigit() or index == 0 or not lines[index - 1].strip()):
            continue
        if value in {"文字记录", "转录结果", "关键词", "关键词：", "关键词:", "关键字", "关键字：", "关键字:"}:
            continue
        if not value:
            if not subtitle:
                output.append("")
            continue
        stripped = SPEAKER_RE.sub("", value)
        if stripped != value:
            if output and output[-1]:
                output.append("")
            value = stripped
        else:
            value = PREFIX_STAMP_RE.sub("", value)
        if not value:
            continue
        value = re.sub(r"<" + STAMP + r">", "", value)
        value = re.sub(r"</?(?:c(?:\.[^ >]+)?|v(?:\s+[^>]+)?|lang(?:\s+[^>]+)?|b|i|u|ruby|rt)>", "", value)
        if subtitle:
            value = unescape(value)
        output.append(value)
    # Strip Markdown scaffolding, retaining all visible headings and quotations.
    return clean_markdown("\n".join(output))


def choose_mode(text: str, path: Path, mode: str = "auto") -> str:
    if mode != "auto":
        return mode
    suffix = path.suffix.lower()
    if suffix in {".srt", ".vtt"}:
        return "transcript"
    if suffix in {".html", ".htm"} or re.search(r"<(?:!doctype|html|body|p|article|div)\b", text[:3000], re.I):
        return "html"
    if any(CUE_RE.match(line) or SPEAKER_RE.match(line) for line in text.splitlines()) or sum(bool(PREFIX_STAMP_RE.match(line)) for line in text.splitlines()) >= 2:
        return "transcript"
    if suffix in {".md", ".markdown"} or re.search(r"^ {0,3}#{1,6}\s", text, re.M):
        return "markdown"
    return "plain"


def clean_text(text: str, mode: str) -> str:
    if mode == "html":
        return clean_html(text)
    if mode == "markdown":
        return clean_markdown(text)
    if mode == "transcript":
        return clean_transcript(text)
    return text.strip()


def prepare(inputs, out: Path, mode="auto", speech_units=False, overwrite=False) -> dict:
    if out.is_symlink() or (out.exists() and not out.is_dir()):
        raise ValueError("输出必须是普通目录，不能是符号链接。")
    paths = collect_paths(inputs, (out,))
    if not paths:
        raise ValueError("没有找到可处理的输入文件。")
    records, contents = [], []
    source_paths = {path.resolve() for path in paths}
    for index, path in enumerate(paths, 1):
        raw = read_utf8(path)
        if raw.lstrip().startswith(REPORT_MARKER):
            continue
        selected = choose_mode(raw, path, mode)
        cleaned = clean_text(raw, selected)
        if speech_units:
            cleaned = re.sub(r"[，；：！？]+", "。", cleaned)
        if not cleaned.strip():
            raise ValueError("某个输入清理后没有正文；未写出结果。")
        name = f"D{index:03d}.txt"
        target = out / name
        if target.resolve() in source_paths or target.is_symlink():
            raise ValueError("输出与源文件冲突，或目标是符号链接。")
        if target.exists() and not overwrite:
            raise ValueError("输出文件已存在；请换目录或显式使用 --overwrite。")
        records.append({
            "label": f"D{index:03d}", "source_name": path.name, "output": name, "mode": selected,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256((cleaned + "\n").encode("utf-8")).hexdigest(),
        })
        contents.append((target, cleaned + "\n"))
    if not contents:
        raise ValueError("输入中只有本工具报告，没有语料正文。")
    manifest_path = out / "preprocess-manifest.json"
    if manifest_path.is_symlink() or (manifest_path.exists() and not overwrite):
        raise ValueError("预处理清单已存在；请换目录或显式使用 --overwrite。")
    manifest = {
        "schema_version": "1.0", "documents": records,
        "punctuation": "speech_units" if speech_units else "original",
        "normalization": "Chinese ，；：！？ to 。" if speech_units else "No sentence punctuation normalization",
        "notes": "换行统一为 LF；字幕换行不代表作者自然段；关键词等歧义正文保留。",
    }
    out.mkdir(parents=True, exist_ok=True)
    for target, content in contents:
        with target.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    with manifest_path.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return manifest


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="本地语料预处理；默认保留原文标点，不改源文件。")
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--mode", choices=MODES, default="auto")
    parser.add_argument("--speech-units", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.inputs, args.out, args.mode, args.speech_units, args.overwrite)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"预处理失败：{error}", file=sys.stderr)
        return 2
    print(f"已处理 {len(result['documents'])} 篇；标点口径：{result['punctuation']}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
