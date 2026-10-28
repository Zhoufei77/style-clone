# 来源与许可

本 skill 的方法与部分组件，整合自两个 MIT 许可的开源项目，在此致谢并保留其许可：

## 1. ghost-writer
- 仓库：`https://github.com/OneSpiral/ghost-writer`
- 用途：24 维法医式风格分析框架（5 组 24 维拆解网格）。
- 许可：见 `LICENSE-ghost-writer.txt`（MIT）。

## 2. ahao-writing-dna-distiller
- 仓库：`https://github.com/ahao31196/ahao-writing-dna-distiller`
- 用途：六层蒸馏方法、AI 味防火墙（L1.5）、`scripts/distill_metrics.py`、`templates/` 产物模板。
- 许可：见 `LICENSE-ahao.txt`（MIT）。

## 本 skill 的新增部分
- `SKILL.md`（三段流水线整合、通用化、不可退让线）
- `references/distill-guide.md`（24 维 × 六层合并流水线）
- `references/write-guide.md`（复刻流水线）
- `references/preprocess.md`（输入类型识别 + 清洗规范）
- `references/verify-guide.md`（subagent 客观对比验证）
- `scripts/preprocess.py`（转录稿/HTML/Markdown/纯文本分流清洗）
- `templates/WRITING-DNA.md`（通用整合入口模板）

## 通用版

本版由 style-clone 固定源码版本 `407a09a05396d45549752edfbaef25174c5e5616` 整理，保留提炼、写作、对比验证流程；重写通用入口与工作指南，调整模板与统计措辞，移除特定 Agent 和预置作者习惯。脚本修订用于保护原文、保持统计口径并减少报告的默认信息披露。

上游方法、原脚本及模板的归属仍按本文件与两份上游 MIT 许可保留。新增和修订部分使用本包 `LICENSE`，不将本地用户资料或运行产物纳入许可或公开分发范围。
