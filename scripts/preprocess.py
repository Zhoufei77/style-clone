#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预处理：按输入类型清洗对标文案，供 distill_metrics.py 使用。
用法：
    python3 preprocess.py <输入文件或目录...> --out <输出目录>

自动识别类型：
  - 转录稿（含「说话人 时间戳」「关键词」「文字记录」）→ 剥脚手架 + 意群标点归一
  - HTML → 剥标签保正文
  - Markdown → 剥标题/引用标记
  - 纯文本 → 直进

纯标准库，无需联网。
"""
import sys, os, re, glob, argparse

TRANSCRIPT_HINT = re.compile(r'说话人\s*\d+\s*[\d:]+|文字记录|关键词[:：]')
SENT_PUNCT = {'，': '。', '；': '。', '：': '。', '！': '。', '？': '。'}


def is_html(text):
    t = text.lstrip().lower()
    return t.startswith('<!doctype') or t.startswith('<html') or '</' in text[:2000]


def clean_transcript(text):
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r'^说话人\s*\d+\s*[\d:]+$', s):
            out.append('')  # 段落切点
            continue
        if s.startswith('关键词') or s.startswith('文字记录') or s.startswith('转录结果'):
            continue
        if s.startswith('>') or s.startswith('#'):
            continue
        if re.match(r'^\d{4}年\d+月\d+日', s) and ('|' in s or '秒' in s):
            continue
        out.append(s)
    text = '\n'.join(out)
    # 意群标点归一：口播节奏单位=意群，不是句号
    for a, b in SENT_PUNCT.items():
        text = text.replace(a, b)
    return text


def clean_html(text):
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    return text


def clean_markdown(text):
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith('>') or s.startswith('#'):
            continue
        lines.append(ln)
    return '\n'.join(lines)


def clean(text):
    if is_html(text):
        return clean_html(text)
    if TRANSCRIPT_HINT.search(text):
        return clean_transcript(text)
    if re.search(r'^\s{0,3}#{1,6}\s', text, re.M):
        return clean_markdown(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+', help='文件或目录（目录递归取 .md/.txt/.html/.htm）')
    ap.add_argument('--out', required=True, help='清洗后输出目录')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    paths = []
    for inp in args.inputs:
        if os.path.isdir(inp):
            for e in ('*.md', '*.txt', '*.html', '*.htm'):
                paths += glob.glob(os.path.join(inp, '**', e), recursive=True)
        else:
            paths.append(inp)

    for p in sorted(set(paths)):
        if os.path.basename(p).startswith('.'):
            continue
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                raw = f.read()
        except Exception as ex:
            print(f'[skip] {p}: {ex}', file=sys.stderr)
            continue
        cleaned = clean(raw)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        name = os.path.splitext(os.path.basename(p))[0] + '.txt'
        with open(os.path.join(args.out, name), 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print(f'{os.path.basename(p)} -> {name} ({len(cleaned)} chars)')


if __name__ == '__main__':
    main()
