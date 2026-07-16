# Agent Skill Quality Gate

Local-first quality checks for reusable AI procedures. The project inspects synthetic or explicitly
provided `SKILL.md` trees, produces review-only findings, and evaluates whether a skill helps the
right held-out tasks without widening its trigger or context cost.

The initial scaffold provides the CLI and quality gates. Subsequent modules add skill-card parsing,
static analysis, prune suggestions, and deterministic promotion decisions.

## Development

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --no-editable --dev
uv run --no-sync agent-skill-quality --help
uv run --no-sync ruff check .
uv run --no-sync pytest
```

The non-editable sync avoids macOS treating editable-install path files inside a dot-prefixed virtual
environment as hidden. After changing package source files, run:

```sh
uv sync --locked --no-editable --dev --reinstall-package agent-skill-quality-gate
```

## Privacy Boundary

The project is designed for synthetic fixtures and local inspection. It does not collect or retain
raw agent logs, credentials, secrets, private workplace data, or transcript corpora.
