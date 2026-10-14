from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_validator_module():
    path = ROOT / "scripts" / "validate-workflow.py"
    spec = importlib.util.spec_from_file_location("validate_workflow_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tutorial_text(*, ready: bool) -> str:
    marks = ["x", "x", "x", " ", " ", " ", " "] if ready else [" "] * 7
    state = "ready" if ready else "missing"
    actual = "角色脸、服装和画风在三张结果中保持一致" if ready else ""
    conclusion = "双参考组的角色和画风更稳定，失败点集中在手部" if ready else ""
    screenshot_path = "证据/教程测试/截图/" if ready else ""
    return f"""
## 内容策划

### 文章原型

教程清单型

### 实测任务包

- 测试媒介：AI 绘图
- 测试目标：只比较单参考和双参考对角色一致性的影响
- 测试状态：{state}

#### 输入素材

- 全身角色设定图
- 风格校准图

#### 可复制测试提示词

```text
主体：一个戴蓝色帽子的女孩
场景：坐在书桌前写作
构图：中景，人物位于画面中央
画风：怪诞手绘
光线：柔和侧光
配色：蓝色和米白色
比例：16:9
禁止：换脸、换装、肢体变形、文字乱码
本轮只测试：是否加入风格校准图
预期结果：角色身份和画风在多张图片中保持稳定
```

#### 参数与变量

| 参数 | 固定值 | 本轮变量 | 记录位置 |
|------|--------|----------|----------|
| 比例 | 16:9 | 参考图数量 | 参数截图 |

#### 预期结果与失败信号

- 预期结果：角色稳定
- 失败信号：换脸或换装

#### 截图清单

- [{marks[0]}] 工具和模型选择界面 → 证明测试环境
- [{marks[1]}] 输入素材与完整提示词 → 证明输入一致
- [{marks[2]}] 关键参数 → 证明参数一致
- [{marks[3]}] 第一次完整结果 → 证明原始输出
- [{marks[4]}] 关键细节或失败位置 → 证明判断依据
- [{marks[5]}] 修改前后或 A/B 对照 → 证明变量影响
- [{marks[6]}] 最终可用结果 → 支撑教程结论

#### 实测结果记录

- 测试状态：{state}
- 截图或录屏路径：{screenshot_path}
- 输出文件路径：
- 实际结果：{actual}
- 异常与重试：手部出现一次变形
- 正文可引用结论：{conclusion}
"""


def tutorial_findings(tmp_path: Path, text: str, stage: str):
    validator = load_validator_module()
    validator.ROOT = tmp_path
    path = tmp_path / "选题库" / "待写" / "教程.md"
    findings = []
    stage_index = list(validator.CONTENT_STAGE_STATUS.keys()).index(stage)
    validator.validate_tutorial_test_package(
        path,
        text,
        {"recommended_path": "tutorial", "content_angle": "tutorial"},
        findings,
        True,
        stage_index,
    )
    return findings


def test_tutorial_planned_accepts_ready_to_run_prompt_package(tmp_path: Path) -> None:
    findings = tutorial_findings(tmp_path, tutorial_text(ready=False), "planned")
    assert findings == []


def test_tutorial_assets_ready_rejects_unfinished_test(tmp_path: Path) -> None:
    findings = tutorial_findings(tmp_path, tutorial_text(ready=False), "assets_ready")
    codes = {finding.code for finding in findings}
    assert "content.tutorial_test_not_ready" in codes
    assert "content.tutorial_test_evidence_missing" in codes
    assert "content.tutorial_test_result_missing" in codes


def test_tutorial_assets_ready_accepts_real_results_and_screenshots(tmp_path: Path) -> None:
    findings = tutorial_findings(tmp_path, tutorial_text(ready=True), "assets_ready")
    assert findings == []


def replace_capture_plan(text: str, plan: str) -> str:
    before, rest = text.split("#### 截图清单", 1)
    _, after = rest.split("#### 实测结果记录", 1)
    return before + "#### 截图清单\n\n" + plan + "\n\n#### 实测结果记录" + after


def test_short_tutorial_can_plan_three_meaningful_captures(tmp_path: Path) -> None:
    text = replace_capture_plan(tutorial_text(ready=False), (
        "- [ ] 输入区：记录参考图与完整提示词，证明输入一致\n"
        "- [ ] 设置面板：记录模型和参数，证明操作条件\n"
        "- [ ] 结果页：记录两组完整输出及失败细节，证明变量影响"
    ))
    assert tutorial_findings(tmp_path, text, "planned") == []
    codes = {f.code for f in tutorial_findings(tmp_path, text, "assets_ready")}
    assert "content.tutorial_test_not_ready" in codes
    assert "content.tutorial_test_evidence_missing" in codes
    assert "content.tutorial_test_result_missing" in codes


def test_one_recording_can_be_planned_as_equivalent_evidence(tmp_path: Path) -> None:
    text = replace_capture_plan(tutorial_text(ready=False),
        "- [ ] 录制从输入参考图、设置模型参数到两组输出的完整过程，标注对比位置与失败细节"
    )
    assert tutorial_findings(tmp_path, text, "planned") == []


def test_seven_empty_boxes_do_not_make_a_capture_plan(tmp_path: Path) -> None:
    text = replace_capture_plan(tutorial_text(ready=False), "\n".join(["- [ ]"] * 7))
    codes = {f.code for f in tutorial_findings(tmp_path, text, "planned")}
    assert "content.tutorial_screenshot_plan_incomplete" in codes


def hook_text(*, mode: str, state: str, anchor_status: str = "candidate") -> str:
    return f"""
## 内容策划

### Hook素材增补

- Hook模式：{mode}
- Hook目标：用同任务前后耗时差异说明流程价值
- Hook可用状态：{state}
- 当前最强可用锚点：后台计时记录
- 事实边界：只适用于这一次固定样本测试

| 编号 | 类型 | 候选素材或主张 | 证明什么 | 来源、日期或获取动作 | 状态 | 可用于 |
|---|---|---|---|---|---|---|
| H01 | 数据 | 同任务耗时由 30 分钟降至 12 分钟 | 流程节省时间 | 本地日志；2026-07-29 | {anchor_status} | 开头 |
"""


def hook_findings(tmp_path: Path, text: str, stage: str):
    validator = load_validator_module()
    validator.ROOT = tmp_path
    findings = []
    validator.validate_hook_evidence_supplement(
        tmp_path / "选题库" / "待写" / "Hook.md",
        text,
        findings,
        True,
        stage,
        "standard",
    )
    return findings


def test_hook_planned_allows_candidate_with_clear_collection_boundary(tmp_path: Path) -> None:
    assert hook_findings(
        tmp_path,
        hook_text(mode="evidence", state="candidate"),
        "planned",
    ) == []


def test_hook_assets_ready_requires_verified_anchor_for_evidence_mode(tmp_path: Path) -> None:
    findings = hook_findings(
        tmp_path,
        hook_text(mode="evidence", state="ready", anchor_status="candidate"),
        "assets_ready",
    )
    assert {finding.code for finding in findings} == {
        "content.hook_verified_anchor_missing"
    }


def test_hook_assets_ready_accepts_verified_or_bounded_opinion(tmp_path: Path) -> None:
    assert hook_findings(
        tmp_path,
        hook_text(mode="evidence", state="ready", anchor_status="verified"),
        "assets_ready",
    ) == []
    assert hook_findings(
        tmp_path,
        hook_text(mode="opinion", state="ready"),
        "assets_ready",
    ) == []


def growth_brief_findings(tmp_path: Path, *, complete: bool):
    validator = load_validator_module()
    validator.ROOT = tmp_path
    path = tmp_path / "选题库" / "待写" / "增长稿.md"
    path.parent.mkdir(parents=True)
    text = """
## 原始素材

一条真实素材

## 选题评估

### 判断模块

推荐增长型观点文。

### 第二层思考

帮助读者减少选择成本。

### 角度矩阵

增长角度和核心交付已经明确。

### 核心洞见

一个可验证的判断。

## 内容Brief

目标读者、动作和承诺已经确认。
"""
    frontmatter = {
        "stage": "checked_in",
        "workflow_mode": "standard",
        "content_goal": "growth",
        "brief_audience": "正在选择 AI 工具的内容创作者",
        "brief_user_action": "转发给同事并选择测试工具",
        "brief_core_promise": "给出一套可验证的选择方法",
    }
    if complete:
        frontmatter.update(
            {
                "brief_seed_sharer": "团队里先试工具的人",
                "brief_share_recipient": "正在做工具选型的同事",
                "brief_share_message": "我找到一套少踩坑的判断方法",
            }
        )
    findings = []
    validator.validate_content_gate(path, text, frontmatter, findings)
    return findings


def test_growth_brief_requires_three_share_entry_fields(tmp_path: Path) -> None:
    findings = growth_brief_findings(tmp_path, complete=False)
    assert "content.growth_share_brief_missing" in {
        finding.code for finding in findings
    }


def test_growth_brief_accepts_specific_share_entry(tmp_path: Path) -> None:
    findings = growth_brief_findings(tmp_path, complete=True)
    assert "content.growth_share_brief_missing" not in {
        finding.code for finding in findings
    }


def flagship_style_text(author_presence: str, *, field_name: str = "作者在场设计") -> str:
    checks = "\n".join(f"- [x] {index}. 检查项" for index in range(1, 7))
    return f"""
## 内容策划

### 风格转译

| 项目 | 内容 |
|------|------|
| 调性档位 | B 平实型 |
| 适合本人风格的开头 | 反常识 |
| 可用口语表达 | 按语境选用，不硬塞 |
| {field_name} | {author_presence} |
| 本篇禁用表达 | 不用机械转折 |
| 正文语气基准 | 像给朋友说明筛选结果 |
| 人格姿态自检 | 不装专家，不做中立旁白 |

### 反AI味检查

{checks}
"""


def style_findings(tmp_path: Path, text: str):
    validator = load_validator_module()
    validator.ROOT = tmp_path
    findings = []
    validator.validate_style_chain(
        tmp_path / "选题库" / "待写" / "旗舰稿.md",
        text,
        {"stage": "strategies_generated"},
        findings,
        True,
        "flagship",
    )
    return findings


def test_flagship_style_accepts_routed_author_presence_without_quota(tmp_path: Path) -> None:
    findings = style_findings(
        tmp_path,
        flagship_style_text(
            "正文候选：无，不强行添加；验证边界：未部署，只在范围说明披露；"
            "内部过程日志：浏览器登录与自动化恢复，仅留写作笔记"
        ),
    )
    assert findings == []


def test_flagship_style_rejects_incomplete_author_presence_routing(tmp_path: Path) -> None:
    findings = style_findings(
        tmp_path,
        flagship_style_text("正文候选：作者真实判断；验证边界：无"),
    )
    assert {finding.code for finding in findings} == {
        "content.author_presence_routing_incomplete"
    }


def test_flagship_style_rejects_legacy_humanity_quota_field(tmp_path: Path) -> None:
    findings = style_findings(
        tmp_path,
        flagship_style_text(
            "至少两条折腾经历",
            field_name="必须保留的人味",
        ),
    )
    assert "content.style_translation_incomplete" in {
        finding.code for finding in findings
    }


def opening_findings(tmp_path: Path, opening: str, *, collision_check: bool = True):
    validator = load_validator_module()
    validator.ROOT = tmp_path
    text = f"""
## 正文

{opening}

## 写作笔记

### 风格自检

- 风格档案是否已读取：是
- 开头原型：直接判断
- 近 5 篇撞型检查：{'通过' if collision_check else '不通过'}
- 自检结论：像
"""
    findings = []
    validator.validate_opening_diversity(
        tmp_path / "选题库" / "进行中" / "新稿.md",
        text,
        {"stage": "drafted", "created": "2026-08-31"},
        findings,
        True,
    )
    return findings


def test_opening_diversity_rejects_formulaic_source_action(tmp_path: Path) -> None:
    findings = opening_findings(
        tmp_path,
        "今天整理我的素材时，我刷到一条挺有意思的提示词。",
    )
    assert "content.opening_formula_banned" in {
        finding.code for finding in findings
    }


def test_opening_diversity_rejects_stop_and_difference_shell(tmp_path: Path) -> None:
    findings = opening_findings(
        tmp_path,
        "真正让我停下来看的，是评论和转发之间的差别。",
    )
    assert "content.opening_formula_banned" in {
        finding.code for finding in findings
    }


def test_opening_diversity_accepts_direct_judgment_with_collision_check(tmp_path: Path) -> None:
    findings = opening_findings(
        tmp_path,
        "选公众号题，我现在先看读者读完会做什么。",
    )
    assert findings == []


def flagship_research_text(*, ready: bool) -> str:
    if ready:
        ledger = (
            "| E01 | 产品于 2026-07-01 发布 | 事实 | "
            "https://example.com/release；2026-07-01；访问 2026-07-29 | "
            "一手 | 官方发布页 | 可用 |"
        )
        checks = """
- 纵向线完整：是
- 横向覆盖主要玩家：是
- 时效性事实新鲜：是
- 交叉洞察有双轴证据：是
- 未核实项已隔离：是
- 结论：通过
"""
    else:
        ledger = "| | | | | | | |"
        checks = """
- 纵向线完整：
- 横向覆盖主要玩家：
- 时效性事实新鲜：
- 交叉洞察有双轴证据：
- 未核实项已隔离：
- 结论：通过 / 不通过
"""
    return f"""
## 市场调研

### 深度调研

#### 策划可用结论

- 差异化切口：从用户决策成本切入

#### 证据账本

| 编号 | 主张 | 类型 | 来源与日期 | 证据等级 | 交叉验证 | 使用状态 |
|------|------|------|------------|----------|----------|----------|
{ledger}

#### 信息充分性检查

{checks}
"""


def flagship_research_findings(tmp_path: Path, *, ready: bool):
    validator = load_validator_module()
    validator.ROOT = tmp_path
    findings = []
    validator.validate_flagship_research_evidence(
        tmp_path / "选题库" / "待写" / "旗舰调研.md",
        flagship_research_text(ready=ready),
        findings,
        True,
        "market_researched",
        "flagship",
    )
    return findings


def test_flagship_research_accepts_usable_evidence_and_sufficiency(tmp_path: Path) -> None:
    assert flagship_research_findings(tmp_path, ready=True) == []


def test_flagship_research_rejects_placeholder_evidence(tmp_path: Path) -> None:
    findings = flagship_research_findings(tmp_path, ready=False)
    assert {
        "content.flagship_evidence_ledger_missing",
        "content.flagship_research_sufficiency_incomplete",
        "content.flagship_research_sufficiency_not_passed",
    }.issubset({finding.code for finding in findings})
