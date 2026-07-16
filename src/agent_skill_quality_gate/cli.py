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
        help="Evaluate local trigger fixtures or compare a local variant ablation.",
    )
    evaluation_parser.add_argument(
        "root",
        type=Path,
        nargs="?",
        help="Directory containing one or more SKILL.md files.",
    )
    evaluation_parser.add_argument(
        "cases",
        type=Path,
        nargs="?",
        help="YAML file containing synthetic workflow cases.",
    )
    evaluation_parser.add_argument(
        "--variants",
        type=Path,
        help="YAML manifest for baseline, bloated, and distilled local skill variants.",
    )
    evaluation_parser.add_argument(
        "--case-fixture",
        type=Path,
        help="YAML fixture used with --variants.",
    )
    evaluation_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status when evaluation or promotion criteria fail.",
    )
    evaluation_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the ablation recommendation as stable JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command is None:
        return 0

    from .ablation import (
        evaluate_ablation,
        load_variant_specs,
        promotion_passes,
        render_machine_recommendation,
    )
    from .analyzer import analyze_tree
    from .evaluation import evaluate_selection, load_workflow_cases
    from .models import SkillEvaluationError, SkillParseError
    from .parser import parse_skill_tree
    from .pruning import propose_pruning
    from .reporting import (
        render_ablation_evaluation,
        render_lint_summary,
        render_markdown_report,
        render_prune_review_packet,
        render_selection_evaluation,
    )

    try:
        if arguments.command == "skill-eval":
            if arguments.variants is not None:
                if (
                    arguments.root is not None
                    or arguments.cases is not None
                    or arguments.case_fixture is None
                ):
                    raise SkillEvaluationError(
                        "skill-eval --variants requires --case-fixture and no positional arguments."
                    )
                ablation = evaluate_ablation(
                    load_variant_specs(arguments.variants),
                    arguments.case_fixture,
                )
                if arguments.json:
                    print(render_machine_recommendation(ablation.decision), end="")
                else:
                    print(render_ablation_evaluation(ablation), end="")
                return 0 if not arguments.strict or promotion_passes(ablation.decision) else 1
            if arguments.root is None or arguments.cases is None:
                raise SkillEvaluationError(
                    "skill-eval requires ROOT and CASES when --variants is not supplied."
                )
            parsed = parse_skill_tree(arguments.root)
            cases = load_workflow_cases(arguments.cases)
            evaluation = evaluate_selection(parsed.cards, cases)
            print(render_selection_evaluation(evaluation), end="")
            passed = all(outcome.is_correct for outcome in evaluation.outcomes)
            passed = passed and not evaluation.contract_violations
            return 0 if not arguments.strict or passed else 1
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
