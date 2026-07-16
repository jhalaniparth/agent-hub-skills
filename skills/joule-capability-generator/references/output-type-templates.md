# Output Type Function Templates

Each template replaces the standard `agent_call.yaml` when a specific output
type is requested. Variables in `{{double braces}}` are substituted from user
inputs. Only generate the files that are actually needed.

---

## genai — `tools/agent_call.yaml` (default for A2A agents)

Use when no output type is specified, or when the agent returns free-form text
that Joule's AI should reformat. The `agent_result` is passed to Joule's GenAI
layer via `response_context` in the scenario file.

```yaml
parameters:
  - name: agent_context_id
    optional: true

action_groups:
  - actions:
    - type: agent-request
      agent_type: remote
      system_alias: {{destination_name}}
      body:
        contextId: <? agent_context_id ?>
      result_variable: agentResponse

  - condition: "agentResponse.body.status.state == 'input-required'"
    actions:
      - type: set-variables
        variables:
          - name: replyText
            value: "<? agentResponse.body.status.message.parts[0].text ?>"

  - condition: "agentResponse.body.status.state == 'completed'"
    actions:
      - type: set-variables
        variables:
          - name: replyText
            value: "<? agentResponse.body.artifacts[0].parts[0].text ?>"

result:
  agent_context_id: "<? agentResponse.body.contextId ?>"
  responseToUser: "<? replyText ?>"
  agent_result: "<? agentResponse ?>"
```

---

## text — `tools/agent_call_text.yaml`

Use when the agent returns a plain string to display verbatim — no AI rewrite.
The `message` action emits the text directly to the user. Omit `response_context`
from the scenario file.

```yaml
parameters:
  - name: agent_context_id
    optional: true

action_groups:
  - actions:
    - type: agent-request
      agent_type: remote
      system_alias: {{destination_name}}
      body:
        contextId: <? agent_context_id ?>
      result_variable: agentResponse

  - condition: "agentResponse.body.status.state == 'input-required'"
    actions:
      - type: message
        message:
          type: text
          content: "<? agentResponse.body.status.message.parts[0].text ?>"

  - condition: "agentResponse.body.status.state == 'completed'"
    actions:
      - type: message
        message:
          type: text
          content: "<? agentResponse.body.artifacts[0].parts[0].text ?>"

result:
  agent_context_id: "<? agentResponse.body.contextId ?>"
```

---

## card — `tools/agent_call_card.yaml`

Use when the agent returns structured data to display as a titled card. The
agent must return JSON in its artifact text with these fields (all optional
except `title`): `title`, `subtitle`, `description`, `status`, `imageUri`.

```yaml
parameters:
  - name: agent_context_id
    optional: true

action_groups:
  - actions:
    - type: agent-request
      agent_type: remote
      system_alias: {{destination_name}}
      body:
        contextId: <? agent_context_id ?>
      result_variable: agentResponse

  - condition: "agentResponse.body.status.state == 'input-required'"
    actions:
      - type: message
        message:
          type: text
          content: "<? agentResponse.body.status.message.parts[0].text ?>"

  - condition: "agentResponse.body.status.state == 'completed'"
    actions:
      - type: set-variables
        variables:
          - name: cardData
            value: "<? agentResponse.body.artifacts[0].parts[0].text.toJson() ?>"
      - type: message
        message:
          type: card
          title: "<? cardData.title ?>"
          subtitle: "<? cardData.subtitle ?>"
          description: "<? cardData.description ?>"
          status: "<? cardData.status ?>"

result:
  agent_context_id: "<? agentResponse.body.contextId ?>"
```

**Agent contract:** the agent must return a JSON string as its artifact text,
e.g.:
```json
{"title": "PR-10042", "subtitle": "Pending Approval", "description": "Office supplies — 5 units", "status": "Open"}
```

---

## list — `tools/agent_call_list.yaml`

Use when the agent returns a collection of items (search results, PR list,
approval queue, etc.). The agent must return JSON with an `items` array; each
item may have `title`, `subtitle`, `description`, `status`.

```yaml
parameters:
  - name: agent_context_id
    optional: true

action_groups:
  - actions:
    - type: agent-request
      agent_type: remote
      system_alias: {{destination_name}}
      body:
        contextId: <? agent_context_id ?>
      result_variable: agentResponse

  - condition: "agentResponse.body.status.state == 'input-required'"
    actions:
      - type: message
        message:
          type: text
          content: "<? agentResponse.body.status.message.parts[0].text ?>"

  - condition: "agentResponse.body.status.state == 'completed'"
    actions:
      - type: set-variables
        variables:
          - name: listData
            value: "<? agentResponse.body.artifacts[0].parts[0].text.toJson() ?>"
      - type: message
        message:
          type: list
          items: "<? listData.items ?>"

result:
  agent_context_id: "<? agentResponse.body.contextId ?>"
```

**Agent contract:** the agent must return a JSON string, e.g.:
```json
{
  "items": [
    {"title": "PR-10042", "subtitle": "Office supplies", "status": "Pending"},
    {"title": "PR-10043", "subtitle": "IT equipment", "status": "Approved"}
  ]
}
```

---

## quick_replies — `tools/agent_call_quick_replies.yaml`

Use when the agent asks a follow-up question and provides a fixed set of options
for the user to tap (e.g., "Which delivery date works? [Today] [Next Week]
[Custom]"). The agent must return a JSON object with `question` (string) and
`options` (array of strings) in its `input-required` status message.

```yaml
parameters:
  - name: agent_context_id
    optional: true

action_groups:
  - actions:
    - type: agent-request
      agent_type: remote
      system_alias: {{destination_name}}
      body:
        contextId: <? agent_context_id ?>
      result_variable: agentResponse

  - condition: "agentResponse.body.status.state == 'input-required'"
    actions:
      - type: set-variables
        variables:
          - name: promptData
            value: "<? agentResponse.body.status.message.parts[0].text.toJson() ?>"
      - type: message
        message:
          type: text
          content: "<? promptData.question ?>"
      - type: message
        message:
          type: quick_replies
          replies: "<? promptData.options ?>"

  - condition: "agentResponse.body.status.state == 'completed'"
    actions:
      - type: message
        message:
          type: text
          content: "<? agentResponse.body.artifacts[0].parts[0].text ?>"

result:
  agent_context_id: "<? agentResponse.body.contextId ?>"
```

**Agent contract:** when asking a follow-up question, the agent must return a
JSON string as its status message text, e.g.:
```json
{"question": "Which delivery date works best?", "options": ["Today", "Next Week", "Custom"]}
```

---

## Mixing output types across scenarios

When a capability has scenarios with different output types, generate one
function file per type. Each scenario's `target.name` points to the right file:

| Scenario output type | `target.name` in scenario YAML |
|---------------------|-------------------------------|
| `genai` | `tools/agent_call` |
| `text` | `tools/agent_call_text` |
| `card` | `tools/agent_call_card` |
| `list` | `tools/agent_call_list` |
| `quick_replies` | `tools/agent_call_quick_replies` |

All function files share the same `{{destination_name}}` system alias.

---

## Composite layouts

Use a composite layout when a single agent response needs to emit **multiple UI
elements in sequence** — e.g., a list of items followed by quick reply buttons,
or a card followed by a follow-up question with chips.

Multiple `message` actions in the same action group fire in order. Joule renders
them top-to-bottom in the conversation.

### Pattern: list card + quick replies (agent returns stringified JSON)

**Use case:** agent returns one JSON string as artifact text containing both an
`items` array (for the list) and a `quick_replies` array (for suggestion chips).

**Agent contract — artifact text must be a JSON string like:**
```json
{
  "items": [
    {"title": "PR-1042", "subtitle": "Office supplies", "status": "Pending"},
    {"title": "PR-1043", "subtitle": "IT equipment",    "status": "Approved"}
  ],
  "quick_replies": ["Approve all", "Reject all", "Show details"]
}
```

**Function YAML:**
```yaml
parameters:
  - name: agent_context_id
    optional: true

action_groups:
  - actions:
    - type: agent-request
      agent_type: remote
      system_alias: {{destination_name}}
      body:
        contextId: <? agent_context_id ?>
      result_variable: agentResponse

  # input-required: agent is asking a follow-up — show text + chips if present
  - condition: "agentResponse.body.status.state == 'input-required'"
    actions:
      - type: set-variables
        variables:
          - name: promptRaw
            value: "<? agentResponse.body.status.message.parts[0].text ?>"
      # Try to parse as JSON; fall back to plain text
      - type: set-variables
        variables:
          - name: promptData
            value: "<? promptRaw.startsWith('{') ? promptRaw.toJson() : null ?>"
      - type: message
        message:
          type: text
          content: "<? promptData != null ? promptData.question : promptRaw ?>"
      - condition: "promptData != null && promptData.quick_replies != null"
        type: message
        message:
          type: quick_replies
          replies: "<? promptData.quick_replies ?>"

  # completed: parse the JSON artifact, render list then quick replies
  - condition: "agentResponse.body.status.state == 'completed'"
    actions:
      - type: set-variables
        variables:
          - name: responseData
            value: "<? agentResponse.body.artifacts[0].parts[0].text.toJson() ?>"
      - type: message
        message:
          type: list
          items: "<? responseData.items ?>"
      - condition: "responseData.quick_replies != null && responseData.quick_replies.size() > 0"
        type: message
        message:
          type: quick_replies
          replies: "<? responseData.quick_replies ?>"

result:
  agent_context_id: "<? agentResponse.body.contextId ?>"
```

**Key SpEL notes:**
- `.toJson()` — deserialises a JSON string into a SpEL-navigable object. Required because A2A artifact text is always a raw string, not a pre-parsed object.
- `.startsWith('{')` — cheap guard before calling `.toJson()` so plain-text responses don't throw a parse error.
- `responseData.quick_replies.size() > 0` — guards against an empty array rendering a blank chip bar.
- The second `message` action (quick_replies) is inside a `condition` block so it only fires when the array is present and non-empty. Joule skips action groups whose condition is false.
- Items in the `list` message must have at least `title`; `subtitle`, `description`, and `status` are optional.

### Pattern: card + quick replies

Same structure as above but swap the `list` message for a `card`:

```yaml
      - type: message
        message:
          type: card
          title: "<? responseData.title ?>"
          subtitle: "<? responseData.subtitle ?>"
          description: "<? responseData.description ?>"
          status: "<? responseData.status ?>"
      - condition: "responseData.quick_replies != null && responseData.quick_replies.size() > 0"
        type: message
        message:
          type: quick_replies
          replies: "<? responseData.quick_replies ?>"
```

**Agent contract for card + quick replies:**
```json
{
  "title": "PR-1042",
  "subtitle": "Office supplies — 5 units",
  "description": "Requested by: John Smith | Delivery: 2026-07-01",
  "status": "Pending Approval",
  "quick_replies": ["Approve", "Reject", "Request changes"]
}
```

### Pattern: text + quick replies

When the agent returns a plain question string alongside quick reply options:

```yaml
      - type: set-variables
        variables:
          - name: responseData
            value: "<? agentResponse.body.artifacts[0].parts[0].text.toJson() ?>"
      - type: message
        message:
          type: text
          content: "<? responseData.message ?>"
      - condition: "responseData.quick_replies != null && responseData.quick_replies.size() > 0"
        type: message
        message:
          type: quick_replies
          replies: "<? responseData.quick_replies ?>"
```

**Agent contract:**
```json
{
  "message": "Which items would you like to include in the requisition?",
  "quick_replies": ["All items", "Only urgent", "Let me choose"]
}
```

### Accessing nested quick_replies (object array, not string array)

If your agent returns quick replies as **objects** with a label field rather than
plain strings — e.g.:
```json
{
  "quick_replies": [
    {"label": "Approve", "value": "approve"},
    {"label": "Reject",  "value": "reject"}
  ]
}
```

Use SpEL **collection projection** to extract just the labels for the chip bar:
```yaml
          replies: "<? responseData.quick_replies.![label] ?>"
```

`.![fieldName]` projects each object in the list to the value of that field,
producing a plain string array that the `quick_replies` message type expects.
Substitute `label` with whatever field name your agent uses.
