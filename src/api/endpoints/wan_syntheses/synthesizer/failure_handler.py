from __future__ import annotations

import os
from typing import Any

from store import assign

COLLECTION = "wan-syntheses"


def _reason(event: dict[str, Any]) -> str:
    condition = event.get("requestContext", {}).get("condition")
    if condition:
        return f"synthesizer invocation failed ({condition})"
    return "synthesizer terminated before completing (timed out or crashed)"


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    synthesis_id = int(event["requestPayload"]["synthesis"])
    assign(
        os.environ["STORE_TABLE"], COLLECTION, str(synthesis_id),
        {"status": "timeout", "reason": _reason(event)},
    )
    return {"status": "timeout", "synthesis": synthesis_id}
