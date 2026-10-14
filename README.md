# AI 内容制作工作流

一套面向 AI 内容创作者的本地工作流，用 Markdown 管理选题、素材、写作、审稿、发布和数据复盘，并用 Python 脚本保证状态、目录和内容门禁一致。

它不是单纯的提示词集合，而是一套可追踪、可校验、可恢复的内容生产系统：每个阶段的结果都会落盘，重要事实有证据边界，工作流规则有自动化测试。

## 核心能力

- **完整内容流水线**：从原始素材、选题、调研和策划，一直推进到写作、标题、审稿、发布与复盘。
- **三种工作模式**：`quick` 适合强时效短篇，`standard` 适合日常内容，`flagship` 适合深度打磨。
- **结构化内容资产**：选题、提示词、知识卡片、核心概念、爆款结构和金句分目录沉淀。
- **证据与实测门禁**：关键数据、案例和教程结果在进入正文前需要完成核实或实测。
- **个人风格约束**：写作、标题和审稿共享风格档案，减少模板腔和 AI 味。
- **自动化治理**：状态迁移、目录映射、YAML 字段、Skill 路由和模板结构均可机械校验。
- **数据闭环**：发布后记录平台数据，用真实表现校准选题、标题和内容方法。

## 工作流

```text
raw_idea
  → topics_generated
  → checked_in
  → market_researched（可选）
  → strategies_generated
  → planned
  → assets_ready
  → drafted
  → titled
  → reviewed
  → published
```

所有阶段都可以安全转入 `archived`。强时效短篇在满足条件时可走精简路径：

```text
raw_idea → topics_generated → checked_in → drafted
```

状态、目录、合法迁移和路由的机器权威源是 [`scripts/workflow_config.py`](scripts/workflow_config.py)。

## 快速开始

### 环境要求

- Python 3.9 或更高版本
- Git
- Python 包：`PyYAML`、`pytest`
- 推荐在支持项目级指令与 Skill 的 AI 编程工具中使用

### 1. 克隆并安装依赖

```bash
git clone https://github.com/G-MUYI/content-workflow-lite.git
cd content-workflow-lite
python -m pip install pyyaml pytest
python scripts/init-personal-files.py
```

初始化命令会从空白模板创建本地个人档案，不覆盖已有文件。这些档案由 `.gitignore` 排除，不会随常规 Git 提交公开。

### 2. 查看工作区仪表盘

```bash
python scripts/run-opening-protocol.py
```

仪表盘会扫描当前内容与素材，输出在途数量、流程瓶颈、停滞告警和下一步建议。

### 3. 预检一条自然语言命令

```bash
python scripts/workflow-dispatch.py --command "继续"
```

查看全部可用路由：

```bash
python scripts/workflow-dispatch.py --routes
```

### 4. 创建第一篇内容

将新素材保存到 `选题库/_inbox/`，默认使用：

```text
选题库/_模板/选题模板-标准.md
```

如果在支持本项目指令的 AI 工具中工作，也可以直接发送素材，或使用“从头开始”“策划”“确认素材”“写”“标题”“审稿”等自然语言命令推进。

## 常用命令

| 目的 | 命令 |
|---|---|
| 查看本地仪表盘 | `python scripts/run-opening-protocol.py` |
| 查看命令路由 | `python scripts/workflow-dispatch.py --routes` |
| 预检工作流命令 | `python scripts/workflow-dispatch.py --command "一键推进"` |
| 校验内容与素材结构 | `python scripts/validate-workflow.py` |
| 审计规则、Skill 和路由 | `python scripts/audit-workflow-governance.py` |
| 审计内容单元关系 | `python scripts/audit-content-units.py` |
| 检查发布与复盘数据 | `python scripts/validate-publish-review.py` |
| 生成复盘草案 | `python scripts/generate-review-report.py` |
| 查看提示词补全建议 | `python scripts/organize-prompts.py --suggest` |
| 运行全量测试 | `python -m pytest -q` |

涉及文件移动、发布归档或批量修改的命令，请先查看帮助、执行只读预检，并确认当前 Git 工作区可恢复。

## 目录结构

```text
.
├── AGENTS.md                 # 启动合同、硬门禁和权限边界
├── scripts/
│   ├── workflow_config.py    # 字段、状态、迁移、路由的机器权威源
│   ├── workflow-dispatch.py  # 自然语言命令预检与任务路由
│   ├── validate-workflow.py  # 内容与素材结构校验
│   └── opening-dashboard.py  # 本地工作区仪表盘
├── skills/                   # 各阶段执行卡与通用规范
├── 选题库/
│   ├── _inbox/              # 原始素材和待确认选题
│   ├── 待写/                # 已确认、待策划或待补素材
│   ├── 进行中/              # 初稿、标题和审稿阶段
│   ├── 已发布/              # 按年月归档的已发布内容
│   └── 已弃用/              # 已归档的弃用内容
├── 素材库/                  # 提示词、知识卡片、概念、结构和金句
├── 数据统计/                # 发布数据、复盘和审计记录
├── tests/                   # 单元测试和流程测试
├── evals/                   # 路由与行为场景评测
└── docs/                    # 系统说明、使用指南和运维排错
```

## 设计原则

1. **积极保存**：关键结果写入文件，不只保留在聊天记录中。
2. **权威源唯一**：机器值集中在 `workflow_config.py`，其他文档只解释或引用。
3. **状态真实**：没有完成实测、核验或审稿，就不提前标记完成。
4. **证据分层**：事实、引述、推断和作者判断分别处理。
5. **作者在场**：保留与主题相关的操作、选择和判断，不用过程日志伪造真人感。
6. **可恢复优先**：批量变更先审计、小样本验证，再逐批扩张。

## 开发与验证

修改状态机、YAML 字段、阶段门禁、模板、路由或 Skill 后，至少运行：

```bash
python scripts/audit-workflow-governance.py
python scripts/validate-workflow.py
python -m pytest -q
```

全部通过只代表静态治理面和自动化测试通过；外部事实、作者风格、实测结果和发布风险仍需按内容逐项确认。

## 文档

- [`AGENTS.md`](AGENTS.md)：核心执行合同
- [`skills/_通用/工作流详细规范.md`](skills/_通用/工作流详细规范.md)：完整业务规则与边界
- [`docs/README.md`](docs/README.md)：系统说明、使用指南和运维排错索引
- [`选题库/README.md`](选题库/README.md)：选题库使用说明

## 首次使用前

克隆后先做完这三步，工作流才能按你自己的风格跑：

1. 填 `skills/_通用/创作者定位.md`：你是谁、写什么、写给谁、不写什么。选题判断依赖它。
2. 填 `skills/_通用/风格档案/我的风格.md`：贴 3-5 段你自己写得最像自己的原文，再按〇.5 归纳特征。没有这一步，写作和审稿没有风格基线。
3. 按需填 `skills/_通用/用户偏好.md`。建议先留空，用起来再逐步补。

前两步完成后，先拿一篇旧稿跑一次「标题 → 审稿」，确认门禁和风格判断符合预期，再开始批量生产。

## 隐私与安全

本仓库是工作流的**框架**，公开的部分只有规则、脚本、模板和测试。请注意：

- 空白档案模板保存在 `skills/_通用/初始化模板/`；运行 `python scripts/init-personal-files.py` 后，个人档案生成到工作流约定的位置，并由 `.gitignore` 排除。请只填写生成的本地档案，不要在公开模板中写入个人内容；风格原文样本也请放在忽略范围内。
- `选题库/`、`素材库/`、`数据统计/` 里放的是你的真实内容、第三方素材和业务数据。开源部署时建议整体忽略，只保留目录骨架和模板。
- 不要提交 API Key、Cookie、账号信息、未授权素材和其他敏感数据。

`.gitignore` 已排除本地配置、环境变量、依赖和构建产物；新增工具时请同步维护忽略规则。

## 贡献

提交变更前请：

1. 保持 UTF-8 编码和清晰的 Markdown 结构。
2. 将规则修改同步到受影响的机器合同、Skill、模板与测试。
3. 运行治理审计、工作流校验和全量测试。
4. 在提交说明中写清用户影响、验证结果以及仍未解决的警告。

## 许可证

本项目采用 [MIT License](LICENSE)。第三方依赖仍遵循各自的许可证。
