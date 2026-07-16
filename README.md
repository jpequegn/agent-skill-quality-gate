# Agent Skill Quality Gate

Agent Skill Quality Gate is a local-first quality gate for reusable AI procedures stored as
`SKILL.md` files. It makes a skill's routing rules, context cost, verification steps, and safety
boundaries inspectable before the procedure is reused.

The project is deliberately deterministic: it uses static analysis and synthetic fixtures, not an
LLM judge or an external API. Suggestions are review-only. The tool never edits inspected skills.

## Quick Start

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked --no-editable --dev
uv run --no-sync agent-skill-quality --help
```

On macOS, the non-editable install avoids hidden editable-install path files in the dot-prefixed
virtual environment. After changing package source files, refresh the installed package:

```sh
uv sync --locked --no-editable --dev --reinstall-package agent-skill-quality-gate
```

## Fixture Walkthrough

The repository includes only synthetic fixtures, so a new user can run the complete workflow
without supplying workplace data.

```sh
# Inspect static quality and print a redacted Markdown report.
uv run --no-sync agent-skill-quality lint tests/fixtures/corpus
uv run --no-sync agent-skill-quality report tests/fixtures/corpus

# Produce review-only delete, consolidate, or move-to-reference suggestions.
uv run --no-sync agent-skill-quality suggest-prune tests/fixtures/corpus

# Measure trigger precision, recall, false-positive rate, and contracts by split.
uv run --no-sync agent-skill-quality skill-eval \
  tests/fixtures/evaluation/skills tests/fixtures/evaluation/cases.yaml

# Compare local baseline, bloated, and distilled variants. Strict mode fails unless promotion clears.
uv run --no-sync agent-skill-quality skill-eval \
  --variants tests/fixtures/ablation/variants.yaml \
  --case-fixture tests/fixtures/ablation/cases.yaml --strict

# Emit only the machine-readable promotion recommendation for CI or another local tool.
uv run --no-sync agent-skill-quality skill-eval \
  --variants tests/fixtures/ablation/variants.yaml \
  --case-fixture tests/fixtures/ablation/cases.yaml --json
```

`lint`, `report`, and `suggest-prune` are advisory and return zero after successfully inspecting a
tree, even when they find issues. `skill-eval --strict` returns non-zero when trigger routing,
declared contracts, or promotion criteria fail.

## Skill Card

Each inspected skill starts with YAML front matter that declares when it should be selected and
what evidence it must produce.

```markdown
---
name: incident-triage
description: Route a production incident through an evidence-backed response.
skill_card:
  trigger:
    - A production incident needs an initial response plan.
  exclusions:
    - Do not use for product feature planning.
  required_inputs:
    - Incident summary
  approved_tools:
    - incident-api
  expected_evidence:
    - Incident timeline
  references: []
---

Confirm the incident summary and verify the cited timeline before recording a handoff.
```

The parser reads `SKILL.md` files and declared local Markdown references below the supplied root.
It rejects references that escape that root and ignores external URLs. See
[architecture.md](docs/architecture.md) for the model, scoring, and evaluation rules.

## Privacy Boundary

Use synthetic data or explicitly approved local procedure text. The project does not send data to
an API, call an LLM, retain traces, or collect raw agent logs, credentials, secrets, or workplace
transcripts. Report evidence redacts common secret-like values. The supplied corpus is synthetic.

Prune output is a dry-run review packet only: it does not write, rename, or delete inspected
`SKILL.md` files. Apply any proposed edit through normal human review.

## Development

Run the same checks used in CI:

```sh
uv run --no-sync ruff check --no-cache .
uv run --no-sync pytest
```
