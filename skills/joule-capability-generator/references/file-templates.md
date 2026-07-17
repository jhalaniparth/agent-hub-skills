# Joule Capability File Templates

Variables in `{{double braces}}` are substituted from user inputs.

---

## da.sapdas.yaml

```yaml
schema_version: 1.4.0
name: {{capability_name}}
capabilities:
  - type: local
    folder: ./a2a
```

---

## a2a/capability.sapdas.yaml

```yaml
schema_version: 3.27.0

metadata:
  display_name: {{agent_display_name}}
  namespace: {{namespace}}
  name: {{capability_name}}
  version: {{version}}
  description: >-
    {{capability_description}}

system_aliases:
  {{destination_name}}:
    destination: {{destination_name}}
```

**Note:** `{{destination_name}}` must be the exact string of the BTP destination
that points to the agent's A2A endpoint. It is used as both the alias key and
the destination reference. Each agent gets a unique destination name.

---

## a2a/capability_context.yaml

```yaml
variables:
  - name: agent_context_id
```

This single context variable threads the A2A `contextId` through all scenarios,
enabling multi-turn conversations with the remote agent.

---

## a2a/scenarios/{{scenario_slug}}.yaml

One file per scenario. `{{scenario_slug}}` is the title lowercased with spaces
replaced by underscores (e.g., `create_purchase_requisition`).

The `target.name` must match the function file for this scenario's output type
(see `output-type-templates.md`). The `response_context` block is **only
included for `genai` output type** — omit it for all other types.

**genai (default for A2A agents):**
```yaml
title: {{scenario_title}}
description: >-
  {{scenario_description}}

target:
  type: function
  name: tools/agent_call
  parameters:
    - name: agent_context_id
      value: $capability_context.agent_context_id

capability_context:
  - name: agent_context_id
    value: $target_result.agent_context_id

response_context:
  - description: Response from {{agent_display_name}}
    value: $target_result.agent_result
```

**text / card / list / quick_replies** (no `response_context` — output is
rendered directly by the function's `message` action):
```yaml
title: {{scenario_title}}
description: >-
  {{scenario_description}}

target:
  type: function
  name: tools/agent_call_{{output_type}}
  parameters:
    - name: agent_context_id
      value: $capability_context.agent_context_id

capability_context:
  - name: agent_context_id
    value: $target_result.agent_context_id
```

### Adding conversation starters (schema ≥ 3.4.0)

If the user wants a welcome-screen shortcut for the scenario, append:

```yaml
conversation_starter:
  title: {{starter_title}}        # ≤32 chars, shown on welcome screen
  trigger_utterance: {{utterance}} # natural-language phrase that fires this scenario
```

### Adding role-based visibility (ibn_targets example)

```yaml
visibility_condition:
  objects:
    - type: ibn_targets
      intents:
        - semantic_object: {{SemanticObject}}
          action: {{action}}
```

---

## a2a/functions/tools/agent_call.yaml

For all function file templates (genai, text, card, list, quick_replies, and composite layouts), see `references/output-type-templates.md`. That file is the single authoritative source for function YAML — use it for every output type including the default genai template.
