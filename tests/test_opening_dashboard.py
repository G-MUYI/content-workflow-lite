from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dashboard_module():
    path = ROOT / "scripts" / "opening-dashboard.py"
    spec = importlib.util.spec_from_file_location("opening_dashboard_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_item(path: Path, *, title: str, stage: str, days_old: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    updated = (date.today() - timedelta(days=days_old)).isoformat()
    path.write_text(
        "---\n"
        f"title: {title}\n"
        f"stage: {stage}\n"
        "status: in_progress\n"
        "priority: A\n"
        f"created: {updated}\n"
        f"updated: {updated}\n"
        "---\n",
        encoding="utf-8",
    )


def test_dashboard_deduplicates_item_alerts_and_uses_queue_bottleneck(tmp_path: Path) -> None:
    dashboard = load_dashboard_module()
    dashboard.TOPIC_ROOT = tmp_path / "选题库"
    dashboard.MATERIAL_ROOT = tmp_path / "素材库"
    dashboard.STATS_ROOT = tmp_path / "数据统计"
    dashboard.SESSION_FILE = tmp_path / "会话记忆.md"
    dashboard.PREFERENCES_FILE = tmp_path / "用户偏好.md"

    for index in range(3):
        write_item(
            dashboard.TOPIC_ROOT / "进行中" / f"draft-{index}.md",
            title=f"草稿{index}",
            stage="drafted",
            days_old=30,
        )
    write_item(
        dashboard.TOPIC_ROOT / "待写" / "checked-in.md",
        title="单篇旧选题",
        stage="checked_in",
        days_old=60,
    )

    output = dashboard.build_dashboard()
    alarm_section = output.split("⚠️ 告警", 1)[1].split("🔴 进行中", 1)[0]

    assert "最大瓶颈: drafted (3 篇，累计停留 90 天，平均 30.0 天)" in output
    assert "交付尾部 WIP: 3 / 3篇" in output
    assert "达到或超过 WIP 上限 3 篇" in alarm_section
    for index in range(3):
        assert alarm_section.count(f"《草稿{index}》") == 1
    assert "超过 14 天未更新" not in alarm_section
