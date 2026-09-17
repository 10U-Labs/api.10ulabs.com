import json
from typing import Any, Dict

RACK_CONFIGURATIONS = "/rack-configurations"
RACK_CONFIGURATION = RACK_CONFIGURATIONS + "/{id}"
UNKNOWN = "ZZZZZZZZZ"


def post(body: Any) -> Dict[str, Any]:
    raw = body if isinstance(body, str) else json.dumps(body)
    return {"resource": RACK_CONFIGURATIONS, "httpMethod": "POST", "body": raw}


def get(config_hash: str) -> Dict[str, Any]:
    return {"resource": RACK_CONFIGURATION, "httpMethod": "GET",
            "pathParameters": {"id": config_hash}}


def submission(configuration: Any, **extra: Any) -> Dict[str, Any]:
    return {"device_id": "device-1", "configuration": configuration, **extra}
