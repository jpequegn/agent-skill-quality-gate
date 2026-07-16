# Architecture And Evaluation

## Pipeline

1. `parser.py` reads only `SKILL.md` files and permitted local Markdown references below the
   inspected root. It normalizes a `SkillCard` and records missing manifest fields as diagnostics.
2. `analyzer.py` applies stable lint rules for trigger clarity, context hygiene, instruction
   quality, verification, safety, and governance. Each category begins at 100; errors deduct 25
   points and warnings deduct 12 points.
3. `reporting.py` renders deterministic summaries and Markdown evidence. Secret-like values in
   finding evidence are redacted before rendering.
4. `pruning.py` maps existing static findings to review-only `delete`, `consolidate`, or
   `move-to-reference` proposals. It has no file-writing API.
5. `evaluation.py` routes synthetic requests by declared trigger terms and exclusions, then checks
   expected artifacts, requested tools, and forbidden instruction fragments. It reports
   development and held-out metrics separately.
6. `ablation.py` compares local baseline, bloated, and distilled variants and returns an
   explainable `promote`, `revise`, or `retire` recommendation.

## Routing And Metrics

Trigger evaluation is lexical and deterministic. A card is selected only when a declared trigger
shares at least two specific terms with the request and no declared exclusion matches. Ties remain
unselected rather than being resolved arbitrarily.

For each split, the evaluator reports precision, recall, false-positive rate, and the TP, FP, FN,
and TN counts. It retains no request log or execution trace. Fixtures name the expected skill,
whether it should trigger, required artifacts, requested tools, and instruction fragments that
must not appear.

The ablation runner reports:

- Success: correct selection with no contract violation, separated into development and held-out.
- Retries: fixture cases that did not succeed on their first deterministic pass.
- Context cost: total characters in a variant's main skill files and permitted references.
- Latency proxy: context cost plus 500 units for each retry. It is a comparison aid, not a timing
  measurement.
- Safety and evidence violations: blocking forbidden-instruction or raw-log guidance, and missing
  expected artifacts.

The distilled candidate is promoted only when it improves held-out success over baseline, does not
perform worse on held-out data than development data, and has no negative-trigger, safety, or
evidence violations. A candidate with no useful development or held-out signal is retired. Other
failures are revised. `skill-eval --strict` maps a non-promotion outcome to a non-zero exit status.

## Boundaries

This is a quality gate for reusable procedure text, not a runtime orchestrator or a live-model
benchmark. It does not execute a skill's tools, score model generations, or replace human review.
Use the structured report and review packet as evidence for a pull request or governance decision.
