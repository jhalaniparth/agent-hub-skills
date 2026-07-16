# agent-hub-skills

Claude Code skills for SAP agent development, published by the SiX team.

## Skills included

| Skill | Description |
|---|---|
| `joule-deploy-agent-btp-cf` | Deploy a Python A2A or MCP agent to SAP BTP Cloud Foundry, wiring up Destination Service credentials for AI Core and S/4HANA |
| `joule-capability-generator` | Generate all YAML files and a `.daar` package to expose an agent in SAP Joule |
| `joule-six-demo-agent-designer` | Guide through intent capture, agent decomposition, and synthesis of production-ready enriched prompts for Joule Studio |

## Installation

### Method 1 — claude plugin install (auto-updates)

```bash
claude plugin install https://github.tools.sap/six-cit-ai/agent-hub-skills
```

> Note: requires a Personal Access Token for github.tools.sap configured in your Claude Code settings.

### Method 2 — Direct download (no PAT required)

1. Download the [latest release zip](https://github.tools.sap/six-cit-ai/agent-hub-skills/releases/latest) in your browser (SAP SSO works)
2. Run:

```bash
unzip agent-hub-skills.zip
cp -r agent-hub-skills/skills/* ~/.claude/skills/
```

Skills are available immediately in your next Claude Code session.
