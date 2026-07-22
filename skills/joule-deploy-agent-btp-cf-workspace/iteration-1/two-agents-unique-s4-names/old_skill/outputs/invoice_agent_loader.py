# Load credentials from BTP Destination Service before any other import
# (skill-snapshot references/vcap-bridge.md — inserted at top of invoice-agent/app/main.py)
import json as _json
import logging as _logging
import os as _os

_logger_boot = _logging.getLogger(__name__)


def _setenv_if_missing(key, value):
    if value and not _os.environ.get(key):
        _os.environ[key] = str(value)


def _bridge_vcap_to_sdk() -> None:
    """Populate CLOUD_SDK_CFG_DESTINATION_DEFAULT_* from VCAP_SERVICES when running on CF.

    sap-cloud-sdk reads credentials from K8s secret mounts or these env vars.
    On plain CF the binding lands in VCAP_SERVICES, so we bridge the gap here.
    Only runs when VCAP_SERVICES is present (i.e. on CF); no-ops locally.
    """
    vcap_raw = _os.environ.get("VCAP_SERVICES")
    if not vcap_raw:
        return
    try:
        vcap = _json.loads(vcap_raw)
    except Exception:
        return

    dest_creds = None
    for _svc_name, instances in vcap.items():
        if "destination" in _svc_name.lower():
            if instances:
                dest_creds = instances[0].get("credentials", {})
                break

    if not dest_creds:
        return

    mapping = {
        "clientid":     "CLIENTID",
        "clientsecret": "CLIENTSECRET",
        "url":          "URL",        # OAuth token endpoint base
        "uri":          "URI",        # Destination service REST base
        "identityzone": "IDENTITYZONE",
    }
    for vcap_key, sdk_suffix in mapping.items():
        value = dest_creds.get(vcap_key)
        if value:
            _setenv_if_missing(f"CLOUD_SDK_CFG_DESTINATION_DEFAULT_{sdk_suffix}", value)

    _logger_boot.info("Bridged VCAP_SERVICES destination binding → CLOUD_SDK_CFG_DESTINATION_DEFAULT_* env vars")


def _load_destinations() -> None:
    try:
        from sap_cloud_sdk.destination import AccessStrategy, create_client
        client = create_client()

        # S/4HANA — BasicAuthentication destination
        # AccessStrategy.PROVIDER_ONLY: single-tenant app running in its own subaccount.
        # The default (SUBSCRIBER_FIRST) requires a tenant subdomain and will fail here.
        try:
            dest = client.get_subaccount_destination("S4HANA", access_strategy=AccessStrategy.PROVIDER_ONLY)
            props = dest.properties or {}
            _setenv_if_missing("S4_BASE_URL", dest.url)
            _setenv_if_missing("S4_USERNAME", props.get("User") or props.get("user"))
            _setenv_if_missing("S4_PASSWORD", props.get("Password") or props.get("password"))
            _logger_boot.info("S4HANA credentials loaded from destination")
        except Exception as e:
            _logger_boot.warning("Could not load S4HANA destination: %s", e)

        # AI Core — additional properties use aicore_* naming (exact BTP export format)
        try:
            dest = client.get_subaccount_destination("AICORE", access_strategy=AccessStrategy.PROVIDER_ONLY)
            props = dest.properties or {}
            _setenv_if_missing("AICORE_AUTH_URL",       props.get("aicore_auth_url"))
            _setenv_if_missing("AICORE_CLIENT_ID",      props.get("aicore_client_id"))
            _setenv_if_missing("AICORE_CLIENT_SECRET",  props.get("aicore_client_secret"))
            _setenv_if_missing("AICORE_BASE_URL",       props.get("aicore_base_url") or dest.url)
            _setenv_if_missing("AICORE_RESOURCE_GROUP", props.get("aicore_resource_group"))
            _logger_boot.info("AICORE credentials loaded from destination")
        except Exception as e:
            _logger_boot.warning("Could not load AICORE destination: %s", e)

    except Exception as e:
        _logger_boot.warning("Destination service unavailable, using env vars: %s", e)


_bridge_vcap_to_sdk()
_load_destinations()
