# Agent Hub Schema — Quick Reference

## Required fields
id, name, shortDescription (≤160 chars), status, agentType, industry (array),
businessProcess, owner, landscapes (array, minItems: 1), samplePrompts (array, minItems: 1)

## Enum values

| Field | Allowed values |
|---|---|
| `status` | `"live"` \| `"development"` \| `"deprecated"` |
| `agentType` | `"joule"` \| `"custom-ui"` \| `"api-based"` \| `"workflow"` |
| `landscapes[].tier` | `"DEV"` \| `"QA"` \| `"PROD"` |
| `landscapes[].status` | `"live"` \| `"degraded"` \| `"down"` \| `"unknown"` |
| `samplePrompts[].category` | `"Basic"` \| `"Advanced"` \| `"Edge Case"` |
| `autonomousDomain` | `"Autonomous Finance"` \| `"Autonomous Supply Chain"` \| `"Autonomous Procurement"` \| `"Autonomous HR"` \| `"Autonomous Sales"` \| `"Autonomous Operations"` \| `"Other"` |
| `deploymentModel` | `"common-subaccount"` \| `"dedicated-subaccount"` |
| `source` | `"github"` \| `"manual"` \| `"csv"` |

## id format
Pattern: `^[a-z0-9-]+$` (lowercase kebab-case only)

## Full schema
See data/agents.schema.json in the Agent Hub repo for complete validation rules.
