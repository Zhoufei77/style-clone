#!/usr/bin/env python3
"""Descriptive, local corpus statistics; no identity or quality assessment."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import statistics
import sys

from preprocess import REPORT_MARKER, VisibleHTML, choose_mode, clean_text, collect_paths, configure_console, read_utf8


SCHEMA_VERSION = "1.0"
SCOPE = "descriptive_corpus_statistics"
UNITS_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ebefA-Za-z0-9]")
PARTICLES = "啊吧呢吗嘛呗啦咯哈哟喔噢咧"
TRANSITIONS = ("值得注意的是", "总而言之", "综上所述", "与此同时", "除此之外", "不仅如此", "但是", "然而", "因此", "不过", "所以", "于是", "结果", "后来", "此外", "同时", "首先", "其次", "最后", "而且", "再说", "其实")
SURFACE_FORMS = ("的存在", "进行了", "使得", "得以")
PUNCTUATION = "，。！？；：、,.!?;:—–（）()“”「」『』…"
PATTERNS = {
    "not_but": re.compile(r"不是[^。！？!?\n]{1,60}?而是"),
    "three_item_enumeration": re.compile(r"[^，。！？!?、\n]{1,20}、[^，。！？!?、\n]{1,20}、[^，。！？!?、\n]{1,20}"),
    "both_and": re.compile(r"既[^。！？!?\n]{1,40}?又"),
}
SENT_SPLIT = re.compile(r"[。！？!?]+|…{2,}|(?<!\d)\.(?!\d)|\n\s*\n")


def units(value: str) -> int:
    return len(UNITS_RE.findall(value))


def ratio(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def distribution(values: list[int], paragraph=False) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0, "min": None, "max": None, "mean": None, "median": None,
                "p10": None, "p25": None, "p75": None, "p90": None, "cv_population": None,
                "histogram": {}}

    def percentile(fraction):
        position = (len(ordered) - 1) * fraction
        lower, upper = math.floor(position), math.ceil(position)
        return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 6)

    mean = statistics.mean(ordered)
    bins = (("1-40", 1, 40), ("41-100", 41, 100), ("101-200", 101, 200), ("201+", 201, math.inf)) if paragraph else (("1-8", 1, 8), ("9-15", 9, 15), ("16-29", 16, 29), ("30-49", 30, 49), ("50+", 50, math.inf))
    return {
        "n": len(ordered), "min": ordered[0], "max": ordered[-1], "mean": round(mean, 6),
        "median": statistics.median(ordered), "p10": percentile(.10), "p25": percentile(.25),
        "p75": percentile(.75), "p90": percentile(.90),
        "cv_population": round(statistics.pstdev(ordered) / mean, 6) if mean else None,
        "histogram": {label: sum(low <= value <= high for value in ordered) for label, low, high in bins},
    }


class HTMLLayout(VisibleHTML):
    def __init__(self):
        super().__init__()
        self.counts = Counter()

    def handle_starttag(self, tag, attrs):
        hidden = bool(self.hidden) or tag in self.HIDDEN
        if not hidden:
            if tag in {"b", "strong"}:
                self.counts["html_bold"] += 1
            if tag == "img":
                self.counts["images"] += 1
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                self.counts["headings"] += 1
            if tag == "blockquote":
                self.counts["quote_blocks"] += 1
            if tag == "li":
                self.counts["list_items"] += 1
        super().handle_starttag(tag, attrs)


def layout(raw: str, mode: str) -> dict:
    result = {"markdown_bold": 0, "html_bold": 0, "headings": 0, "images": 0,
              "quote_blocks": 0, "list_items": 0, "nonempty_lines": sum(bool(line.strip()) for line in raw.splitlines())}
    if mode == "html":
        parser = HTMLLayout()
        parser.feed(raw)
        parser.close()
        result.update(parser.counts)
    elif mode in {"markdown", "transcript"}:
        # Fenced code is not authorial layout or prose.
        lines, fence = [], None
        for line in raw.splitlines():
            if fence:
                if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*", line):
                    fence = None
                continue
            match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
            if match:
                fence = (match.group(1)[0], len(match.group(1)))
                continue
            lines.append(line)
        visible = "\n".join(lines)
        result["markdown_bold"] = len(re.findall(r"(?:\*\*[^*\n]+\*\*|__[^_\n]+__)", visible))
        result["headings"] = len(re.findall(r"^ {0,3}#{1,6}\s+", visible, re.M))
        result["images"] = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", visible))
        result["quote_blocks"] = len(re.findall(r"^ {0,3}>\s?", visible, re.M))
        result["list_items"] = len(re.findall(r"^\s*(?:[-+*]\s+|\d+[.)]\s+)", visible, re.M))
    return result


def measure(raw: str, mode: str) -> dict:
    plain = clean_text(raw, mode)
    # URL spellings and destinations are not prose or English vocabulary samples.
    plain = re.sub(r"https?://\S+", "", plain)
    sentences = [value.strip() for value in SENT_SPLIT.split(plain) if units(value)]
    paragraphs = [value.strip() for value in re.split(r"\n\s*\n", plain) if units(value)]
    sentence_lengths, paragraph_lengths = [units(value) for value in sentences], [units(value) for value in paragraphs]
    # Empty strings must not count as particles ("" is a substring of any string).
    endings = sum(bool(tail) and tail in PARTICLES for tail in
                  (value.rstrip(" \t\r\n“”‘’「」『』\"'）)]}")[-1:] for value in sentences))
    return {
        "length_units": units(plain), "sentence_lengths": sentence_lengths, "paragraph_lengths": paragraph_lengths,
        "particle_occurrences": Counter({char: plain.count(char) for char in PARTICLES if plain.count(char)}),
        "particle_sentence_endings": endings,
        "punctuation": Counter({char: plain.count(char) for char in PUNCTUATION if plain.count(char)}),
        "transitions": Counter({word: plain.count(word) for word in TRANSITIONS if plain.count(word)}),
        "surface_forms": Counter({word: plain.count(word) for word in SURFACE_FORMS if plain.count(word)}),
        "rhetorical_patterns": Counter({name: len(pattern.findall(plain)) for name, pattern in PATTERNS.items()}),
        "digits": len(re.findall(r"[0-9]", plain)),
        "number_blocks": len(re.findall(r"[0-9]+(?:[.,][0-9]+)*%?", plain)),
        "english_blocks": len(re.findall(r"[A-Za-z]{2,}(?:[-'][A-Za-z]{2,})*", plain)),
        "layout": Counter(layout(raw, mode)),
        "samples": [value[:80] for value in sentences if units(value) <= 30][:2],
    }


def empty_measurement() -> dict:
    value = measure("", "plain")
    value["samples"] = []
    return value


def describe(value: dict) -> dict:
    sentences = value["sentence_lengths"]
    count = len(sentences)
    thousand = value["length_units"] / 1000
    mappings = ("particle_occurrences", "punctuation", "transitions", "surface_forms", "rhetorical_patterns", "layout")
    return {
        "length_units": value["length_units"],
        "sentences": distribution(sentences), "paragraphs": distribution(value["paragraph_lengths"], True),
        "sentence_ratios": {"le_8": ratio(sum(length <= 8 for length in sentences), count),
                            "le_15": ratio(sum(length <= 15 for length in sentences), count),
                            "ge_50": ratio(sum(length >= 50 for length in sentences), count)},
        "particle_sentence_endings": value["particle_sentence_endings"],
        "particle_ending_ratio": ratio(value["particle_sentence_endings"], count),
        **{name: dict(sorted(value[name].items())) for name in mappings},
        "numeric_english": {name: value[name] for name in ("digits", "number_blocks", "english_blocks")},
        "per_1000_length_units": {
            **{name: ratio(value[name], thousand) for name in ("digits", "number_blocks", "english_blocks")},
            "transition_occurrences": ratio(sum(value["transitions"].values()), thousand),
            "particle_occurrences": ratio(sum(value["particle_occurrences"].values()), thousand),
        },
    }


def analyze_documents(documents, include_samples=False) -> dict:
    aggregate = empty_measurement()
    results = []
    formats = Counter()
    for index, (raw, mode) in enumerate(documents, 1):
        value = measure(raw, mode)
        formats[mode] += 1
        result = {"label": f"D{index:03d}", "format": mode,
                  "status": "ok" if value["length_units"] else "empty", "metrics": describe(value)}
        if include_samples:
            result["samples"] = value["samples"]
        results.append(result)
        for key in ("length_units", "particle_sentence_endings", "digits", "number_blocks", "english_blocks"):
            aggregate[key] += value[key]
        for key in ("sentence_lengths", "paragraph_lengths"):
            aggregate[key].extend(value[key])
        for key in ("particle_occurrences", "punctuation", "transitions", "surface_forms", "rhetorical_patterns", "layout"):
            aggregate[key].update(value[key])
    return {
        "schema_version": SCHEMA_VERSION, "scope": SCOPE,
        "privacy": {"labels": "opaque", "samples_included": bool(include_samples)},
        "measurement": {
            "length_unit": "Chinese characters plus ASCII letters and digits; punctuation and spaces excluded",
            "sentences": "Terminal 。！？!? and non-decimal periods; blank lines also delimit units",
            "paragraphs": "Blank-line-separated visible text, including headings and quotations",
            "quantiles": "Linear interpolation; population standard deviation divided by mean for CV",
            "short_long_thresholds": "Descriptive bins only: <=8, <=15, >=50 length units",
            "word_counts": "Fixed literal forms; no segmentation, entity extraction, or semantic classification",
        },
        "document_count": len(results), "nonempty_document_count": sum(item["status"] == "ok" for item in results),
        "formats": dict(sorted(formats.items())), "summary": describe(aggregate), "documents": results,
    }


def display(value) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def render_report(report: dict) -> str:
    lines = [REPORT_MARKER, "# 语料描述统计报告", "", "统计仅描述本次语料，不鉴定作者、AI 来源或文章质量，也不自动制定禁词与写作配额。",
             "长度单位为汉字、ASCII 字母和数字字符；标点与空白不计入长度。句子按终止标点和空行启发式切分，小数点保留；自然段按空行切分，标题与引语保留。字幕换行不代表作者自然段。",
             "分位数使用线性插值；CV 使用总体标准差÷均值。短长句阈值仅为分箱口径。词频为固定词面匹配，不代表语义功能。无数据或零分母显示 N/A。",
             "默认仅使用 D001 等编号，不输出来源路径、原文短句或高频实体。", "",
             f"文档数：{report['document_count']}；有内容文档：{report['nonempty_document_count']}。", ""]

    def section(title, metrics):
        lines.extend(["## " + title, "", f"长度单位总数：{metrics['length_units']}。", "",
                      "| 分布 | 数量 | 最小 | 最大 | 均值 | 中位数 | P10 | P25 | P75 | P90 | CV |",
                      "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for label, key in (("句子", "sentences"), ("段落", "paragraphs")):
            dist = metrics[key]
            lines.append("| " + label + " | " + " | ".join(display(dist[name]) for name in ("n", "min", "max", "mean", "median", "p10", "p25", "p75", "p90", "cv_population")) + " |")
        lines.extend(["", "句长分箱：" + json.dumps(metrics["sentences"]["histogram"], ensure_ascii=False),
                      "段长分箱：" + json.dumps(metrics["paragraphs"]["histogram"], ensure_ascii=False),
                      "短句≤8 / ≤15 / 长句≥50占比：" + " / ".join(display(metrics["sentence_ratios"][key]) for key in ("le_8", "le_15", "ge_50")),
                      "句尾语气词比例：" + display(metrics["particle_ending_ratio"]), ""])
        for label, key in (("语气词字面次数", "particle_occurrences"), ("标点次数", "punctuation"), ("过渡词词面次数", "transitions"),
                           ("指定表层形式次数", "surface_forms"), ("修辞结构模式次数", "rhetorical_patterns"), ("数字与英文块", "numeric_english"),
                           ("每千长度单位次数", "per_1000_length_units"), ("排版标记次数", "layout")):
            entries = metrics[key]
            lines.append(label + "：" + ("；".join(f"{name}={display(value)}" for name, value in entries.items()) if entries else "N/A"))
        lines.append("")

    section("汇总", report["summary"])
    for document in report["documents"]:
        section(document["label"] + "（" + document["format"] + "；" + document["status"] + "）", document["metrics"])
        if "samples" in document:
            lines.extend(["已显式启用的本地样本（最多两句）：", ""])
            for sample in document["samples"]:
                lines.append("> " + sample.replace("\n", " ").replace("\r", " "))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def own_report(path: Path) -> bool:
    if path.suffix.lower() == ".json":
        try:
            return json.loads(read_utf8(path)).get("scope") == SCOPE
        except (ValueError, AttributeError):
            return False
    return read_utf8(path).lstrip().startswith(REPORT_MARKER)


def build_report(source: Path, out: Path, json_out=None, include_samples=False, overwrite=False) -> dict:
    destinations = [out] + ([json_out] if json_out is not None else [])
    if len({path.resolve() for path in destinations}) != len(destinations):
        raise ValueError("Markdown 和 JSON 输出不能指向同一文件。")
    if source.is_file() and source.resolve() in {path.resolve() for path in destinations}:
        raise ValueError("输出不能覆盖输入语料。")
    for path in destinations:
        if path.is_symlink() or (path.exists() and (not overwrite or not own_report(path))):
            raise ValueError("输出已存在或不是本工具报告；请换路径，重写本工具报告需显式 --overwrite。")
    paths = collect_paths([source], destinations)
    if not paths:
        raise ValueError("没有找到可分析的语料文件。")
    documents = []
    for path in paths:
        raw = read_utf8(path)
        if raw.lstrip().startswith(REPORT_MARKER):
            continue
        documents.append((raw, choose_mode(raw, path)))
    if not documents:
        raise ValueError("输入中只有本工具报告，没有语料。")
    report = analyze_documents(documents, include_samples)
    contents = [(out, render_report(report))]
    if json_out is not None:
        contents.append((json_out, json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"))
    for path, content in contents:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    return report


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="本地语料描述统计；默认不输出原文样本或来源路径。")
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--json", dest="json_out", type=Path)
    parser.add_argument("--include-samples", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(args.source, args.out, args.json_out, args.include_samples, args.overwrite)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"统计失败：{error}", file=sys.stderr)
        return 2
    print(f"已生成描述报告，文档 {report['document_count']} 篇；包含原文样本：{bool(args.include_samples)}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
