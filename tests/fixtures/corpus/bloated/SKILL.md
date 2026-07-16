---
name: bloated-review
description: Demonstrates duplicated and conditional instructions in a synthetic procedure.
skill_card:
  trigger:
    - A bounded source change requires a review packet.
  exclusions:
    - Do not use outside a source-code review.
  required_inputs:
    - Source diff
  approved_tools:
    - git-diff
  expected_evidence:
    - Test result
  references: []
---

# Bloated Review

Verify the changed files before continuing.
Verify the changed files before continuing.
TODO: add a concrete validation step.
If the change is high risk, add more review detail here.
