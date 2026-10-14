from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_report_module():
    path = ROOT / "scripts" / "generate-review-report.py"
    spec = importlib.util.spec_from_file_location("review_report_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_simple_snapshot_metrics() -> None:
    report = load_report_module()
    text = """## 发布后数据

| 平台 | 记录日期 | 阅读量 | 点赞 | 收藏 | 备注（可选） |
|------|---------|-------|------|------|-------------|
| 微信公众号 | 2026-07-27 | 1,200 | 30 | 45 | |

**数据填写状态**：已填写
"""
    platform, metrics, window = report.parse_publish_metrics(text)
    assert platform == "微信公众号"
    assert window == "2026-07-27"
    assert metrics["阅读量"] == 1200
    assert metrics["点赞"] == 30
    assert metrics["收藏"] == 45


def test_legacy_metrics_use_latest_available_window() -> None:
    report = load_report_module()
    text = """## 发布后数据

### 微信公众号

| 指标 | 24h | 72h | 7d |
|------|-----|-----|-----|
| 阅读量 | 100 | 300 | 500 |
| 点赞 | 5 | 10 | 20 |
| 收藏 | 2 | 8 | 15 |
"""
    platform, metrics, window = report.parse_publish_metrics(text)
    assert platform == "微信公众号"
    assert window == "7d"
    assert metrics["阅读量"] == 500
    assert metrics["点赞"] == 20
    assert metrics["收藏"] == 15


def test_final_title_formula_ids_are_traceable() -> None:
    report = load_report_module()
    text = """## 标题备选

**最终选定**：同一素材换个顺序，结果差这么多
**最终公式 ID**：XHS-019 + XHS-056
**最终证据映射**：E02、截图 3-5
"""
    assert report.parse_formula_ids(text) == ["XHS-019", "XHS-056"]
    assert report.formula_category("XHS-019") == "C 反差与意外"
    assert report.formula_category("XHS-056") == "I 案例与复盘"
