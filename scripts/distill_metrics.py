#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作 DNA 蒸馏 · 量化基线器（distill_metrics.py）

一次跑出一个作者/公众号的全套量化指纹，作为写作 DNA 的「人味量化基线」。
下游写作时拿这些数值当尺子，判断草稿是「像作者本人」还是「往 AI 收敛」。

用法：
    python3 distill_metrics.py <语料目录>
    python3 distill_metrics.py <语料目录> --out baseline-report.md

产出：
  表层：句长分布 + 变异系数CV、短/长句占比、段落长度、加粗频率、
        小标题、图片密度、标点偏好、中英混用、emoji
  人味：语气词收尾率、高危词自然密度(附命中明细)、名词化/翻译腔密度、
        「不是A而是B」密度、排比三连密度、具体度代理(数字/英文块密度)
  词频：Top 30（装 jieba 更准，否则字符二元组近似）

纯标准库，无需联网。
"""

import sys, os, re, glob, argparse
from collections import Counter, OrderedDict

CJK = r'\u4e00-\u9fff'

# —— AI 味高危词黑名单（建基线用：看作者对这些词的“自然”使用频率）——
HIGH_RISK = [
    '值得注意的是', '值得一提的是', '总而言之', '综上所述', '总的来说',
    '事实上', '实际上', '某种程度上', '在一定程度上', '归根结底', '说到底',
    '不仅仅是', '不只是', '更是', '真正的', '所谓的',
    '与此同时', '除此之外', '此外', '然而', '因此',
    '首先', '其次', '最后', '无论是', '让我们', '我们不妨',
    '拥抱', '赋能', '抓手', '闭环', '颗粒度', '底层逻辑', '心智',
    '重新定义', '未来已来', '值得我们', '深刻地', '极大地',
]
NOMINALIZE = ['的存在', '进行了', '使得', '得以', '具有很强', '性的', '化的', '被']
END_PARTICLES = '啊吧呢吗嘛呗啦咯哈哟喔噢咧'
SENT_SPLIT = re.compile(r'[。！？!?…]+|\n{2,}')


def read_texts(corpus_dir):
    exts = ('*.md', '*.txt', '*.html', '*.htm')
    paths = []
    for e in exts:
        paths += glob.glob(os.path.join(corpus_dir, '**', e), recursive=True)
    docs = []
    for p in sorted(set(paths)):
        if os.path.basename(p).startswith('.'):
            continue
        try:
            with open(p, 'r', encoding='utf-8', errors='replace') as f:
                docs.append((p, f.read()))
        except Exception as ex:
            print(f'[skip] {p}: {ex}', file=sys.stderr)
    return docs


def count_layout(raw, is_html):
    """加粗、小标题、图片、引用块——在清洗前统计标记。"""
    md_bold = len(re.findall(r'\*\*[^*\n]+\*\*', raw))
    html_bold = 0
    imgs = len(re.findall(r'!\[[^\]]*\]\([^)]*\)', raw))
    if is_html:
        html_bold = (len(re.findall(r'font-weight\s*:\s*(?:bold|[6-9]00)', raw, re.I))
                     + len(re.findall(r'<(?:b|strong)\b', raw, re.I)))
        imgs += len(re.findall(r'<img\b', raw, re.I))
    headings = [len(re.sub(r'\s', '', m)) for m in re.findall(r'^\s{0,3}#{1,6}\s+(.+)$', raw, re.M)]
    quotes = len(re.findall(r'^\s{0,3}>', raw, re.M))
    return md_bold, html_bold, imgs, headings, quotes


def clean(text, is_html):
    if is_html:
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', text, flags=re.I | re.S)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', text)
    text = re.sub(r'`[^`]*`', ' ', text)
    return text


def analyze(docs):
    s = {
        'n_docs': len(docs), 'total_chars': 0,
        'sent_lens': [], 'para_lens': [],
        'md_bold': 0, 'html_bold': 0, 'headings': [], 'images': 0, 'quotes': 0,
        'dashes': 0, 'parens': 0, 'cn_quotes': 0, 'emoji': 0,
        'ascii_runs': 0, 'digits': 0,
        'risk_hits': Counter(), 'risk_total': 0,
        'nominalize': 0, 'bushi_ershi': 0, 'sanlian': 0,
        'end_particle_sents': 0, 'total_sents': 0,
        'short_samples': [], 'colloquial': 0,
        'ai_conn': Counter(), 'human_conn': Counter(),
        'word_counter': Counter(), 'char_counter': Counter(),
    }
    # 连接词对照：AI 常用 signpost vs 作者可能用的"人话"接续
    AI_CONN = ['然而', '因此', '与此同时', '除此之外', '此外', '首先', '其次',
               '最后', '总而言之', '综上所述', '值得注意的是', '不仅如此', '进而', '故而']
    HUMAN_CONN = ['但', '可', '不过', '所以', '于是', '结果', '后来', '你看',
                  '说白了', '问题是', '关键', '说真的', '其实', '而且', '再说']
    emoji_re = re.compile('[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]')
    try:
        import jieba
        has_jieba = True
    except Exception:
        has_jieba = False

    for path, raw in docs:
        is_html = path.lower().endswith(('.html', '.htm')) or ('</' in raw[:2000])
        md_bold, html_bold, imgs, headings, quotes = count_layout(raw, is_html)
        s['md_bold'] += md_bold; s['html_bold'] += html_bold
        s['images'] += imgs; s['headings'] += headings; s['quotes'] += quotes

        plain = clean(raw, is_html)
        s['total_chars'] += len(re.findall(r'[^\s]', plain))

        # 标点 / 混用 / 具体度代理
        s['dashes'] += len(re.findall(r'——|—', plain))
        s['parens'] += len(re.findall(r'[（）()]', plain))
        s['cn_quotes'] += len(re.findall(r'[“”「」『』]', plain))
        s['emoji'] += len(emoji_re.findall(plain))
        s['ascii_runs'] += len(re.findall(r'[A-Za-z]{2,}', plain))
        s['digits'] += len(re.findall(r'\d', plain))

        # AI 味标记
        for w in HIGH_RISK:
            c = plain.count(w)
            if c:
                s['risk_hits'][w] += c
                s['risk_total'] += c
        s['nominalize'] += sum(plain.count(w) for w in NOMINALIZE)
        s['colloquial'] += len(re.findall(r'[' + END_PARTICLES + r']', plain))
        for w in AI_CONN:
            c = plain.count(w)
            if c: s['ai_conn'][w] += c
        for w in HUMAN_CONN:
            c = plain.count(w)
            if c: s['human_conn'][w] += c
        s['bushi_ershi'] += len(re.findall(r'不是[^，。！？]{1,20}?而是', plain))
        s['sanlian'] += len(re.findall(r'[^\s，。]{2,10}、[^\s，。]{2,10}、[^\s，。]{2,10}', plain))
        s['sanlian'] += len(re.findall(r'既[^，。]{1,15}又[^，。]{1,15}(?:还|也)', plain))

        # 段落
        for para in re.split(r'\n{2,}', plain):
            p = para.strip()
            plen = len(re.findall(r'[^\s]', p))
            if plen > 0:
                s['para_lens'].append(plen)

        # 句子 + 语气词收尾
        for sent in SENT_SPLIT.split(plain):
            sent = sent.strip()
            if not sent:
                continue
            slen = len(re.findall(r'[' + CJK + r'A-Za-z0-9]', sent))
            if slen > 0:
                s['sent_lens'].append(slen)
                s['total_sents'] += 1
                if sent[-1] in END_PARTICLES:
                    s['end_particle_sents'] += 1
                # 收集"人话素材"：极短句样本（供样本库 / 防火墙 C 用）
                if 2 <= slen <= 8 and re.search(r'[' + CJK + r']', sent):
                    if len(s['short_samples']) < 40:
                        s['short_samples'].append(sent)

        # 词频
        if has_jieba:
            for w in jieba.cut(plain):
                w = w.strip()
                if len(w) >= 2 and re.search(r'[' + CJK + ']', w):
                    s['word_counter'][w] += 1
        else:
            cjk = re.findall(r'[' + CJK + r']', plain)
            joined = ''.join(cjk)
            for i in range(len(joined) - 1):
                s['word_counter'][joined[i:i + 2]] += 1

    s['has_jieba'] = has_jieba
    return s


def pct(a, b):
    return f'{(100.0 * a / b):.1f}%' if b else 'n/a'


def render(s):
    sents = s['sent_lens']; paras = s['para_lens']
    n = max(s['n_docs'], 1)
    k = s['total_chars'] / 1000.0 if s['total_chars'] else 0

    def avg(xs):
        return sum(xs) / len(xs) if xs else 0

    mean = avg(sents)
    if sents and mean:
        var = sum((x - mean) ** 2 for x in sents) / len(sents)
        cv = (var ** 0.5) / mean
    else:
        cv = 0
    short = sum(1 for x in sents if x <= 15)
    short8 = sum(1 for x in sents if x <= 8)
    long_ = sum(1 for x in sents if x >= 50)

    L = []
    L.append('# 写作 DNA 量化基线报告\n')
    L.append(f'- 文档数：{s["n_docs"]}　总非空字符：{s["total_chars"]}')
    L.append(f'- 分词方式：{"jieba" if s["has_jieba"] else "字符二元组近似（装 jieba 更准）"}')
    L.append('')
    L.append('## 句子（节奏）')
    L.append(f'- 句子数：{len(sents)}　平均句长：{mean:.1f} 字')
    L.append(f'- **句长变异系数 CV：{cv:.2f}**（越高越有人味；下游草稿低于此 0.6 倍 → 偏 AI）')
    L.append(f'- 短句(≤15字)占比：{pct(short, len(sents))}　**短句(≤8字)占比：{pct(short8, len(sents))}**　长句(≥50字)占比：{pct(long_, len(sents))}')
    L.append('')
    L.append('## 段落（移动端节奏）')
    L.append(f'- 段落数：{len(paras)}　平均段落长度：{avg(paras):.1f} 字')
    L.append(f'- 短段(≤40字)占比：{pct(sum(1 for x in paras if x <= 40), len(paras))}（公众号常见短段节奏）')
    L.append('')
    L.append('## 排版标记')
    L.append(f'- Markdown 加粗 `**`：{s["md_bold"]}　HTML 加粗：{s["html_bold"]}')
    L.append(f'- 每千字加粗约：{((s["md_bold"] + s["html_bold"]) / k):.1f} 次' if k else '- 每千字加粗：n/a')
    L.append(f'- 小标题数：{len(s["headings"])}　平均字数：{avg(s["headings"]):.1f}')
    L.append(f'- 引用/金句块 `>`：{s["quotes"]}　图片：{s["images"]}（每篇约 {s["images"] / n:.1f} 张）')
    L.append('')
    L.append('## 人味指纹（对抗 AI 味的核心基线）')
    L.append(f'- **语气词收尾率：{pct(s["end_particle_sents"], s["total_sents"])}**（句尾带 啊/吧/呗/嘛…；AI 常为 0）')
    L.append(f'- **高危词自然密度：{(s["risk_total"] / k):.2f}/千字**（作者本人的套话基线；草稿远超即 AI 味）')
    L.append(f'- 名词化/翻译腔密度：{(s["nominalize"] / k):.2f}/千字（作者通常很低）')
    L.append(f'- 「不是A而是B」密度：{(s["bushi_ershi"] / k):.2f}/千字')
    L.append(f'- 排比三连密度：{(s["sanlian"] / k):.2f}/千字（供下游限流）')
    L.append('')
    L.append('## 具体度代理 / 标点混用')
    L.append(f'- 数字密度：{(s["digits"] / k):.1f}/千字　英文词块(≥2字母)：{(s["ascii_runs"] / k):.1f}/千字（越高越具体/越洋气）')
    L.append(f'- 破折号：{s["dashes"]}　括号：{s["parens"]}　中文引号：{s["cn_quotes"]}　emoji：{s["emoji"]}')
    L.append('')
    if s['risk_hits']:
        L.append('## 作者命中的高危词（自然频率，非扣分，用来建基线）')
        for w, c in s['risk_hits'].most_common(20):
            L.append(f'- {w} × {c}')
        L.append('')
    L.append('## 高频词 Top 30（人工过滤停用词/噪声副词后填入 01-language-dna.md）')
    for w, c in s['word_counter'].most_common(30):
        L.append(f'- {w} × {c}')
    L.append('')

    # —— 连接词对照：作者靠什么替代 signpost ——
    L.append('## 连接词对照（作者用"人话"还是"AI signpost"接续）')
    ai_top = s['ai_conn'].most_common(10)
    hu_top = s['human_conn'].most_common(10)
    L.append('- AI 式 signpost（作者若≈0，全部列入 06 防火墙 A1 红线禁用）：'
             + ('，'.join(f'{w}×{c}' for w, c in ai_top) if ai_top else '（几乎不用，很好）'))
    L.append('- 人话接续（作者的替代动作，填进 06 防火墙 C1 过渡库）：'
             + ('，'.join(f'{w}×{c}' for w, c in hu_top) if hu_top else '（未检出，需人工补）'))
    L.append('')

    # —— 人话素材：短句样本 ——
    L.append('## 人话素材 · 极短句样本（直接挑进 01 样本库 C7 / 防火墙 C）')
    if s['short_samples']:
        for smp in s['short_samples'][:20]:
            L.append(f'- 「{smp}」')
    else:
        L.append('- （未检出 ≤8 字短句——作者句子偏长，或语料需再看）')
    L.append(f'\n- 语气词出现总数：{s["colloquial"]}（每千字 {(s["colloquial"]/k):.1f}；越高越口语）')
    L.append('')

    # —— 自动写作指令建议：把数值翻成 06 防火墙 B 表 ——
    L.append('## ⭐ 自动写作指令建议（直接填进 06-ai-flavor-firewall.md 的 B 表）')
    L.append('> 这几条把上面的数值翻成了下游能执行的硬指令——这才是真正压 AI 味的东西。')
    target_short = max(3, round(short8 / max(len(sents), 1) * 30)) if sents else 3
    every_n = round(100.0 / (100.0 * s['end_particle_sents'] / s['total_sents'])) if s['end_particle_sents'] else '很多'
    risk_budget = max(1, round((s['risk_total'] / k) * 3)) if k else 1
    L.append(f'- 短句：一篇 ~3000 字里，≤8 字短句**不少于 {target_short} 句**；每 3–4 句穿插 1 句')
    L.append(f'- 语气收尾：**每 {every_n} 句**允许 1 句用语气词收尾（照作者习惯，别硬加）')
    L.append(f'- 高危词预算：3000 字全文高危词**总数 ≤ {risk_budget} 个**，红线词 0 个')
    L.append(f'- 段落：每段 ≤ {avg(paras)*1.3:.0f} 字左右，该短处敢一句一段')
    L.append('- 具体度：每 2–3 段至少 1 个真名字/真数字，禁用"很多/一些/某种"')
    L.append('')
    L.append('> 脚本只给数字和素材。招牌句型、修辞、称呼距离、以及样本库的分桶挑选需人工完成。')
    L.append('> **务必**把「自动写作指令建议」填进 06 防火墙——只有指令化的规则才拦得住 AI 味。')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('corpus_dir')
    ap.add_argument('--out', default=None, help='报告写到文件（默认打印到屏幕）')
    args = ap.parse_args()

    if not os.path.isdir(args.corpus_dir):
        print(f'目录不存在：{args.corpus_dir}', file=sys.stderr); sys.exit(1)
    docs = read_texts(args.corpus_dir)
    if not docs:
        print('没找到 .md/.txt/.html 文件', file=sys.stderr); sys.exit(1)

    report = render(analyze(docs))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(report + '\n')
        print(f'报告已写入 {args.out}')
    else:
        print(report)


if __name__ == '__main__':
    main()
