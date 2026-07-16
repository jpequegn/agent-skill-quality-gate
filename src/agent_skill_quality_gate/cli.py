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
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument(
            "root",
            type=Path,
            help="Directory containing one or more SKILL.md files.",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command is None:
        return 0

    from .analyzer import analyze_tree
    from .models import SkillParseError
    from .reporting import render_lint_summary, render_markdown_report

    try:
        run = analyze_tree(arguments.root)
    except SkillParseError as error:
        print(f"error: {error}")
        return 2

    if arguments.command == "lint":
        print(render_lint_summary(run))
    if arguments.command == "report":
        print(render_markdown_report(run), end="")
    return 0
