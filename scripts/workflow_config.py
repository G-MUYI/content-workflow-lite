from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = ROOT / "选题库"
MATERIAL_ROOT = ROOT / "素材库"


CONTENT_STAGE_STATUS = {
    "raw_idea": "todo",
    "topics_generated": "todo",
    "checked_in": "todo",
    "market_researched": "todo",
    "strategies_generated": "todo",
    "planned": "todo",
    "assets_ready": "todo",
    "drafted": "in_progress",
    "titled": "in_progress",
    "reviewed": "in_progress",
    "published": "done",
    "archived": "archived",
}

CONTENT_DIR_STAGES = {
    "_inbox": {"raw_idea", "topics_generated"},
    "待写": {"checked_in", "market_researched", "strategies_generated", "planned", "assets_ready"},
    "进行中": {"drafted", "titled", "reviewed"},
    "已发布": {"published"},
    "已弃用": {"archived"},
}

CONTENT_ALLOWED_TRANSITIONS = {
    "raw_idea": {"topics_generated", "archived"},
    "topics_generated": {"checked_in", "archived"},
    "checked_in": {"market_researched", "strategies_generated", "archived"},
    "market_researched": {"strategies_generated", "archived"},
    "strategies_generated": {"planned", "archived"},
    "planned": {"assets_ready", "archived"},
    "assets_ready": {"drafted", "archived"},
    "drafted": {"titled", "archived"},
    "titled": {"reviewed", "archived"},
    "reviewed": {"published", "archived"},
    "published": {"archived"},
    "archived": set(),
}

CONTENT_CONDITIONAL_TRANSITIONS = {
    "checked_in": [
        {
            "to": "drafted",
            "condition": "workflow_mode=quick 或 content_form=short_post 或 recommended_path=short_post_first 或 explicit_mode=快速出稿",
            "note": "速发短篇/快速出稿允许跳过市场调研和完整策划。",
        }
    ],
}

CONTENT_CORE_KEYS = [
    "title",
    "status",
    "stage",
    "agent",
    "priority",
    "interrupt_type",
    "source",
    "source_type",
    "tags",
    "created",
    "updated",
]

CONTENT_EXTENDED_KEYS = [
    "source_id",
    "workflow_mode",
    "timeliness_level",
    "recommended_path",
    "content_angle",
    "content_goal",
    "content_form",
    "target_platforms",
    "primary_platform",
    "brief_audience",
    "brief_user_action",
    "brief_core_promise",
    "evidence_status",
    "published_platforms",
    "published_date",
    "voice_anchors",
]

CONTENT_GROWTH_BRIEF_KEYS = [
    "brief_seed_sharer",
    "brief_share_recipient",
    "brief_share_message",
]

CONTENT_UNIT_TYPES = {
    "question",
    "concept",
    "viewpoint",
    "case",
    "solution",
}

CONTENT_UNIT_RELATIONS = {
    "responds_to",
    "explains",
    "proves",
    "conflicts_with",
}

WORKFLOW_MODES = {"quick", "standard", "flagship"}
DEFAULT_WORKFLOW_MODE = "standard"

# 自动推进采用拉动式优先级：越接近发布，越先完成。
# 说明文件只引用此顺序，不再维护另一套可漂移的排序。
NEXT_ACTION_STAGE_ORDER = (
    "reviewed",
    "titled",
    "drafted",
    "assets_ready",
    "planned",
    "strategies_generated",
    "market_researched",
    "checked_in",
    "topics_generated",
    "raw_idea",
)

# WIP 仅限制未指定对象的自动选取；明确指定内容/来源的任务不被改派。
# 调度批次是选取范围，不限制已授权目标内的前置、修复和验证步数。
DELIVERY_TAIL_STAGES = {"drafted", "titled", "reviewed"}
DELIVERY_TAIL_WIP_LIMIT = 3


# 每日多来源选题评分的机器合同。
# 模型只负责按 0-10 给出子分；总分、信源修正、门槛和排序由脚本计算。
DAILY_SOURCE_SCORE_DIMENSIONS = {
    "audience_fit": {
        "label": "受众需求匹配",
        "weight": 25,
        "minimum": 6,
    },
    "information_gain": {
        "label": "信息增量",
        "weight": 20,
        "minimum": 0,
    },
    "actionable_value": {
        "label": "可交付价值",
        "weight": 20,
        "minimum": 6,
    },
    "evidence_readiness": {
        "label": "证据可写性",
        "weight": 25,
        "minimum": 6,
    },
    "timeliness": {
        "label": "时效窗口",
        "weight": 10,
        "minimum": 0,
    },
}

DAILY_SOURCE_TIER_MODIFIERS = {
    "primary": 5,
    "original": 3,
    "reliable_secondary": 0,
    "aggregation": -3,
    "unknown": -5,
}

DAILY_SOURCE_SELECTION_THRESHOLD = 70

DAILY_SOURCE_HARD_BLOCKERS = {
    "duplicate",
    "private_only",
    "source_inaccessible",
}

DAILY_SOURCE_PATH_GATES = {
    "short_post_first": {"timeliness": 7, "evidence_readiness": 6},
    "short_post": {"timeliness": 7, "evidence_readiness": 6},
    "tutorial": {"actionable_value": 7, "evidence_readiness": 7},
    "prompt_list": {"actionable_value": 7, "evidence_readiness": 7},
    "tool_list": {"actionable_value": 7, "evidence_readiness": 7},
    "comparison": {"actionable_value": 7, "evidence_readiness": 7},
    "opinion": {"audience_fit": 7, "information_gain": 7},
    "methodology": {"audience_fit": 7, "information_gain": 7},
    "case": {"audience_fit": 7, "information_gain": 7},
}

# YouMind 每日采集范围与添加时间核实合同。
# 范围固定为「灵感收集」项目；添加时间由 UUIDv7 source_id 解码，由脚本计算。
YOUMIND_SOURCE_BOARD = {
    "name": "灵感收集",
    "board_id": "019a3112-160b-79e9-83dd-2605cc47513e",
}
YOUMIND_DAILY_SOURCE_LIMIT = 5
YOUMIND_ADDED_TIME_UTC_OFFSET_HOURS = 8

ASSET_CORE_KEYS = [
    "title",
    "status",
    "stage",
    "agent",
    "handler_skill",
    "material_type",
    "board_name",
    "source",
    "source_type",
    "source_id",
    "tags",
    "created",
    "updated",
]

KNOWN_SKILLS = {
    "topic-master": "skills/选题大师/SKILL.md",
    "knowledge-gardener": "skills/知识园丁/SKILL.md",
    "prompt-librarian": "skills/提示词整理师/SKILL.md",
    "viral-content-strategist": "skills/爆款内容策划师/SKILL.md",
    "story-writer": "skills/故事化写手/SKILL.md",
    "title-master": "skills/标题大师/SKILL.md",
    "content-reviewer": "skills/审稿编辑/SKILL.md",
    "style-learner": "skills/风格学习师/SKILL.md",
    "xiaohongshu-card-maker": "skills/小红书卡片大师/SKILL.md",
    "video-maker": "skills/视频生成器/SKILL.md",
    "remotion-best-practices": "skills/Remotion最佳实践/SKILL.md",
    "workflow-maintainer": "skills/workflow-maintainer/SKILL.md",
}

QUICK_COMMAND_LINES = [
    "📎 快捷命令",
    "  ┄┄ 工作流（直接说中文）┄┄",
    "  流程 → \"继续\" | \"一键推进\" | \"从头开始\"+素材 | \"快速出稿\" | \"速发\"",
    "  单步 → \"策划\" | \"补钩子素材\" | \"确认素材\" | \"写\" | \"标题\" | \"修稿\" | \"复审\" | \"市场调研\"",
    "  管理 → \"帮我整理inbox\" | \"批量整理历史内容\" | \"弃用：xxx\" | \"这篇发了\" | \"仪表盘\" | \"工作流体检\"",
    "  素材 → \"整理素材\" | \"整理提示词\" | \"查素材\" | \"复盘\" | \"填数据\"",
    "  分发 → \"转小红书\" | \"生成视频\" | \"发个短的\" | \"X版\" | \"朋友圈版\"",
    "  学习 → \"记住xxx\" | \"查看我的风格档案\" | \"本周学到了什么\"",
    "  ┄┄ 系统 Skills（需用英文 /命令）┄┄",
    "  /browse        浏览网页        /qa             自动测试+修复",
    "  /qa-only       仅测试报告      /review         代码审查",
    "  /ship          发布/创建PR     /investigate    调试排错",
    "  /office-hours  头脑风暴        /design-review  视觉走查",
    "  /design-consultation 设计系统  /retro          周回顾",
    "  /plan-ceo-review  战略评审     /plan-eng-review  架构评审",
    "  /plan-design-review 设计评审   /codex          第二意见",
    "  /careful       生产环境保护    /guard          最大安全模式",
    "  /freeze        限定编辑范围    /unfreeze       解除限定",
]

ROUTE_RULES = [
    {
        "intent": "全库 inbox 批量处理",
        "triggers": ["帮我整理inbox", "整理inbox", "整理素材"],
        "target": "workflow-dispatch → inbox-router",
        "preflight": "扫描选题与素材 inbox；提示词素材采用素材库 + 选题库双轨处理",
    },
    {
        "intent": "新素材入库",
        "triggers": ["从头开始", "帮我选题", "今天写什么"],
        "target": "topic-master",
        "preflight": "收到链接、想法或文案时先创建 _inbox 文件",
    },
    {
        "intent": "整理选题 inbox",
        "triggers": ["整理选题inbox", "整理选题 inbox"],
        "target": "topic-master",
        "preflight": "仅处理选题 inbox 中 stage=raw_idea 的文件",
    },
    {
        "intent": "确认选题入库",
        "triggers": ["确认入库", "确认选题"],
        "target": "topic-master",
        "preflight": "stage 应为 topics_generated；用户需要明确选择主推角度",
    },
    {
        "intent": "整理提示词资产",
        "triggers": ["整理提示词", "处理提示词集"],
        "target": "prompt-librarian → topic-master",
        "preflight": "整理提示词后同步创建或维护 prompt_list 选题 handoff",
    },
    {
        "intent": "提示词补全建议",
        "triggers": ["提示词补全建议", "批量补提示词"],
        "target": "scripts/organize-prompts.py --suggest",
        "preflight": "只读列出提示词卡片缺口",
    },
    {
        "intent": "提示词归档",
        "triggers": ["归档提示词", "整理完成提示词"],
        "target": "scripts/organize-prompts.py --apply",
        "preflight": "只归档通过完整性检查的提示词，并维护 handoff",
    },
    {
        "intent": "素材库检索",
        "triggers": ["查素材", "写之前查一下素材", "有没有写过"],
        "target": "knowledge-gardener",
        "preflight": "检索素材库与历史内容",
    },
    {
        "intent": "内容单元整理",
        "triggers": ["拆成内容单元", "整理内容单元", "建立素材关系"],
        "target": "knowledge-gardener",
        "preflight": "拆为 question / concept / viewpoint / case / solution，并登记 responds_to / explains / proves / conflicts_with 关系",
    },
    {
        "intent": "市场调研",
        "triggers": ["市场调研", "看看别人怎么写"],
        "target": "knowledge-gardener",
        "preflight": "标准模式按需执行，旗舰模式默认执行",
    },
    {
        "intent": "内容策划",
        "triggers": ["策划", "开始策划", "出大纲"],
        "target": "viral-content-strategist",
        "preflight": "stage 应为 checked_in、market_researched 或 strategies_generated",
    },
    {
        "intent": "Hook 素材增补",
        "triggers": ["补钩子素材", "开头补素材", "增补数据案例权威", "补开头证据"],
        "target": "viral-content-strategist → knowledge-gardener",
        "preflight": "优先处理 strategies_generated 或 planned；只把 verified 锚点标为标题和正文可用",
    },
    {
        "intent": "确认大纲",
        "triggers": ["确认大纲"],
        "target": "viral-content-strategist",
        "preflight": "stage 应为 strategies_generated；确认结构与派活清单后进入 planned",
    },
    {
        "intent": "正文写作",
        "triggers": ["写", "开始写", "写文章"],
        "target": "story-writer",
        "preflight": "标准/旗舰长文需要 assets_ready；short_post 可从 checked_in 速发",
    },
    {
        "intent": "素材准备确认",
        "triggers": ["确认素材", "素材准备好了", "准备好了"],
        "target": "workflow-dispatch → assets-ready",
        "preflight": "stage 应为 planned；教程类须完成实测任务包、至少 3 张关键截图或等价证据和实测结论，其他文章确认关键支撑已准备好",
    },
    {
        "intent": "短篇速发",
        "triggers": ["速发", "短篇速发", "快速出稿", "发个短的", "X版", "朋友圈版", "公众号短文"],
        "target": "topic-master → story-writer",
        "preflight": "新素材先完成最小选题确认，已有 short_post 可直接写",
    },
    {
        "intent": "补风格链路",
        "triggers": ["补风格链路"],
        "target": "story-writer",
        "preflight": "补齐风格自检或必要风格基线，不改变当前 stage",
    },
    {
        "intent": "继续推进",
        "triggers": ["继续"],
        "target": "workflow-dispatch → next-stage skill",
        "preflight": "指定对象时继续原任务，否则按配置选取；常规选择与缺口修复自主执行，真实证据门禁保留",
    },
    {
        "intent": "一键推进",
        "triggers": ["一键推进", "自动推进"],
        "target": "workflow-dispatch → next-stage skill",
        "preflight": "未指定对象时每轮选择最多 3 篇；选定后完成阶段目标及必要前置，不按步骤数提前停止；明确人工选择或新增外部影响按会话授权处理",
    },
    {
        "intent": "弃用归档",
        "triggers": ["弃用"],
        "target": "workflow-dispatch",
        "preflight": "目标更新为 archived 并移动到已弃用目录",
    },
    {
        "intent": "发布归档",
        "triggers": ["这篇发了", "发布到公众号", "发布到微信", "发布到小红书", "发布到知乎", "发布归档", "归档发布"],
        "target": "scripts/publish-content.py",
        "preflight": "只允许 reviewed 文件；必须明确发布平台",
    },
    {
        "intent": "发布数据补录",
        "triggers": ["填数据", "补数据"],
        "target": "knowledge-gardener",
        "preflight": "处理已发布但尚无有效数据的文章",
    },
    {
        "intent": "发布数据复盘",
        "triggers": ["复盘", "看数据", "生成复盘草案", "自动复盘"],
        "target": "scripts/generate-review-report.py",
        "preflight": "只纳入有有效阅读数据的文章；无数据时停止",
    },
    {
        "intent": "校验发布复盘",
        "triggers": ["校验发布复盘", "检查发布数据"],
        "target": "scripts/validate-publish-review.py",
        "preflight": "检查发布元数据、数据填写状态和复盘记录",
    },
    {
        "intent": "查看仪表盘",
        "triggers": ["仪表盘", "看仪表盘", "选题库状态"],
        "target": "scripts/run-opening-protocol.py",
        "preflight": "只读扫描当前工作区",
    },
    {
        "intent": "校验工作流",
        "triggers": ["校验工作流", "检查结构"],
        "target": "scripts/validate-workflow.py",
        "preflight": "检查目录、stage、status、字段与阶段门禁",
    },
    {
        "intent": "工作流治理收尾",
        "triggers": ["工作流体检", "工作流收尾", "规则审计", "治理审计"],
        "target": "workflow-maintainer",
        "preflight": "仅审计请求只读；要求优化或修复时编辑真实依赖并验证；清理按既有授权和保全边界处理",
    },
    {
        "intent": "分级扩张批处理",
        "triggers": ["批量整理历史内容", "批量迁移历史内容", "分级扩张"],
        "target": "workflow-maintainer → scripts/plan-batch-expansion.py",
        "preflight": "先只读审计，再处理最多 5 个或 10% 的小样本；验证通过后才能分批扩大",
    },
    {
        "intent": "查看触发路由",
        "triggers": ["查看触发路由", "技能路由"],
        "target": "scripts/workflow-dispatch.py --routes",
        "preflight": "只读展示命令、Skill 与前置条件",
    },
    {
        "intent": "标题优化",
        "triggers": ["标题", "起标题", "优化标题", "确认标题"],
        "target": "title-master",
        "preflight": "drafted 可生成候选；用户或授权模型完成终选并保存依据、公式与证据映射后进入 titled；返修标题需重验时保持 titled 校准",
    },
    {
        "intent": "标题复盘训练",
        "triggers": ["标题复盘", "标题训练", "帮我改旧标题", "拿这几篇练标题"],
        "target": "title-master",
        "preflight": "读取 3-5 篇内容，每篇至少改写 5 个标题并说明理由",
    },
    {
        "intent": "审稿质检",
        "triggers": ["审稿", "复审", "重新审稿", "检查"],
        "target": "content-reviewer",
        "preflight": "stage 应为 titled",
    },
    {
        "intent": "审稿返修",
        "triggers": ["修稿", "按审稿意见修改", "根据审稿修改"],
        "target": "story-writer",
        "preflight": "stage 应为 titled 且已有未通过的审稿记录；返修保持 titled，必要时先重跑标题再复审",
    },
    {
        "intent": "分发卡片",
        "triggers": ["转小红书", "做卡片", "做成卡片"],
        "target": "xiaohongshu-card-maker",
        "preflight": "读取 drafted 及以上内容或 planned 大纲，生成后回写分发素材",
    },
    {
        "intent": "生成视频",
        "triggers": ["生成视频", "做成视频", "转视频"],
        "target": "video-maker",
        "preflight": "最低 stage 为 planned；生成后回写分发素材",
    },
    {
        "intent": "素材反哺",
        "triggers": ["整理素材库"],
        "target": "knowledge-gardener",
        "preflight": "从已发布文章提炼候选金句、概念和结构，不自动修改方法论",
    },
    {
        "intent": "学习个人风格",
        "triggers": ["学习我的风格", "学习这篇爆款", "记录这次反馈", "学习我的修改"],
        "target": "style-learner",
        "preflight": "先记录原文或修改证据，再更新风格档案",
    },
    {
        "intent": "查看学习档案",
        "triggers": ["查看我的风格档案", "我的偏好", "本周学到了什么"],
        "target": "style-learner",
        "preflight": "只读汇总偏好、风格档案和最近反馈",
    },
    {
        "intent": "会话记忆管理",
        "triggers": ["上次说到哪了", "继续上次的", "记住这个偏好", "否决这个方向", "记录待验证假设", "暂停自动学习", "恢复自动学习"],
        "target": "workflow-dispatch → session-memory",
        "preflight": "读取或更新当前任务、已否决方向、待验证假设和用户偏好，不修改内容文件",
    },
    {
        "intent": "版本记录",
        "triggers": ["存档记录", "历史"],
        "target": "git log",
        "preflight": "只读展示最近 10 条提交",
    },
    {
        "intent": "版本推送",
        "triggers": ["推送", "同步"],
        "target": "git push",
        "preflight": "先确认分支、提交和远端，不隐式提交未确认文件",
    },
    {
        "intent": "版本回退",
        "triggers": ["撤回", "回退", "不要了"],
        "target": "workflow-dispatch → safe-revert",
        "preflight": "先展示目标和影响，只执行可恢复回退",
    },
]
