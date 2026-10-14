# 提示词库

> 存放手动收集或从其他来源整理出来的可复用提示词资产。

## 目录说明

- `_inbox/`：刚收集、还没整理的原始提示词
- `已整理/`：已经完成结构化整理、可直接复用的提示词卡片

## 推荐流程

1. 把原始提示词放到 `素材库/提示词/_inbox/`
2. 调用 `skills/提示词整理师/SKILL.md`
3. 整理完成后移到 `素材库/提示词/已整理/`

## 常用命令

```bash
python scripts/organize-prompts.py --suggest
python scripts/organize-prompts.py --check
python scripts/organize-prompts.py --apply
```
