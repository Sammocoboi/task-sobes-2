from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .logic import campaign_payload, editable_stream, geo_from_filter_payload, stream_payloads
from .models import DemoCampaign, DemoOption, DemoStream
from .schemas import CampaignCreate


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


class KeitaroService:
    def __init__(self) -> None:
        if not settings.keitaro_base_url or not settings.keitaro_api_key:
            raise ServiceError("Для live режима задайте KEITARO_BASE_URL и KEITARO_API_KEY", 503)
        self.client = httpx.Client(base_url=settings.keitaro_base_url.rstrip("/") + "/admin_api/v1/", headers={"Api-Key": settings.keitaro_api_key}, timeout=20.0)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.client.request(method, path.lstrip("/"), **kwargs)
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            status = 404 if exc.response.status_code == 404 else 502
            raise ServiceError(f"Keitaro: HTTP {exc.response.status_code}. {detail}", status) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise ServiceError(f"Ошибка соединения с Keitaro: {exc}", 502) from exc

    def options(self) -> dict:
        return {
            "domains": self._request("GET", "domains"),
            "groups": self._request("GET", "groups", params={"type": "campaigns"}),
            "sources": self._request("GET", "traffic_sources"),
            "offers": self._request("GET", "offers"),
        }

    def campaigns(self) -> list[dict]:
        return self._request("GET", "campaigns")

    def detail(self, campaign_id: int) -> dict:
        campaign = self._request("GET", f"campaigns/{campaign_id}")
        streams = self._request("GET", f"campaigns/{campaign_id}/streams")
        campaign["streams"] = streams
        campaign["geo"] = next((
            geo_from_filter_payload(item.get("payload"))
            for stream in streams
            for item in (stream.get("filters") or [])
            if item.get("name") in {"country", "geo"} and item.get("mode") == "accept"
        ), [])
        return campaign

    def create(self, data: CampaignCreate) -> dict:
        options = self.options()
        missing = [label for kind, label in (
            ("domains", "домены"), ("groups", "группы"), ("sources", "источники трафика"), ("offers", "офферы"),
        ) if not any(row.get("state", "active") == "active" for row in options[kind])]
        if missing:
            raise ServiceError(f"Создание кампании недоступно: Keitaro не вернул доступные справочники ({', '.join(missing)}).", 409)
        for kind, entity_id in (("domains", data.domain_id), ("groups", data.group_id), ("sources", data.traffic_source_id), ("offers", data.offer_id)):
            if not any(row.get("id") == entity_id and row.get("state", "active") == "active" for row in options[kind]):
                raise ServiceError(f"Выбранный {kind} #{entity_id} не найден или неактивен")
        campaign = self._request("POST", "campaigns", json=campaign_payload(data.name, data.domain_id, data.group_id, data.traffic_source_id))
        campaign_id = campaign["id"]
        try:
            for payload in stream_payloads(campaign_id, data.geo, data.offer_id, settings.google_redirect_url):
                self._request("POST", "streams", json=payload)
        except ServiceError as exc:
            try:
                self._request("DELETE", f"campaigns/{campaign_id}")
            except ServiceError:
                raise ServiceError(f"Потоки не созданы; проверьте кампанию #{campaign_id} в Keitaro. {exc.message}", 502) from exc
            raise ServiceError(f"Не удалось создать потоки, кампания #{campaign_id} перенесена в архив. {exc.message}", 502) from exc
        return self.detail(campaign_id)

    def update_offers(self, campaign_id: int, stream_id: int, offers: list[dict[str, int]]) -> dict:
        detail = self.detail(campaign_id)
        stream = next((item for item in detail["streams"] if item["id"] == stream_id), None)
        if not stream or not editable_stream(stream):
            raise ServiceError("Поток с офферами не найден", 404)
        available = {item["id"] for item in self._request("GET", "offers") if item.get("state", "active") == "active"}
        if any(item["offer_id"] not in available for item in offers):
            raise ServiceError("Один из офферов не найден или неактивен")
        self._request("PUT", f"streams/{stream_id}", json={"offers": [{**item, "state": "active"} for item in offers]})
        return self.detail(campaign_id)


class DemoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def options(self) -> dict:
        rows = self.db.scalars(select(DemoOption).order_by(DemoOption.id)).all()
        return {name: [{"id": row.id, "name": row.name, "state": row.state} for row in rows if row.kind == name] for name in ("domains", "groups", "sources", "offers")}

    def campaigns(self) -> list[dict]:
        rows = self.db.scalars(select(DemoCampaign).order_by(DemoCampaign.id.desc())).all()
        return [self._campaign(row, False) for row in rows]

    def detail(self, campaign_id: int) -> dict:
        row = self.db.get(DemoCampaign, campaign_id)
        if not row:
            raise ServiceError("Кампания не найдена", 404)
        return self._campaign(row, True)

    def _campaign(self, row: DemoCampaign, include_streams: bool) -> dict:
        result = {"id": row.id, "name": row.name, "alias": row.alias, "geo": row.geo, "domain_id": row.domain_id, "group_id": row.group_id, "traffic_source_id": row.traffic_source_id, "state": row.state, "created_at": row.created_at.isoformat()}
        if include_streams:
            result["streams"] = [{"id": s.id, "campaign_id": row.id, "name": s.name, "type": s.type, "schema": s.schema, "action_type": s.action_type, "action_payload": s.action_payload, "position": s.position, "filters": s.filters, "offers": s.offers} for s in row.streams]
        return result

    def create(self, data: CampaignCreate) -> dict:
        options = self.options()
        for kind, entity_id in (("domains", data.domain_id), ("groups", data.group_id), ("sources", data.traffic_source_id), ("offers", data.offer_id)):
            if not any(row["id"] == entity_id and row["state"] == "active" for row in options[kind]):
                raise ServiceError(f"Выбранный {kind} #{entity_id} не найден или неактивен")
        row = DemoCampaign(name=data.name, alias=f"campaign-{len(self.campaigns())+1}", geo=data.geo, domain_id=data.domain_id, group_id=data.group_id, traffic_source_id=data.traffic_source_id)
        self.db.add(row)
        self.db.flush()
        for payload in stream_payloads(row.id, data.geo, data.offer_id, settings.google_redirect_url):
            self.db.add(DemoStream(campaign_id=row.id, name=payload["name"], type=payload["type"], schema=payload["schema"], action_type=payload["action_type"], action_payload=payload.get("action_payload"), position=payload["position"], filters=payload.get("filters", []), offers=payload.get("offers", [])))
        self.db.commit()
        return self.detail(row.id)

    def update_offers(self, campaign_id: int, stream_id: int, offers: list[dict[str, int]]) -> dict:
        row = self.db.get(DemoStream, stream_id)
        if not row or row.campaign_id != campaign_id or (not row.offers and row.schema != "landings"):
            raise ServiceError("Поток с офферами не найден", 404)
        available = {item["id"] for item in self.options()["offers"] if item["state"] == "active"}
        if any(item["offer_id"] not in available for item in offers):
            raise ServiceError("Один из офферов не найден или неактивен")
        row.offers = [{**item, "state": "active"} for item in offers]
        self.db.commit()
        return self.detail(campaign_id)


@lru_cache(maxsize=1)
def live_service() -> KeitaroService:
    return KeitaroService()


def get_service(db: Session) -> KeitaroService | DemoService:
    return live_service() if settings.keitaro_mode == "live" else DemoService(db)
