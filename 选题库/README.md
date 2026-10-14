# 选题库

> 用md文件和文件夹管理你的选题全生命周期

---

## 文件夹结构

```
选题库/
├── _inbox/              # 📥 待处理的原始素材
├── _模板/              # 📋 选题模板
├── 待写/                # ⏳ 已确认但还没写的选题
├── 进行中/              # ✍️ 正在写的选题
├── 已发布/              # ✅ 已发布的选题（归档）
│   └── 2026/           # 按年份归档
│       └── 01/         # 按月份归档
└── 已弃用/              # 🗑️ 弃用的选题
```

---

## 选题状态流转

```
raw_idea → topics_generated → checked_in → market_researched
                                      └→ strategies_generated → planned → drafted → titled → reviewed → published
任意 stage → archived
```

---

## 爆款评估体系（7维度）

每个选题都用7个维度评估爆款潜力：

| 维度 | 权重 | 满分条件 |
|------|-----|---------|
| **打断力** | ⭐⭐⭐ | 意外+相关+紧迫，至少占2个 |
| **认知刷新** | ⭐⭐⭐ | 读完觉得"原来是这样" |
| **人性触发** | ⭐⭐ | 懒/贪/怕/好奇/虚荣/掌控 |
| **身份锚定** | ⭐⭐ | 一眼知道是写给谁的 |
| **作品支撑** | ⭐⭐⭐ | 有具体案例/数字/经历 |
| **可收藏性** | ⭐⭐ | 有模板/清单/提示词可带走 |
| **工作量** | ⭐ | 预估投入 |

> **维度名称固定**：不要使用变体（如"认知颠覆"、"情绪共振"、"你独有"、"可写性"）。

### 爆款潜力等级

| 等级 | 条件 | 建议 |
|------|------|------|
| 🔥🔥🔥 S级 | 6维度全满 | 立刻写 |
| 🔥🔥 A级 | 5维度满 | 优先写 |
| 🔥 B级 | 4维度满 | 可以写 |
| ⚪ C级 | 3个及以下 | 暂缓或换角度 |

---

## 文件命名规范

### 选题文件

```
[等级]-[打断要素]-选题标题.md
```

**等级**：S级 / A级 / B级 / C级

**打断要素**：意外 / 相关 / 紧迫

**示例**：
```
S级-意外-自律是个谎言.md
A级-相关-给想用AI但不知道从哪开始的人.md
B级-紧迫-这个红利窗口只剩3个月.md
```

### 原始素材文件

```
[日期]-[来源]-简短描述.md
```

**示例**：
```
20260122-经历-用AI三天赚了3000.md
20260122-文章-某公众号的选题方法.md
```

---

## 使用方法

### 1. 投喂原始素材

把任何想法、经历、看到的东西扔进 `_inbox/` 文件夹。

日常更推荐直接说自然语言：

- `看仪表盘`
- `整理提示词`
- `归档提示词`
- `检查发布复盘`
- `生成复盘草案`

命令行主要是给底层脚本和批处理用，不是日常主入口。

如果要校验当前工作流结构、素材库结构和历史内容问题：

```bash
python scripts/validate-workflow.py
```

如果要补齐活动文件和已发布文件的 schema：

```bash
python scripts/migrate-content-schema.py --check
python scripts/migrate-content-schema.py --apply
```

如果要直接看当前开局仪表盘：

```bash
python scripts/run-opening-protocol.py
python scripts/opening-dashboard.py
```

如果要把整理完成的提示词从 `_inbox` 归档到 `已整理`：

```bash
python scripts/organize-prompts.py --suggest
python scripts/organize-prompts.py --check
python scripts/organize-prompts.py --apply
```

如果要单独检查发布后数据和复盘流程：

```bash
python scripts/validate-publish-review.py
```

如果要基于当前已发布数据生成复盘草案：

```bash
python scripts/generate-review-report.py
python scripts/generate-review-report.py --output "数据统计/2026-03-W2-复盘-自动生成.md"
```

如果要把历史发布文章和周复盘从 6 维度迁到 7 维度：

```bash
python scripts/migrate-review-dimensions.py
python scripts/migrate-review-dimensions.py --apply
```

### 2. 加工成选题

调用 **选题大师**，它会：
- 生成5个选题（不是10个）
- 每个选题带7维度评估
- 给出爆款潜力等级
- 推荐Top 3

### 3. 按需裂变

对感兴趣的选题说"帮我裂变xxx"，才会展开子选题。

### 4. 开始写作

把选题从 `待写/` 移到 `进行中/`。

### 5. 发布归档

发布后移到 `已发布/YYYY/MM/`。

---

## 快速命令

```
选题库状态          # 查看库存统计
帮我整理inbox      # 处理待处理素材
今天写什么         # 推荐当前最该写的选题
帮我裂变xxx        # 展开某个选题的子选题
开始写xxx          # 把选题移到进行中
这篇发了           # 发布归档
```

---

## 注意事项

1. **不要堆积**：`_inbox/` 里的素材最好当天处理
2. **优先S级**：S级选题超过3天没写，就浪费了
3. **及时弃用**：超过2周没动的选题，考虑移到 `已弃用/`
4. **定期复盘**：每周看看发了什么、弃了什么、7维度预判准不准
5. **版本控制**：每次阶段性操作后自动 commit，支持回滚

---

