from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_audit_module():
    path = ROOT / "scripts" / "audit-workflow-governance.py"
    spec = importlib.util.spec_from_file_location("workflow_governance_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_governance_audit_has_no_errors() -> None:
    audit = load_audit_module()
    report = audit.build_report()
    errors = [
        finding
        for finding in report["findings"]
        if finding["level"] == "error"
    ]
    assert errors == []


def test_agents_core_stays_below_warning_budget() -> None:
    audit = load_audit_module()
    assert (ROOT / "AGENTS.md").stat().st_size <= audit.WARNING_BUDGET
