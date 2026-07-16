"""Constrained parsing for SKILL.md trees and local Markdown references."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .models import ParseDiagnostic, ParseResult, ReferenceDocument, SkillCard, SkillParseError

_FRONT_MATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<metadata>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((?P<target>[^)\s]+)(?:\s+[^)]*)?\)")
_SKILL_CARD_FIELDS = {
    "trigger",
    "exclusions",
    "required_inputs",
    "approved_tools",
    "expected_evidence",
    "references",
    "version",
    "review_by",
}
_OPTIONAL_LIST_FIELDS = {
    "trigger": "triggers",
    "exclusions": "exclusions",
    "required_inputs": "required inputs",
    "approved_tools": "approved tools",
    "expected_evidence": "expected evidence",
}


def _relative_path(root: Path, path: Path) -> Path:
    return path.resolve().relative_to(root)


def _require_string(metadata: Mapping[str, object], field: str, path: Path) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SkillParseError(f"{path}: front matter field '{field}' must be a non-empty string.")
    return value.strip()


def _string_list(
    metadata: Mapping[str, object],
    field: str,
    path: Path,
    diagnostics: list[ParseDiagnostic],
) -> tuple[str, ...]:
    value = metadata.get(field)
    if value is None:
        diagnostics.append(
            ParseDiagnostic(
                code=f"missing-{field.replace('_', '-')}",
                message=f"Skill card does not declare {field.replace('_', ' ')}.",
                source_path=path,
            )
        )
        return ()
    valid_items = isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )
    if not valid_items:
        raise SkillParseError(f"{path}: skill_card.{field} must be a list of non-empty strings.")
    return tuple(item.strip() for item in value)


def _optional_string(metadata: Mapping[str, object], field: str, path: Path) -> str | None:
    value = metadata.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SkillParseError(f"{path}: skill_card.{field} must be a non-empty string.")
    return value.strip()


def _optional_date(metadata: Mapping[str, object], path: Path) -> date | None:
    value = metadata.get("review_by")
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            message = f"{path}: skill_card.review_by must use ISO date format."
            raise SkillParseError(message) from error
    raise SkillParseError(f"{path}: skill_card.review_by must use ISO date format.")


def _read_front_matter(path: Path) -> tuple[Mapping[str, object], str]:
    try:
        document = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise SkillParseError(f"{path}: SKILL.md must be UTF-8 text.") from error

    match = _FRONT_MATTER_PATTERN.match(document)
    if match is None:
        raise SkillParseError(f"{path}: SKILL.md must begin with YAML front matter.")

    try:
        metadata = yaml.safe_load(match.group("metadata"))
    except yaml.YAMLError as error:
        raise SkillParseError(f"{path}: malformed YAML front matter.") from error
    if not isinstance(metadata, dict):
        raise SkillParseError(f"{path}: front matter must be a mapping.")

    return metadata, document[match.end() :].strip()


def _markdown_reference_targets(instruction_text: str) -> Iterable[str]:
    for match in _MARKDOWN_LINK_PATTERN.finditer(instruction_text):
        target = match.group("target").split("#", maxsplit=1)[0]
        if target:
            yield target


def _local_markdown_reference(
    root: Path,
    source_path: Path,
    target: str,
    diagnostics: list[ParseDiagnostic],
) -> ReferenceDocument | None:
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None

    candidate = (source_path.parent / target).resolve()
    try:
        relative = _relative_path(root, candidate)
    except ValueError:
        raise SkillParseError(f"{source_path}: reference escapes the inspected root: {target}")

    if candidate.suffix.lower() != ".md":
        diagnostics.append(
            ParseDiagnostic(
                code="unsupported-reference",
                message=f"Ignored non-Markdown reference: {target}",
                source_path=_relative_path(root, source_path),
            )
        )
        return None
    if not candidate.is_file():
        diagnostics.append(
            ParseDiagnostic(
                code="missing-reference",
                message=f"Referenced Markdown file does not exist: {target}",
                source_path=_relative_path(root, source_path),
            )
        )
        return None

    character_count = len(candidate.read_text(encoding="utf-8"))
    return ReferenceDocument(path=relative, character_count=character_count)


def parse_skill_file(root: Path, path: Path) -> tuple[SkillCard, tuple[ParseDiagnostic, ...]]:
    """Parse a single SKILL.md under root without reading arbitrary linked files."""

    root = root.resolve()
    path = path.resolve()
    if path.name != "SKILL.md":
        raise SkillParseError(f"{path}: only files named SKILL.md may be parsed.")
    try:
        source_path = _relative_path(root, path)
    except ValueError as error:
        raise SkillParseError(f"{path}: SKILL.md must be under the inspected root.") from error

    metadata, instruction_text = _read_front_matter(path)
    name = _require_string(metadata, "name", source_path)
    description = _require_string(metadata, "description", source_path)
    raw_card = metadata.get("skill_card", {})
    if not isinstance(raw_card, dict):
        raise SkillParseError(f"{source_path}: skill_card must be a mapping when present.")

    unknown_fields = set(raw_card).difference(_SKILL_CARD_FIELDS)
    if unknown_fields:
        fields = ", ".join(sorted(unknown_fields))
        raise SkillParseError(f"{source_path}: unsupported skill_card field(s): {fields}")

    diagnostics: list[ParseDiagnostic] = []
    field_values = {
        field: _string_list(raw_card, field, source_path, diagnostics)
        for field in _OPTIONAL_LIST_FIELDS
    }
    reference_targets = list(_string_list(raw_card, "references", source_path, diagnostics))
    reference_targets.extend(_markdown_reference_targets(instruction_text))

    references: list[ReferenceDocument] = []
    seen_paths: set[Path] = set()
    for target in reference_targets:
        reference = _local_markdown_reference(root, path, target, diagnostics)
        if reference is not None and reference.path not in seen_paths:
            references.append(reference)
            seen_paths.add(reference.path)

    card = SkillCard(
        name=name,
        description=description,
        source_path=source_path,
        instruction_text=instruction_text,
        triggers=field_values["trigger"],
        exclusions=field_values["exclusions"],
        required_inputs=field_values["required_inputs"],
        approved_tools=field_values["approved_tools"],
        expected_evidence=field_values["expected_evidence"],
        references=tuple(references),
        version=_optional_string(raw_card, "version", source_path),
        review_by=_optional_date(raw_card, source_path),
    )
    return card, tuple(diagnostics)


def parse_skill_tree(root: Path) -> ParseResult:
    """Parse every nested SKILL.md and collect non-fatal completeness diagnostics."""

    root = root.resolve()
    if not root.is_dir():
        raise SkillParseError(f"{root}: inspected root must be a directory.")

    cards: list[SkillCard] = []
    diagnostics: list[ParseDiagnostic] = []
    for path in sorted(root.rglob("SKILL.md")):
        card, card_diagnostics = parse_skill_file(root, path)
        cards.append(card)
        diagnostics.extend(card_diagnostics)
    return ParseResult(cards=tuple(cards), diagnostics=tuple(diagnostics))
