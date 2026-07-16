---
name: change-review
description: Produce a focused review packet for a bounded source change.
skill_card:
  trigger:
    - A reviewer needs evidence for a proposed source-code change.
  exclusions:
    - Do not use for broad product planning or open-ended research.
  required_inputs:
    - Source diff
  approved_tools:
    - git-diff
  expected_evidence:
    - Test command output summary
  references: []
  version: "1.0.0"
---

# Change Review

Inspect the supplied diff, verify the stated test command, and record a concise decision packet.
