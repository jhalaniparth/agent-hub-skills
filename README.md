# agent-hub-skills

Claude Code skills for SAP agent development, published by the SiX team.

## Skills included

| Skill | Description |
|---|---|
| `joule-deploy-agent-btp-cf` | Deploy a Python A2A or MCP agent to SAP BTP Cloud Foundry, wiring up Destination Service credentials for AI Core and S/4HANA |
| `joule-capability-generator` | Generate all YAML files and a `.daar` package to expose an agent in SAP Joule |
| `joule-six-demo-agent-designer` | Guide through intent capture, agent decomposition, and synthesis of production-ready enriched prompts for Joule Studio |
| `agent-hub-register` | Generate a valid `agents.json` registration entry to list an agent in the SiX Agent Hub catalog |

## Installation

### Method 1 — Claude Code plugin marketplace (auto-updatable)

The repository is public on github.com, so no SSH key, Personal Access Token, or login is required — Claude Code clones it anonymously over HTTPS.

1. Add the marketplace (one-time per machine):

```bash
claude plugin marketplace add jhalaniparth/agent-hub-skills
```

2. Install the plugin (all four skills at once):

```bash
claude plugin install agent-hub-skills@sap-six-agent-hub
```

The `@sap-six-agent-hub` suffix is the marketplace name — the install command needs the `plugin@marketplace` form.

To update to the latest version later, refresh the marketplace and reload:

```bash
claude plugin marketplace update sap-six-agent-hub
```

Then run `/reload-plugins` inside a Claude Code session (or start a new session) to activate the updated skills.

### Method 2 — Direct download (no marketplace setup required)

Use this for restricted environments or if you'd rather not use the plugin CLI.

1. Download the [latest zip](https://github.com/jhalaniparth/agent-hub-skills/archive/refs/heads/main.zip) in your browser.
2. Unzip and copy the four skill folders into `~/.claude/skills/`:

```bash
unzip agent-hub-skills-main.zip
mkdir -p ~/.claude/skills
cp -r agent-hub-skills-main/skills/joule-deploy-agent-btp-cf \
      agent-hub-skills-main/skills/joule-capability-generator \
      agent-hub-skills-main/skills/joule-six-demo-agent-designer \
      agent-hub-skills-main/skills/agent-hub-register \
      ~/.claude/skills/
```

> Copy the four skill folders explicitly rather than `skills/*` — the repo also contains a `*-workspace` development folder that isn't a shippable skill.

Skills are available immediately in your next Claude Code session.
