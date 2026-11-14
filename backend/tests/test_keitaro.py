import httpx

from app.services import KeitaroService
from app.schemas import CampaignCreate
from app.logic import geo_from_filter_payload


def test_geo_filter_payload_formats():
    assert geo_from_filter_payload('["mx", "AU"]') == ["MX", "AU"]
    assert geo_from_filter_payload("mx, AU") == ["MX", "AU"]


def test_keitaro_payloads_and_partial_offer_update():
    sent = []
    streams = []

    def respond(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        if method == "GET" and path in ("/admin_api/v1/domains", "/admin_api/v1/groups", "/admin_api/v1/traffic_sources", "/admin_api/v1/offers"):
            ids = {"domains": 1, "groups": 2, "traffic_sources": 3, "offers": 10}
            return httpx.Response(200, json=[{"id": ids[path.rsplit('/', 1)[-1]], "name": "test", "state": "active"}])
        if method == "POST" and path.endswith("/campaigns"):
            sent.append((method, path, request.content))
            return httpx.Response(200, json={"id": 7, "name": "test"})
        if method == "POST" and path.endswith("/streams"):
            import json
            streams.append(json.loads(request.content))
            return httpx.Response(200, json={"id": len(streams), **streams[-1]})
        if method == "GET" and path.endswith("/campaigns/7"):
            return httpx.Response(200, json={"id": 7, "name": "test"})
        if method == "GET" and path.endswith("/campaigns/7/streams"):
            return httpx.Response(200, json=[{"id": index + 1, **stream} for index, stream in enumerate(streams)])
        if method == "PUT" and path.endswith("/streams/2"):
            import json
            payload = json.loads(request.content)
            sent.append((method, path, payload))
            streams[1]["offers"] = payload["offers"]
            return httpx.Response(200, json={"id": 2, **streams[1]})
        return httpx.Response(404, text=path)

    service = object.__new__(KeitaroService)
    service.client = httpx.Client(base_url="https://tracker.example/admin_api/v1/", transport=httpx.MockTransport(respond))
    created = service.create(CampaignCreate(name="test", geo=["MX"], offer_id=10, domain_id=1, group_id=2, traffic_source_id=3))
    assert created["id"] == 7
    assert streams[0]["filters"] == [{"name": "geo", "mode": "accept", "payload": ["MX"]}]
    assert streams[0]["action_payload"] == "https://www.google.com/"
    assert streams[1]["offers"] == [{"offer_id": 10, "share": 100, "state": "active"}]
    service.update_offers(7, 2, [{"offer_id": 10, "share": 100}])
    assert sent[-1][2] == {"offers": [{"offer_id": 10, "share": 100, "state": "active"}]}
    service.client.close()
