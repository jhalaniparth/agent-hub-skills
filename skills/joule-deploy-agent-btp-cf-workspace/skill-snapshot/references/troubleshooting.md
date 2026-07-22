## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SapException - No credentials found in any source` | AI Core env vars missing | Set 5 AICORE_ vars via `cf set-env` and restage (see below) |
| `S4_CONNECTION_ERROR: HTTP 401` | Wrong S/4HANA credentials | Check `S4_USERNAME` / `S4_PASSWORD` env vars |
| App crashes at start | Wrong command in Procfile | Check path and module:variable reference |
| Health check never passes | App not binding to `$PORT` | Ensure `--port $PORT` in start command |
| 503 from CF router | Import error / missing dep | `cf logs <app> --recent` |
| Destination loader warns at startup | No Destination service bound or instance wrong | Check `jouleagent-dest` exists and is bound |
| `litellm.APIConnectionError` wrapping S4 error label | Agent maps all LLM errors to S4_CONNECTION_ERROR | Check CF logs — it's usually AI Core, not S/4HANA |
| `failed to load destination configuration … env var not found: CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID` | SDK doesn't read `VCAP_SERVICES` — binding exists but SDK can't see it | Add `_bridge_vcap_to_sdk()` from Step 2 before `create_client()` |
| `tenant subdomain must be provided for subscriber access` | `get_subaccount_destination()` defaults to `SUBSCRIBER_FIRST` which requires a tenant | Pass `access_strategy=AccessStrategy.PROVIDER_ONLY` (single-tenant apps running in their own subaccount) |

### Set AI Core credentials directly (if AICORE destination not yet configured in BTP)

```bash
cf set-env <app-name> AICORE_AUTH_URL      "https://<subdomain>.authentication.<region>.hana.ondemand.com/oauth/token"
cf set-env <app-name> AICORE_CLIENT_ID     "sb-..."
cf set-env <app-name> AICORE_CLIENT_SECRET "..."
cf set-env <app-name> AICORE_BASE_URL      "https://api.ai.prod.<region>.aws.ml.hana.ondemand.com/v2"
cf set-env <app-name> AICORE_RESOURCE_GROUP "default"
cf restage <app-name>
```

Get values from BTP Cockpit → AI Core service instance → Service Keys.
