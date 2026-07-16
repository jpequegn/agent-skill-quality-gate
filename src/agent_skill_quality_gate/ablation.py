"""Offline ablation scoring and promotion decisions for reusable skill variants."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

import yaml

from .analyzer import analyze_skill
from .evaluation import evaluate_selection, load_workflow_cases
from .models import (
    AblationEvaluation,
    PromotionDecision,
    SelectionOutcome,
    SkillEvaluationError,
    VariantMetrics,
    VariantRole,
    VariantSpec,
    WorkflowCase,
)
from .parser import parse_skill_tree

_ROLES = frozenset({"baseline", "bloated", "distilled"})
_SAFETY_RULES = frozenset({"RAW_LOG_GUIDANCE_UNSAFE"})


def _required_string(raw: Mapping[str, object], field: str, path: Path) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SkillEvaluationError(f"{path}: variant field '{field}' must be a non-empty string.")
    return value.strip()


def load_variant_specs(path: Path) -> tuple[VariantSpec, ...]:
    """Load a constrained local variant manifest without accessing external resources."""

    try:
        raw_document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SkillEvaluationError(f"{path}: unable to read variant manifest.") from error
    except yaml.YAMLError as error:
        raise SkillEvaluationError(f"{path}: malformed YAML variant manifest.") from error
    if not isinstance(raw_document, Mapping) or not isinstance(raw_document.get("variants"), list):
        raise SkillEvaluationError(f"{path}: variant manifest must contain a variants list.")

    manifest_root = path.resolve().parent
    specs: list[VariantSpec] = []
    names: set[str] = set()
    roles: set[str] = set()
    for index, raw_variant in enumerate(raw_document["variants"], start=1):
        if not isinstance(raw_variant, Mapping):
            raise SkillEvaluationError(f"{path}: variant {index} must be a mapping.")
        name = _required_string(raw_variant, "name", path)
        role = _required_string(raw_variant, "role", path)
        relative_root = _required_string(raw_variant, "root", path)
        if name in names:
            raise SkillEvaluationError(f"{path}: variant name '{name}' is duplicated.")
        if role not in _ROLES or role in roles:
            raise SkillEvaluationError(f"{path}: each variant role must appear exactly once.")
        candidate_root = (manifest_root / relative_root).resolve()
        try:
            candidate_root.relative_to(manifest_root)
        except ValueError as error:
            message = f"{path}: variant root escapes the manifest directory."
            raise SkillEvaluationError(message) from error
        names.add(name)
        roles.add(role)
        specs.append(
            VariantSpec(name=name, role=cast(VariantRole, role), root=candidate_root)
        )
    if roles != _ROLES:
        message = f"{path}: baseline, bloated, and distilled variants are required."
        raise SkillEvaluationError(message)
    return tuple(sorted(specs, key=lambda spec: spec.role))


def _success_rate(
    outcomes: Iterable[SelectionOutcome],
    violated_cases: set[str],
) -> tuple[float, int]:
    outcome_list = tuple(outcomes)
    if not outcome_list:
        return 0.0, 0
    successful = sum(
        outcome.is_correct and outcome.case_id not in violated_cases
        for outcome in outcome_list
    )
    return successful / len(outcome_list), len(outcome_list) - successful


def score_variant(spec: VariantSpec, cases: Iterable[WorkflowCase]) -> VariantMetrics:
    """Run the selection and contract rubric against one local skill variant."""

    cards = parse_skill_tree(spec.root).cards
    evaluation = evaluate_selection(cards, cases)
    violated_cases = {violation.case_id for violation in evaluation.contract_violations}
    development_success, development_retries = _success_rate(
        (outcome for outcome in evaluation.outcomes if outcome.split == "development"),
        violated_cases,
    )
    held_out_success, held_out_retries = _success_rate(
        (outcome for outcome in evaluation.outcomes if outcome.split == "held-out"),
        violated_cases,
    )
    static_safety = sum(
        finding.rule_id in _SAFETY_RULES
        for card in cards
        for finding in analyze_skill(card).findings
    )
    contract_safety = sum(
        violation.code == "FORBIDDEN_INSTRUCTION_PRESENT"
        for violation in evaluation.contract_violations
    )
    return VariantMetrics(
        name=spec.name,
        role=spec.role,
        development_success=development_success,
        held_out_success=held_out_success,
        retries=development_retries + held_out_retries,
        context_cost=sum(card.context_character_count for card in cards),
        latency_proxy=sum(card.context_character_count for card in cards)
        + (development_retries + held_out_retries) * 500,
        negative_triggers=sum(
            not outcome.should_trigger and outcome.selected_skill is not None
            for outcome in evaluation.outcomes
        ),
        safety_violations=static_safety + contract_safety,
        evidence_violations=sum(
            violation.code == "REQUIRED_ARTIFACT_MISSING"
            for violation in evaluation.contract_violations
        ),
    )


def recommend_variant(
    candidate: VariantMetrics,
    baseline: VariantMetrics,
) -> PromotionDecision:
    """Apply a small, explainable rubric to the distilled candidate."""

    if candidate.development_success == 0 and candidate.held_out_success == 0:
        return PromotionDecision(
            candidate=candidate.name,
            recommendation="retire",
            reasons=("No useful development or held-out selection success remains.",),
        )

    reasons: list[str] = []
    if candidate.negative_triggers:
        reasons.append("Negative workflow cases triggered the candidate.")
    if candidate.safety_violations:
        reasons.append("Safety checks found blocking violations.")
    if candidate.evidence_violations:
        reasons.append("Required evidence is not declared by the candidate.")
    if candidate.held_out_success < candidate.development_success:
        reasons.append("Development success did not transfer to held-out fixtures.")
    if candidate.held_out_success <= baseline.held_out_success:
        reasons.append("Held-out success did not exceed the baseline.")
    if reasons:
        return PromotionDecision(
            candidate=candidate.name,
            recommendation="revise",
            reasons=tuple(reasons),
        )
    return PromotionDecision(
        candidate=candidate.name,
        recommendation="promote",
        reasons=("Held-out success exceeded baseline without blocking violations.",),
    )


def evaluate_ablation(variants: Iterable[VariantSpec], cases_path: Path) -> AblationEvaluation:
    """Evaluate baseline, bloated, and distilled local variants against one fixture set."""

    cases = load_workflow_cases(cases_path)
    metrics = tuple(score_variant(spec, cases) for spec in variants)
    metrics_by_role = {metric.role: metric for metric in metrics}
    if set(metrics_by_role) != _ROLES:
        raise SkillEvaluationError(
            "Ablation evaluation requires baseline, bloated, and distilled roles."
        )
    decision = recommend_variant(metrics_by_role["distilled"], metrics_by_role["baseline"])
    return AblationEvaluation(
        variants=tuple(sorted(metrics, key=lambda metric: metric.role)),
        decision=decision,
    )


def render_machine_recommendation(decision: PromotionDecision) -> str:
    """Return a stable JSON recommendation for CI or local automation."""

    payload = {
        "candidate": decision.candidate,
        "recommendation": decision.recommendation,
        "reasons": list(decision.reasons),
    }
    return json.dumps(payload, sort_keys=True) + "\n"


def promotion_passes(decision: PromotionDecision) -> bool:
    """Return whether a strict CI gate may pass."""

    return decision.recommendation == "promote"
