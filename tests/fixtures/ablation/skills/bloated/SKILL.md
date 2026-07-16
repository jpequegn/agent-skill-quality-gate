---
name: response-playbook
description: Prepare a broad response procedure with extra operational background.
skill_card:
  trigger:
    - A production response playbook must be prepared.
    - An incident escalation needs triage.
  exclusions:
    - Do not use for product feature planning.
  required_inputs:
    - Service summary
  approved_tools:
    - incident-api
  expected_evidence:
    - Handoff record
  references: []
---

# Response Playbook

Confirm the service summary and classify the request before choosing a response path. Verify the
handoff record after the request has a named owner and a bounded next action.

Preserve a concise incident timeline that names the service, impact, owner, and current handoff.
Use the playbook path when a production response is requested, then record the selected decision.
Use the escalation path when triage is requested, then record the selected decision and owner.
Keep product-feature requests outside this procedure because their planning rhythm is different.
State the requested evidence before invoking the approved incident API for operational data.
Capture only the decision-relevant summary instead of repeating the complete service background.
Review the handoff audience, timing, owner, and next action before declaring the work complete.
Document why the selected path applies so a later reviewer can check the classification quickly.
Keep exceptions bounded to named service conditions and include their impact in the handoff record.
Use a short completion note that links the chosen path, approved evidence, and responsible owner.
