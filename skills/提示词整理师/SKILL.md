---
name: prompt-librarian
description: |
  提示词整理师，负责把提示词集中的原始素材整理成可复用提示词资产。
  Use when: (1) 用户说"整理提示词"、"处理提示词集", (2) `素材库/提示词/_inbox/` 有待整理文件, (3) 用户说"帮我整理inbox"或"整理素材"且提示词 inbox 有待处理文件, (4) 需要把零散提示词整理成标准卡片。
---

# 提示词整理师 (Prompt Librarian)

> 规则边界：本文是执行卡。资产 schema 与命令路由以 `../../AGENTS.md` 与 `../../scripts/workflow_config.py` 为准。

> 目标很直接：把原始提示词整理成可复用、可检索、可继续优化的资产。

> 协作边界：自主选择、澄清、批准和完成统一按 `../../AGENTS.md` 的“自主执行、澄清与完成”；下文步骤不构成逐步审批，职责切换由当前 Agent 完成。

## 适用输入

- `素材库/提示词/_inbox/` 下的同步文件
- 用户手动贴过来的零散提示词
- 已有提示词卡片，需要重新整理结构

## 与选题库的关系

本 Skill 处理的是 `素材库/提示词/` 目录下的**提示词资产文件**，使用独立 schema，不共享选题库（`选题库/`）的 stage 状态机。

但提示词素材必须走**双轨**：资产文件留在提示词素材库，同时为写文章流程创建/更新一份关联选题文件。也就是说，提示词资产文件本身不要移动到 `选题库/`，但不能让它从选题流程里消失。

| 字段 | 选题库 | 提示词素材库 |
|------|--------|------------|
| `stage` | `raw_idea → checked_in → planned → drafted → reviewed → published` | `collected → organized` |
| `material_type` | — | `prompt_asset` |
| 关联方式 | `source_id + content_angle: prompt_list` | `source_id + content_handoff_file` |

不要把提示词资产文件当成选题文件来处理；要生成一份关联选题副本给选题大师处理。



## 工作原则

1. **保留原文**：不要覆盖 `## 原始素材`
2. **只做结构化整理**：把散乱内容变成标准提示词卡片
3. **优先提炼复用价值**：明确适用场景、输入变量、完整提示词、预期输出
4. **不擅自发明复杂变量**：如果原素材没有，就保持简单

## 处理流程

### Step 1：读取与判断

1. 读取目标文件
2. 优先处理：
   - `素材库/提示词/_inbox/`
   - `stage: collected`
   - `material_type: prompt_asset`
3. 判断这份素材属于哪类提示词：
   - 单条万能提示词
   - 场景模板型
   - 多轮工作流型
   - 改写/润色型
   - 分析/提取型

### Step 2：写入标准结构

填写 `## 提示词拆解`：

- `### 适用场景`
- `### 输入变量`
- `### 完整提示词`
- `### 使用说明`
- `### 预期输出`

填写 `## 优化建议`：

- 当前提示词的强项
- 哪些变量还可以抽象
- 哪些输出格式需要固定
- 是否值得后续沉淀成系列模板

### Step 3：落盘与归档

1. 更新 YAML：
   - `agent: "prompt-librarian"`
   - `updated: [今天日期]`
   - 若没有 `source_id`，补一个稳定的同素材簇 ID
   - `content_handoff: done`
   - `content_handoff_file: "选题库/_inbox/[关联选题文件].md"`
2. 同步创建/更新关联选题：
   - 位置：`选题库/_inbox/`
   - YAML：`stage: raw_idea`、`agent: "topic-master"`、`recommended_path: "prompt_list"`、`content_angle: "prompt_list"`、`content_goal: "collect"`
   - `## 原始素材` 必须保留提示词资产路径、原始素材摘录、提示词拆解摘录
   - 如果已存在相同 `source_id + content_angle: prompt_list` 的选题文件，引用/更新原文件，不新建
   - 只有用户明确说"只入库提示词，不做文章"或 YAML 为 `content_handoff: skipped`，才跳过这一步
3. 如果整理完成，可把文件从 `素材库/提示词/_inbox/` 移到 `素材库/提示词/已整理/`
   - 批量补全建议：`python scripts/organize-prompts.py --suggest`
   - 可执行：`python scripts/organize-prompts.py --check`
   - 执行归档：`python scripts/organize-prompts.py --apply`
4. 如果素材还太乱，保留在 `_inbox/`，并在 `## 优化建议` 写明缺什么；但仍要提醒它后续会双轨转交选题

## 输出标准

整理完成后，这张卡片至少要让用户一眼看到：

1. 这条提示词拿来干什么
2. 输入时要替换哪些变量
3. 完整版本能不能直接复制
4. 输出应该长什么样

## 不要做的事

- 不要删除原始链接和原始备注
- 不要把提示词资产文件直接塞进 `选题库/`
- 不要只整理提示词资产而忘记创建关联选题
- 不要在未获得用户明确授权时把 `content_handoff` 标成 `skipped`
- 不要为了显得高级，强行把简单提示词改写成复杂模板

## 推荐目录

- 待整理：`素材库/提示词/_inbox/`
- 已整理：`素材库/提示词/已整理/`

## 常用触发词

- `整理提示词`
- `处理提示词集`
- `把这条提示词入库`
- `把提示词整理成模板`
