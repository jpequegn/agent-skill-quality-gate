"""Command-line entry point for the skill quality gate."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-skill-quality",
        description="Local-first linting and deterministic evaluation for reusable AI skills.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")
    for command, help_text in (
        ("lint", "Print a compact deterministic analysis summary."),
        ("report", "Print a Markdown quality report."),
        ("suggest-prune", "Print read-only, finding-linked prune suggestions."),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument(
            "root",
            type=Path,
            help="Directory containing one or more SKILL.md files.",
        )
    evaluation_parser = subparsers.add_parser(
        "skill-eval",
        help="Evaluate declared trigger selection against local synthetic fixtures.",
    )
    evaluation_parser.add_argument(
        "root",
        type=Path,
        help="Directory containing one or more SKILL.md files.",
    )
    evaluation_parser.add_argument(
        "cases",
        type=Path,
        help="YAML file containing synthetic workflow cases.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command is None:
        return 0

    from .analyzer import analyze_tree
    from .evaluation import evaluate_selection, load_workflow_cases
    from .models import SkillEvaluationError, SkillParseError
    from .parser import parse_skill_tree
    from .pruning import propose_pruning
    from .reporting import (
        render_lint_summary,
        render_markdown_report,
        render_prune_review_packet,
        render_selection_evaluation,
    )

    try:
        if arguments.command == "skill-eval":
            parsed = parse_skill_tree(arguments.root)
            cases = load_workflow_cases(arguments.cases)
            print(render_selection_evaluation(evaluate_selection(parsed.cards, cases)), end="")
            return 0
        run = analyze_tree(arguments.root)
    except (SkillEvaluationError, SkillParseError) as error:
        print(f"error: {error}")
        return 2

    if arguments.command == "lint":
        print(render_lint_summary(run))
    if arguments.command == "report":
        print(render_markdown_report(run), end="")
    if arguments.command == "suggest-prune":
        print(render_prune_review_packet(propose_pruning(run)), end="")
    return 0
