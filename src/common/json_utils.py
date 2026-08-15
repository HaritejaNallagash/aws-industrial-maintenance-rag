"""Small JSON helpers shared across Lambda handlers."""

import json
from decimal import Decimal
from typing import Any


class EnhancedJsonEncoder(json.JSONEncoder):
    """Encode Decimal values that can appear in DynamoDB responses."""

    def default(self, value: Any) -> Any:
        """Convert DynamoDB ``Decimal`` values into plain JSON numbers."""
        if isinstance(value, Decimal):
            if value % 1 == 0:
                return int(value)
            return float(value)
        return super().default(value)


def dumps(data: Any) -> str:
    """Serialize JSON with stable defaults used by API responses and S3 files.

    The project sorts keys and removes unnecessary whitespace so generated JSON
    stays deterministic. That makes debugging and comparing outputs easier.
    """
    return json.dumps(data, cls=EnhancedJsonEncoder, separators=(",", ":"), sort_keys=True)


def loads_body(event: dict) -> dict:
    """Parse an API Gateway body while tolerating direct Lambda test events.

    The same query Lambda can be triggered from:

    - the browser through the Lambda Function URL, where the payload is usually
      a JSON string stored under ``event["body"]``
    - direct Lambda console tests, where the event is often already a dict

    This helper normalizes both cases into a plain Python dict.
    """
    body = event.get("body", event)
    if isinstance(body, str):
        return json.loads(body or "{}")
    if isinstance(body, dict):
        return body
    return {}
