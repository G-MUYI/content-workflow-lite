from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_ranker_module():
    path = ROOT / "scripts" / "rank-daily-sources.py"
    spec = importlib.util.spec_from_file_location("rank_daily_sources_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidate(
    candidate_id: str,
    *,
    source_tier: str = "original",
    path: str = "methodology",
    scores: dict[str, int] | None = None,
    blockers: list[str] | None = None,
):
    return {
        "id": candidate_id,
        "title": f"候选 {candidate_id}",
        "source_tier": source_tier,
        "recommended_path": path,
        "scores": scores
        or {
            "audience_fit": 8,
            "information_gain": 8,
            "actionable_value": 8,
            "evidence_readiness": 8,
            "timeliness": 5,
        },
        "blockers": blockers or [],
    }


def test_ranker_uses_fixed_formula_and_selects_highest_eligible() -> None:
    ranker = load_ranker_module()
    result = ranker.rank_candidates(
        {
            "candidates": [
                candidate("secondary", source_tier="reliable_secondary"),
                candidate("primary", source_tier="primary"),
            ]
        }
    )

    assert result["selected_id"] == "primary"
    assert result["candidates"][0]["total_score"] == 82.0
    assert result["candidates"][0]["eligible"] is True


def test_ranker_never_selects_duplicate_or_evidence_poor_candidate() -> None:
    ranker = load_ranker_module()
    weak_evidence = candidate(
        "weak",
        scores={
            "audience_fit": 10,
            "information_gain": 10,
            "actionable_value": 10,
            "evidence_readiness": 5,
            "timeliness": 10,
        },
    )
    result = ranker.rank_candidates(
        {
            "candidates": [
                candidate("duplicate", blockers=["duplicate"]),
                weak_evidence,
            ]
        }
    )

    assert result["selected_id"] is None
    assert all(not item["eligible"] for item in result["candidates"])


def test_ranker_applies_path_specific_gate() -> None:
    ranker = load_ranker_module()
    result = ranker.rank_candidates(
        {
            "candidates": [
                candidate(
                    "tutorial",
                    path="tutorial",
                    scores={
                        "audience_fit": 9,
                        "information_gain": 9,
                        "actionable_value": 6,
                        "evidence_readiness": 9,
                        "timeliness": 8,
                    },
                )
            ]
        }
    )

    assert result["selected_id"] is None
    assert "tutorial 门槛" in "；".join(result["candidates"][0]["reasons"])
