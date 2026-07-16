from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from agent_skill_quality_gate.ablation import (
    evaluate_ablation,
    load_variant_specs,
    recommend_variant,
    render_machine_recommendation,
)
from agent_skill_quality_gate.cli import main
from agent_skill_quality_gate.models import VariantMetrics

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ablation"


def _metrics(**changes: object) -> VariantMetrics:
    baseline = VariantMetrics(
        name="baseline",
        role="baseline",
        development_success=1.0,
        held_out_success=0.5,
        retries=1,
        context_cost=300,
        latency_proxy=800,
        negative_triggers=0,
        safety_violations=0,
        evidence_violations=0,
    )
    return replace(baseline, **{"name": "distilled", "role": "distilled", **changes})


def test_ablation_compares_variants_and_promotes_held_out_improvement() -> None:
    evaluation = evaluate_ablation(
        load_variant_specs(FIXTURE_ROOT / "variants.yaml"),
        FIXTURE_ROOT / "cases.yaml",
    )
    metrics_by_role = {metrics.role: metrics for metrics in evaluation.variants}

    assert {metrics.role for metrics in evaluation.variants} == {
        "baseline",
        "bloated",
        "distilled",
    }
    assert metrics_by_role["distilled"].held_out_success == 1.0
    assert metrics_by_role["baseline"].held_out_success < 1.0
    assert metrics_by_role["bloated"].context_cost > metrics_by_role["distilled"].context_cost
    assert evaluation.decision.recommendation == "promote"


def test_recommendation_covers_promote_revise_retire_overfit_and_contract_blocks() -> None:
    baseline = _metrics(name="baseline", role="baseline")

    promoted = recommend_variant(_metrics(held_out_success=1.0), baseline)
    overfit = recommend_variant(_metrics(held_out_success=0.0), baseline)
    unsafe = recommend_variant(_metrics(held_out_success=1.0, safety_violations=1), baseline)
    missing_evidence = recommend_variant(
        _metrics(held_out_success=1.0, evidence_violations=1),
        baseline,
    )
    retired = recommend_variant(_metrics(development_success=0.0, held_out_success=0.0), baseline)

    assert promoted.recommendation == "promote"
    assert overfit.recommendation == "revise"
    assert unsafe.recommendation == "revise"
    assert missing_evidence.recommendation == "revise"
    assert retired.recommendation == "retire"


def test_machine_recommendation_is_stable_json() -> None:
    decision = recommend_variant(
        _metrics(held_out_success=1.0),
        _metrics(name="baseline", role="baseline"),
    )

    payload = json.loads(render_machine_recommendation(decision))

    assert payload["candidate"] == "distilled"
    assert payload["recommendation"] == "promote"
    assert payload["reasons"]


def test_strict_cli_fails_when_variant_cannot_clear_promotion_gate() -> None:
    success = main(
        [
            "skill-eval",
            "--variants",
            str(FIXTURE_ROOT / "variants.yaml"),
            "--case-fixture",
            str(FIXTURE_ROOT / "cases.yaml"),
            "--strict",
        ]
    )
    failure = main(
        [
            "skill-eval",
            "--variants",
            str(FIXTURE_ROOT / "variants-revise.yaml"),
            "--case-fixture",
            str(FIXTURE_ROOT / "cases.yaml"),
            "--strict",
            "--json",
        ]
    )

    assert success == 0
    assert failure == 1
