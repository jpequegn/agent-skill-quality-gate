"""Typed, privacy-safe representations of inspected skill files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class ParseDiagnostic:
    code: str
    message: str
    source_path: Path


@dataclass(frozen=True)
class ReferenceDocument:
    """A permitted local Markdown reference, represented without its contents."""

    path: Path
    character_count: int


@dataclass(frozen=True)
class SkillCard:
    """Normalized metadata and instructions for a single reusable procedure."""

    name: str
    description: str
    source_path: Path
    instruction_text: str
    triggers: tuple[str, ...]
    exclusions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    approved_tools: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    references: tuple[ReferenceDocument, ...]
    version: str | None
    review_by: date | None

    @property
    def main_character_count(self) -> int:
        return len(self.instruction_text)

    @property
    def reference_character_count(self) -> int:
        return sum(reference.character_count for reference in self.references)

    @property
    def context_character_count(self) -> int:
        return self.main_character_count + self.reference_character_count


@dataclass(frozen=True)
class ParseResult:
    cards: tuple[SkillCard, ...]
    diagnostics: tuple[ParseDiagnostic, ...]


class SkillParseError(ValueError):
    """Raised when a SKILL.md cannot be safely interpreted as a skill card."""
