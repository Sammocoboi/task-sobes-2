from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DemoOption(Base):
    __tablename__ = "demo_options"
    kind: Mapped[str] = mapped_column(String(30), primary_key=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(30), default="active")


class DemoCampaign(Base):
    __tablename__ = "demo_campaigns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str] = mapped_column(String(255))
    geo: Mapped[list] = mapped_column(JSON)
    domain_id: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[int] = mapped_column(Integer)
    traffic_source_id: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    streams: Mapped[list["DemoStream"]] = relationship(back_populates="campaign", cascade="all, delete-orphan", order_by="DemoStream.position")


class DemoStream(Base):
    __tablename__ = "demo_streams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("demo_campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(30))
    schema: Mapped[str] = mapped_column(String(30))
    action_type: Mapped[str] = mapped_column(String(50))
    action_payload: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    filters: Mapped[list] = mapped_column(JSON)
    offers: Mapped[list] = mapped_column(JSON)
    campaign: Mapped[DemoCampaign] = relationship(back_populates="streams")


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(50))
    campaign_id: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
