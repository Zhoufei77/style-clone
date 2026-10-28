# 文风复刻·通用版

从参考文案提炼写作 DNA，用新的主题和素材创作同风格内容，再对照原文检查节奏、结构、用词与语气。

技能名：`style-clone-general`。版本：`1.0.0`。许可证：MIT，上游声明见 `NOTICE.md`。

## 三种用法

| 任务 | 输入 | 输出 |
| --- | --- | --- |
| 提炼 distill | 用户提供的参考稿 | 有证据的规律、描述统计、必要短例、结构节拍与写作建议 |
| 复刻 write | 参考稿或 DNA＋本次的新素材 | 保留新事实与受众要求的同风格新稿 |
| 验证 verify | 参考原文＋新稿 | 接近与偏离的位置、证据和修改建议 |

可以只做其中一项，也可以在材料齐全时连续完成。参考稿不预置为某个作者、行业或账号；原作者的身份、经历、数字和观点不会自动迁入新稿。

量化结果用于描述样本和比较差异，不是 AI 来源鉴定、作者身份判断或写作质量分数。单篇参考也能用，结论限于已见样本；更多样本和更多文体不自动等于可靠。

## 在 WorkBuddy 开放平台发布

使用 [开放平台发布入口](https://open.workbuddy.cn/skill/publish?action=create&step=1)，流程为“配置技能 → 确认信息 → 提交审核”。此处按开放平台发布规范打包，不以客户端本地导入规则代替。

1. 上传配套的 `style-clone-general.zip`。发布页仅接受 **ZIP，不超过3MB**。
2. 在确认页核对解析出的中英文名称、介绍、版本和使用示例。
3. 市场展示分类建议选“内容创作”，可按实际定位补充“效率工具”；至少1项、最多3项。
4. 服务类目是另一组必填配置，建议选“工具 → 办公”；至少1项、最多5项。
5. 可保留平台文字头像。若另传头像，使用512×512px、≤500KB的JPG/PNG。
6. 发布者核对其余页面要求后提交审核；打包或解析通过不等于审核通过。

上述包大小、分类及头像要求在开放平台页面中核对，日期为2026-10-25。界面变化时以当前发布页为准。上传与审核状态以开放平台记录为准，此说明不代表已通过审核。

按 [WorkBuddy 开放平台官方技能文档](https://open.workbuddy.cn/docs/skill)，`SKILL.md` 的 YAML frontmatter 已包含全部八项必填字段：

| 字段 | 内容 |
| --- | --- |
| `name` | `style-clone-general` |
| `display_name` | 文风复刻（通用版） |
| `display_name_en` | Writing Style Clone |
| `description` | 用途与触发场景 |
| `description_zh` | 中文详情介绍 |
| `description_en` | 英文详情介绍 |
| `version` | `1.0.0` |
| `author` | `Style Clone contributors` |

可选的 `examples_zh`、`examples_en` 各有三个示例。未设置固定工具白名单；功能不依赖某个厂商的工具名称。

## 安装后这样使用

```text
请用文风复刻通用版，分析这三篇参考稿的节奏、结构和语气。只提炼文风，不写新稿，不把原稿里的经历写进公共模板。
粘贴参考稿
```

```text
请用 style-clone-general，参考上面的文风，根据以下新素材写一篇约600字的文章。保留事实与条件，不照抄参考稿的句子，写完简要说明风格偏差。
粘贴新素材
```

```text
对比参考稿与这篇新稿，指出三处值得修改的位置。不要因为字数或话题不同就直接判为文风不同。
粘贴参考稿和新稿
```

用户只要稿件时，分析与检查留在内部；明确要求对比报告时再交付证据和说明。

## 文件与运行环境

```text
style-clone-general/
├── SKILL.md
├── references/                 提炼、写作、预处理、验证指南
├── templates/              空白通用模板，不含用户文稿
├── scripts/preprocess.py       本地预处理
├── scripts/distill_metrics.py  描述统计与报告
├── tests/                     脚本与发布字段检查
├── README.md
├── NOTICE.md
├── LICENSE
├── LICENSE-ahao.txt
├── LICENSE-ghost-writer.txt
└── VERSION
```

上传 ZIP 中只有这个顶层技能文件夹，内部仅保留 scripts/、references/、templates/、tests/ 等单层子目录，符合2026-10-28发布解析器的两级目录限制；不包含版本控制目录、缓存或运行产物。

普通写作和分析不需要 API Key、Python、网络或其他 Skill。运行可选脚本时，需要 Python 3.9+，只用标准库。Windows 可用 `py -3`，macOS/Linux 可用 `python3`；以下统一写作 `python`。

在用户的任务工作区执行，`<skill-dir>` 换成技能安装目录。输入输出路径属于本次任务，不要将语料和产物写入安装目录：

```sh
python "<skill-dir>/scripts/preprocess.py" 输入目录 --out style-profile/clean
python "<skill-dir>/scripts/distill_metrics.py" style-profile/clean --out style-profile/_meta/baseline-report.md --json style-profile/_meta/baseline.json
python -B -m unittest discover -s "<skill-dir>/tests" -v
```

预处理可指定 `--mode auto|transcript|markdown|html|plain`。默认保留原标点；确需将口播按意群归一时才加 `--speech-units`，并对参考稿与新稿采用相同口径。原件保留用于排版观察，清洗副本用于语言统计。

报告默认不输出原文短句、高频实体或绝对输入路径；确需本地样本时才加 `--include-samples`。没有执行脚本就标明统计未测；没有子代理就使用自检并如实标注，不伪称独立评审。

## 通用化与隐私

本版保留24维观察、规律／基线／样本三层档案、结构节拍、内容边界和对比验证。原有特定 Agent 调用改成可选路径，预置品类例子与写死配额改成从本次语料归纳的风格建议。零次出现不变成禁词，描述性统计不变成复刻保证。

本包只分发空白模板、通用规则和脚本，不附带个人原稿、DNA 档案、客户案例、账号、私有路径或凭据。版权许可中上游作者的公开署名依法保留。

用户提供的原文、生成的档案和报告留在其任务工作区，不自动写进已安装 Skill 或公共包。脚本离线处理指定输入，不上传数据；宿主模型的数据处理规则由宿主决定。公开报告或样本前，应再次核对授权和可识别内容。

来源与修订版本见 `NOTICE.md`。不把某个用户的偏好作为所有人的默认文风。
