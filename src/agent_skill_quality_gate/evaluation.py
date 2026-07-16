"""Deterministic, local selection evaluation for reusable skill cards."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import yaml

from .models import (
    ContractViolation,
    SelectionEvaluation,
    SelectionMetrics,
    SelectionOutcome,
    SkillCard,
    SkillEvaluationError,
    WorkflowCase,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "from",
        "in",
        "is",
        "needs",
        "of",
        "or",
        "the",
        "this",
        "to",
        "use",
        "with",
    }
)
_SPLITS = ("development", "held-out")


def _terms(text: str) -> frozenset[str]:
    return frozenset(
        token.casefold()
        for token in _TOKEN_PATTERN.findall(text)
        if len(token) > 2 and token.casefold() not in _STOP_WORDS
    )


def _required_string(raw: Mapping[str, object], field: str, path: Path) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SkillEvaluationError(f"{path}: case field '{field}' must be a non-empty string.")
    return value.strip()


def _string_list(raw: Mapping[str, object], field: str, path: Path) -> tuple[str, ...]:
    value = raw.get(field, [])
    valid_items = isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )
    if not valid_items:
        message = f"{path}: case field '{field}' must be a list of non-empty strings."
        raise SkillEvaluationError(message)
    return tuple(item.strip() for item in value)


def load_workflow_cases(path: Path) -> tuple[WorkflowCase, ...]:
    """Read synthetic test cases only; no runtime traces or request logs are stored."""

    try:
        raw_document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SkillEvaluationError(f"{path}: unable to read evaluation fixture.") from error
    except yaml.YAMLError as error:
        raise SkillEvaluationError(f"{path}: malformed YAML evaluation fixture.") from error

    if not isinstance(raw_document, Mapping) or not isinstance(raw_document.get("cases"), list):
        raise SkillEvaluationError(f"{path}: evaluation fixture must contain a cases list.")

    cases: list[WorkflowCase] = []
    case_ids: set[str] = set()
    for index, raw_case in enumerate(raw_document["cases"], start=1):
        if not isinstance(raw_case, Mapping):
            raise SkillEvaluationError(f"{path}: case {index} must be a mapping.")
        case_id = _required_string(raw_case, "id", path)
        if case_id in case_ids:
            raise SkillEvaluationError(f"{path}: case id '{case_id}' is duplicated.")
        case_ids.add(case_id)
        split = _required_string(raw_case, "split", path)
        if split not in _SPLITS:
            raise SkillEvaluationError(f"{path}: case '{case_id}' has an unsupported split.")
        should_trigger = raw_case.get("should_trigger")
        if not isinstance(should_trigger, bool):
            message = f"{path}: case '{case_id}' must declare a boolean should_trigger."
            raise SkillEvaluationError(message)
        cases.append(
            WorkflowCase(
                case_id=case_id,
                split=split,
                request=_required_string(raw_case, "request", path),
                skill_name=_required_string(raw_case, "skill", path),
                should_trigger=should_trigger,
                required_artifacts=_string_list(raw_case, "required_artifacts", path),
                requested_tools=_string_list(raw_case, "requested_tools", path),
                forbidden_instructions=_string_list(raw_case, "forbidden_instructions", path),
            )
        )
    return tuple(sorted(cases, key=lambda case: (case.split, case.case_id)))


def _trigger_score(card: SkillCard, request: str) -> int:
    request_terms = _terms(request)
    for exclusion in card.exclusions:
        if len(_terms(exclusion).intersection(request_terms)) >= 2:
            return 0
    return max(
        (len(_terms(trigger).intersection(request_terms)) for trigger in card.triggers),
        default=0,
    )


def select_skill(cards: Iterable[SkillCard], request: str) -> str | None:
    """Route only when a declared trigger has two or more specific matching terms."""

    candidates = [
        (score, card.name)
        for card in cards
        if (score := _trigger_score(card, request)) >= 2
    ]
    if not candidates:
        return None
    highest_score = max(score for score, _ in candidates)
    names = sorted(name for score, name in candidates if score == highest_score)
    return names[0] if len(names) == 1 else None


def check_contract(card: SkillCard, case: WorkflowCase) -> tuple[ContractViolation, ...]:
    """Check the declared card contract against one fixture's expected procedure."""

    violations: list[ContractViolation] = []
    evidence = {item.casefold() for item in card.expected_evidence}
    tools = {item.casefold() for item in card.approved_tools}
    instructions = card.instruction_text.casefold()
    for artifact in case.required_artifacts:
        if artifact.casefold() not in evidence:
            violations.append(
                ContractViolation(
                    case_id=case.case_id,
                    skill_name=card.name,
                    code="REQUIRED_ARTIFACT_MISSING",
                    message=f"Expected evidence is missing required artifact: {artifact}",
                )
            )
    for tool in case.requested_tools:
        if tool.casefold() not in tools:
            violations.append(
                ContractViolation(
                    case_id=case.case_id,
                    skill_name=card.name,
                    code="UNAPPROVED_TOOL",
                    message=f"Case requires a tool outside the approved list: {tool}",
                )
            )
    for forbidden in case.forbidden_instructions:
        if forbidden.casefold() in instructions:
            violations.append(
                ContractViolation(
                    case_id=case.case_id,
                    skill_name=card.name,
                    code="FORBIDDEN_INSTRUCTION_PRESENT",
                    message=f"Instruction text contains forbidden guidance: {forbidden}",
                )
            )
    return tuple(violations)


def _metrics_for_split(
    split: str, outcomes: Iterable[SelectionOutcome]
) -> SelectionMetrics:
    true_positives = false_positives = false_negatives = true_negatives = 0
    for outcome in outcomes:
        selected = outcome.selected_skill is not None
        if outcome.should_trigger and selected and outcome.is_correct:
            true_positives += 1
        elif outcome.should_trigger:
            false_negatives += 1
        elif selected:
            false_positives += 1
        else:
            true_negatives += 1
    return SelectionMetrics(
        split=split,  # type: ignore[arg-type]
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
    )


def evaluate_selection(
    cards: Iterable[SkillCard], cases: Iterable[WorkflowCase]
) -> SelectionEvaluation:
    """Evaluate deterministic trigger selection and declared procedure contracts."""

    cards_by_name = {card.name: card for card in cards}
    outcomes: list[SelectionOutcome] = []
    violations: list[ContractViolation] = []
    for case in cases:
        selected_skill = select_skill(cards_by_name.values(), case.request)
        outcomes.append(
            SelectionOutcome(
                case_id=case.case_id,
                split=case.split,
                skill_name=case.skill_name,
                should_trigger=case.should_trigger,
                selected_skill=selected_skill,
            )
        )
        card = cards_by_name.get(case.skill_name)
        if card is None:
            violations.append(
                ContractViolation(
                    case_id=case.case_id,
                    skill_name=case.skill_name,
                    code="SKILL_NOT_FOUND",
                    message=(
                        "The fixture references a skill that was not parsed from the "
                        "inspected root."
                    ),
                )
            )
        else:
            violations.extend(check_contract(card, case))

    sorted_outcomes = tuple(sorted(outcomes, key=lambda outcome: (outcome.split, outcome.case_id)))
    metrics = tuple(
        _metrics_for_split(
            split,
            (outcome for outcome in sorted_outcomes if outcome.split == split),
        )
        for split in _SPLITS
    )
    return SelectionEvaluation(
        outcomes=sorted_outcomes,
        metrics=metrics,
        contract_violations=tuple(
            sorted(violations, key=lambda item: (item.case_id, item.code, item.skill_name))
        ),
    )
