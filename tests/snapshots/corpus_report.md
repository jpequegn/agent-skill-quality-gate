# Agent Skill Quality Report

## Summary

- Skills inspected: 4
- Average score: 94
- Completeness diagnostics: 6

## Category Dashboard

| Category | Average score |
| --- | ---: |
| context hygiene | 100 |
| governance | 97 |
| instruction quality | 91 |
| safety | 90 |
| trigger clarity | 93 |
| verification | 97 |

## Skill Scores

| Skill | Score | Errors | Warnings |
| --- | ---: | ---: | ---: |
| bloated-review | 94 | 0 | 3 |
| change-review | 100 | 0 | 0 |
| incomplete-procedure | 91 | 1 | 2 |
| unsafe-retention | 93 | 1 | 1 |

## Completeness Diagnostics

- missing-trigger at incomplete/SKILL.md: Skill card does not declare trigger.
- missing-exclusions at incomplete/SKILL.md: Skill card does not declare exclusions.
- missing-required-inputs at incomplete/SKILL.md: Skill card does not declare required inputs.
- missing-approved-tools at incomplete/SKILL.md: Skill card does not declare approved tools.
- missing-expected-evidence at incomplete/SKILL.md: Skill card does not declare expected evidence.
- missing-references at incomplete/SKILL.md: Skill card does not declare references.

## Findings

### bloated-review

| Severity | Rule | Location | Evidence | Review-safe remediation |
| --- | --- | --- | --- | --- |
| warning | BRANCH_DETAIL_INLINE | bloated/SKILL.md:6 | A conditional instruction is present but no local reference was declared. | Move branch-specific detail into a local Markdown reference. |
| warning | INSTRUCTION_DUPLICATED | bloated/SKILL.md:4 | lines 3 and 4: Verify the changed files before continuing. | Keep one canonical instruction and link to detail only when needed. |
| warning | INSTRUCTION_STALE_OR_NOOP | bloated/SKILL.md:5 | TODO: add a concrete validation step. | Replace it with a concrete action, decision rule, or verification step. |

### change-review

No static findings.

### incomplete-procedure

| Severity | Rule | Location | Evidence | Review-safe remediation |
| --- | --- | --- | --- | --- |
| warning | PITFALLS_MISSING | incomplete/SKILL.md | No exclusions or cautionary language found | Document the cases where the skill must not be used and its safety limits. |
| error | TRIGGER_MISSING | incomplete/SKILL.md:1 | skill_card.trigger is absent | Declare the concrete workflow condition that should select this skill. |
| warning | VERIFICATION_MISSING | incomplete/SKILL.md | No verify, validate, test, check, or assert instruction found | Add a concrete command, artifact, or assertion that proves completion. |

### unsafe-retention

| Severity | Rule | Location | Evidence | Review-safe remediation |
| --- | --- | --- | --- | --- |
| error | RAW_LOG_GUIDANCE_UNSAFE | unsafe/SKILL.md:3 | Store raw agent logs and api_key=[REDACTED] for every request. Verify the record. | Retain only curated evidence fields and never collect secrets or raw logs. |
| warning | RULE_OVERBROAD | unsafe/SKILL.md:3 | Store raw agent logs and api_key=[REDACTED] for every request. Verify the record. | Limit the rule to named conditions and declare explicit exclusions. |
