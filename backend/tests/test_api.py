from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import DemoOption


def test_create_and_edit_campaign():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for kind, ids in {"domains": [1], "groups": [2], "sources": [3], "offers": [10, 11, 12]}.items():
            db.add_all(DemoOption(kind=kind, id=item_id, name=f"{kind}-{item_id}") for item_id in ids)
        db.commit()

    def test_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    try:
        client = TestClient(app)
        created = client.post("/api/campaigns", json={"name": "Test campaign", "geo": ["mx", "AU", "mx"], "offer_id": 10, "domain_id": 1, "group_id": 2, "traffic_source_id": 3})
        assert created.status_code == 201, created.text
        campaign = created.json()
        assert campaign["geo"] == ["MX", "AU"]
        assert len(campaign["streams"]) == 2
        assert campaign["streams"][0]["filters"] == [{"name": "geo", "mode": "accept", "payload": ["MX", "AU"]}]
        assert campaign["streams"][0]["action_payload"] == "https://www.google.com/"
        stream = campaign["streams"][1]
        assert stream["offers"][0]["share"] == 100
        path = f"/api/campaigns/{campaign['id']}/streams/{stream['id']}/offers"
        for offer_id in (11, 12):
            response = client.post(path, json={"offer_id": offer_id})
            assert response.status_code == 200, response.text
        assert [item["share"] for item in response.json()["streams"][1]["offers"]] == [34, 33, 33]
        invalid = client.put(path, json={"offers": [{"offer_id": 10, "share": 40}, {"offer_id": 11, "share": 40}, {"offer_id": 12, "share": 10}]})
        assert invalid.status_code == 422
        saved = client.put(path, json={"offers": [{"offer_id": 10, "share": 20}, {"offer_id": 11, "share": 30}, {"offer_id": 12, "share": 50}]})
        assert saved.status_code == 200, saved.text
        removed = client.delete(f"{path}/11")
        assert [item["share"] for item in removed.json()["streams"][1]["offers"]] == [50, 50]
        assert client.delete(f"{path}/12").status_code == 200
        assert client.delete(f"{path}/10").status_code == 400
        assert len(client.get("/api/activity").json()) == 6
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
