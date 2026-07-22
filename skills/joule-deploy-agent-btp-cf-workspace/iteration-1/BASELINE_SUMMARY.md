# Baseline grading summary (iteration-1, old_skill only)

| Eval | Pass rate | Result |
|------|-----------|--------|
| sf-only-no-s4 | 2/5 (40%) | Discovers SF but still wires `S4HANA`; no SF destination |
| two-agents-unique-s4-names | 2/4 (50%) | Both agents get shared `S4HANA` (collision); `AICORE` shared OK |
| mcp-sf-migrate-not-s4-client | 1/4 (25%) | Forces `s4_client.py` + `S4HANA` onto SF MCP agent; MCP removal OK |

**Overall old_skill:** 5/13 assertions passed (~38%)

This is the expected RED baseline before implementing catalog-based discovery / unique destinations / multi-system MCP migration.

`with_skill` runs are deferred until the skill is updated per the design spec.
