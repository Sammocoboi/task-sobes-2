import json
import re
from collections.abc import Sequence


def equal_shares(offer_ids: Sequence[int]) -> list[dict[str, int]]:
    """Split exactly 100 integer percentage points, stable in input order."""
    if not offer_ids or len(set(offer_ids)) != len(offer_ids):
        raise ValueError("Expected nonempty unique offer IDs")
    base, remainder = divmod(100, len(offer_ids))
    return [{"offer_id": offer_id, "share": base + (index < remainder)} for index, offer_id in enumerate(offer_ids)]


def campaign_payload(name: str, domain_id: int, group_id: int, source_id: int) -> dict:
    return {"alias": "", "name": name, "type": "position", "domain_id": domain_id, "group_id": str(group_id), "traffic_source_id": source_id}


def stream_payloads(campaign_id: int, geo: list[str], offer_id: int, google_url: str) -> tuple[dict, dict]:
    """A regular GEO flow is checked before the default offer flow."""
    google = {
        "campaign_id": campaign_id,
        "type": "regular",
        "name": f"{', '.join(geo)} → Google",
        "position": 1,
        "schema": "redirect",
        "action_type": "http",
        "action_payload": google_url,
        "collect_clicks": True,
        "filters": [{"name": "country", "mode": "accept", "payload": geo}],
    }
    offer = {
        "campaign_id": campaign_id,
        "type": "default",
        "name": "Офферы",
        "position": 2,
        "schema": "landings",
        "action_type": "http",
        "collect_clicks": True,
        "offers": [{"offer_id": offer_id, "share": 100, "state": "active"}],
    }
    return google, offer


def editable_stream(stream: dict) -> bool:
    return bool(stream.get("offers")) or stream.get("schema") == "landings"


def geo_from_filter_payload(value: object) -> list[str]:
    """Keitaro versions return filter payloads as arrays or serialized strings."""
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            decoded = value
        value = decoded
    if isinstance(value, list):
        return [str(item).upper() for item in value]
    if isinstance(value, str):
        return [item.upper() for item in re.split(r"[\s,;]+", value) if item]
    return []
