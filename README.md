# style-clone · 风格复刻引擎

把一个作者/账号的写作风格，蒸馏成一套可复用的「写作 DNA」，再照它写出同风格的新内容。**通用**：对标和产出可以是任何领域、任何文体——口播稿、公众号文、小红书、教程、评测、观点文……

> 一个 Claude Code 项目型 skill。只做「提炼 + 复刻 + 验证」，不做参数调研、剪辑、配音等下游。

## 它能做什么

```
① distill（提炼）   几篇对标文案  →  写作 DNA 档案
② write（复刻）     DNA + 内容素材 →  同风格新文案
③ verify（验证）    对标 + 新文案  →  客观对比报告
```

三段在一轮对话里自动接续，只有两次人工输入：给对标文案、给「要复刻什么」。

## 核心原理：蒸馏不是求平均

大多数风格蒸馏的失败，是把 N 篇文压成一份「平均模板」——而一个作者的风格恰恰活在**不规则**里（句长起伏、一句一段、带脾气的地方）。求平均会把这些磨平，磨平 = AI 味。

所以每一层产物都同时输出三层：

- **规律 Patterns**：可迁移规则，但必须带变化区间（是「句长 8–20 字、长句后接 4–8 字短句」，不是「平均句长 15 字」）。
- **基线 Baselines**：量化指纹（句长 CV、短句占比、语气词收尾率、高危词密度…），由脚本产出，当「像不像作者 / 有没有 AI 味」的尺子。
- **样本 Samples**：原文照抄的招牌句，按 7 桶分好，补抽象规律留不住的手感。

## 压 AI 味的关键：描述性 DNA 没用，指令性的才行

「句长 CV 1.4」「语气词收尾率 0.3%」这些数字，下游根本不知道要做什么。所以有专门一层 **AI 味防火墙**，把每个数值翻成能照做的硬指令：

| 描述（没用） | → | 指令（有用） |
|---|---|---|
| 短句占比 31% | → | 每 3–4 句必须有 1 句 ≤8 字砸一下 |
| 高危词密度低 | → | 全文「然而/因此/赋能」= 0 |
| 语气词收尾 0.3% | → | 别硬加语气词 |

## 快速开始

**1. 准备对标文案**（建议 ≥5 篇，覆盖不同类型）

**2. 触发 distill**
```bash
python3 scripts/preprocess.py "对标文件或目录" --out "<作者名>/raw"
python3 scripts/distill_metrics.py "<作者名>/raw" --out "<作者名>/_meta/baseline-report.md"
```
再让 Claude 按 `references/distill-guide.md` 完成 24 维 × 六层蒸馏，产出 `<作者名>/` 整套 DNA。

**3. 触发 write**：DNA + 「要复刻什么」+ 素材 → 新文案。

**4. 触发 verify**：起干净 subagent 客观对比新稿 vs 对标。

## 目录结构

```
style-clone/
├── SKILL.md                    # 入口：三段流水线 + 不可退让线
├── references/
│   ├── distill-guide.md        # 提炼（24维 × 六层）
│   ├── write-guide.md          # 复刻
│   ├── preprocess.md           # 输入清洗
│   └── verify-guide.md         # 客观对比验证
├── scripts/
│   ├── preprocess.py           # 转录稿/HTML/MD/纯文本分流清洗
│   └── distill_metrics.py      # 量化基线
└── templates/dna/              # 产物模板（01~06 + WRITING-DNA + beat-sheet）
```

## 依赖

- Python 3，纯标准库，无需联网。
- 可选 `jieba`（高频词更准；不装用字符二元组近似）。

## 许可

MIT。方法整合自两个 MIT 开源项目，详见 `NOTICE.md`：
- [ghost-writer](https://github.com/OneSpiral/ghost-writer) — 24 维法医式风格分析
- [ahao-writing-dna-distiller](https://github.com/ahao31196/ahao-writing-dna-distiller) — 六层蒸馏 + AI 味防火墙 + 量化基线脚本
