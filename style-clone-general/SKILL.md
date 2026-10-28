---
name: style-clone-general
display_name: 文风复刻（通用版）
display_name_en: Writing Style Clone
description: 从用户提供的参考文案提炼写作风格，形成可复用的写作 DNA，用新主题和素材生成同风格内容，并对比原文与新稿。用户要求提炼文风、复刻账号风格、照参考写作或检查风格偏差时使用。支持文章、口播、教程、评测与故事；不替代事实调研、配音或视频制作。
description_zh: 从参考文案提炼写作 DNA，用新素材创作同风格内容，并对比节奏、结构、用词和语气，保留新任务的事实与表达要求。
description_en: Extract reusable writing patterns from reference texts, create new content in a similar style, and compare rhythm, structure, wording, and tone without importing personal facts.
version: 1.0.0
author: Style Clone contributors
examples_zh:
  - 从这几篇参考文案中提炼文风，整理成可复用的写作 DNA。
  - 参考这些文章的节奏和语气，用我提供的新素材写一篇，不沿用原文的经历和观点。
  - 对比这篇新稿和参考稿，指出风格接近与偏离的位置，并给出修改建议。
examples_en:
  - Extract a reusable writing style profile from these reference texts.
  - Use these reference texts to write about my new topic without copying their personal stories or claims.
  - Compare this draft with the references and explain where its style matches or differs.
---

# 文风复刻·通用版

提炼参考稿的表达方式，再用本次的新素材写作。核心产物是三层写作 DNA：有样本依据的规律、真实测得的描述统计、必要且有权使用的短例。结构与语气从参考稿归纳，不预设某个作者、账号、品类或固定模板。

## 先按用户任务分流

- **提炼 distill**：读取 [提炼指南](references/distill-guide.md)，交付写作 DNA；用户只要分析时，不强制继续写稿。
- **复刻 write**：读取 [写作指南](references/write-guide.md)。已有 DNA 就复用；参考稿和新主题都已给出时，在同一任务内完成提炼、写作和复核，不重复索要已有信息。
- **验证 verify**：读取 [验证指南](references/verify-guide.md)，对照参考原文与新稿指出相似和偏离；只要求评估时不擅自改稿。

先使用当前对话的材料、主题、受众、篇幅和修改范围。缺少会改变结果的信息时集中询问，其余部分继续。单篇参考也能分析，但只称为本次样本观察，不把数量门槛等同于可靠性保证。

## 形式与内容分开

可迁移的是节奏、结构、过渡、举证方式、语气、排版和叙述位置。参考稿中的姓名、账号、自称、经历、客户、产品、数字、引语及观点不自动进入新稿。

新任务的事实只取本次已给或明确允许使用的材料。没有依据就不补造参数、采访、试用或第一人称经历。用户授权虚构时可以创造情节，但保持人物、视角和因果一致；假设案例不能包装成真实经历。

用户指定的新受众、立场、格式和锁定文字优先。不要为了复刻口吻增加辱骂、删掉事实条件、改动引语、冒用身份或强加原作者的观点。风格相似不要求照搬原句。

## 提炼应有的深度

1. **准备可比语料。** 分开作者、文体和用途；保留原件观察排版，另做清洗副本分析语言。处理转录、HTML 或 Markdown 时读取 [预处理指南](references/preprocess.md)。
2. **记录规律与变化。** 按指南的24维观察节奏、词汇、语气、修辞和呈现；有证据才填，不强求每项都有结论。记录变化区间、反例和适用情境。
3. **测量可测的部分。** 有 Python 时运行随包脚本，记录每篇和汇总口径。统计是样本特征，不能证明 AI 来源、写作质量或作者身份；未测的数值写“未测”，不凭感觉填数。
4. **提炼结构节拍。** 逐篇记录每段在做什么，再归纳真实出现的结构原型；不强制凑出固定数量的原型。
5. **把观察变成写作动作。** 给出有条件的节奏、衔接和措辞建议，并附必要证据。样本没出现某个词，不等于该词应被禁用；不机械规定每几句必须有短句、每段必须有数字。
6. **验证迁移。** 用新稿与参考原文复核，区分内容差异、受众要求和真正的风格偏差。数值接近但读感不同，要如实记录。

## 输出与隐私

默认在对话中交付用户需要的分析、稿件或对比结论。需要保存 DNA 或处理文件时，使用用户指定工作区；未指定时放在当前任务工作区的独立 `style-profile/` 中，重名加后缀，不覆盖现有档案。

模板在 `templates/dna/`。完整档案包含整合入口、语言、结构、内容边界与风格控制；排版和选题视角按需填写。模板占位项只供本次填写，不能当成已分析的结果。不把运行产物写入已安装 Skill 的模板、脚本或公共包。

原稿与原句样本只在用户授权的任务范围内使用，摘录保持最少必要量；公开来源遵守其许可与宿主的引用限制。不自动公开原文、作者档案、联系方式、账号或文件路径，也不上传到第三方检测或改写服务。保留依法需要的上游版权声明，不把它误当私人资料删除。

## 可选本地工具

普通提炼与写作只需宿主的文本能力。以下脚本使用 Python 3.9+ 标准库，无需网络、API Key、分词服务或特定 Agent。

在用户的任务工作区执行；`<skill-dir>` 替换为本 Skill 的实际目录，输入输出路径均属于本次任务，不写进安装目录：

```sh
python "<skill-dir>/scripts/preprocess.py" 输入目录 --out style-profile/clean
python "<skill-dir>/scripts/distill_metrics.py" style-profile/clean --out style-profile/_meta/baseline-report.md --json style-profile/_meta/baseline.json
```

Windows 可将 `python` 换成 `py -3`，macOS/Linux 可换成 `python3`。预处理默认保留标点，只有明确分析口播意群时才加 `--speech-units`；参考稿与新稿必须采用相同处理口径。

量化报告默认不输出原文短句或高频实体。确需在本地报告附样本时，才使用 `--include-samples`；这不会授权公开报告。没有 Python 时手工分析并标明统计未测，仍可继续写作。

有独立子代理时可按验证指南做盲评；没有时执行分轮复核并标为“自检”，不伪称独立评审。交付只说明实际完成的验证，不承诺“复刻成功率”或“去 AI 味”分数。
