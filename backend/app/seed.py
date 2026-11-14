from sqlalchemy import select

from .db import SessionLocal
from .models import DemoCampaign, DemoOption, DemoStream


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(DemoOption.id).limit(1)) is not None:
            return
        for kind, values in {
            "domains": [(1, "https://in.posdk.xyz/"), (2, "https://track.example.org/")],
            "groups": [(1, "FORTESTS"), (2, "Рабочие кампании")],
            "sources": [(1, "FORTESTS"), (2, "Facebook Ads"), (3, "Google Ads")],
            "offers": [(101, "Solar — US"), (102, "Home Insurance — MX"), (103, "Finance — AU"), (104, "Travel — RO"), (105, "Health — DE")],
        }.items():
            db.add_all(DemoOption(kind=kind, id=item_id, name=name) for item_id, name in values)
        campaign = DemoCampaign(name="Winter launch / MX", alias="winter-mx", geo=["MX"], domain_id=1, group_id=1, traffic_source_id=1)
        db.add(campaign)
        db.flush()
        db.add_all([
            DemoStream(campaign_id=campaign.id, name="MX → Google", type="regular", schema="redirect", action_type="http", action_payload="https://www.google.com/", position=1, filters=[{"name": "country", "mode": "accept", "payload": ["MX"]}], offers=[]),
            DemoStream(campaign_id=campaign.id, name="Офферы", type="default", schema="landings", action_type="http", action_payload=None, position=2, filters=[], offers=[{"offer_id": 102, "share": 50, "state": "active"}, {"offer_id": 103, "share": 50, "state": "active"}]),
        ])
        db.commit()


if __name__ == "__main__":
    seed()
