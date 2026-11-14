if __name__ == "__main__":
    import subprocess
    import sys
    from pathlib import Path

    # Start Uvicorn as a module so reload workers can import the app package on Windows.
    backend_dir = Path(__file__).resolve().parents[1]
    command = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", "8000", "--reload",
    ]
    env_file = backend_dir / ".env"
    if env_file.is_file():
        command.extend(["--env-file", str(env_file)])
    try:
        raise SystemExit(subprocess.call(command, cwd=backend_dir))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .logic import editable_stream, equal_shares
from .models import Activity
from .schemas import CampaignCreate, OfferAdd, OfferShares
from .services import ServiceError, get_service

app = FastAPI(title="Adrobot Campaign Manager", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[part.strip() for part in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])


@app.exception_handler(ServiceError)
def service_error(_, exc: ServiceError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "mode": settings.keitaro_mode}


@app.get("/api/options")
def options(db: Session = Depends(get_db)) -> dict:
    return get_service(db).options()


@app.get("/api/campaigns")
def campaigns(db: Session = Depends(get_db)) -> list[dict]:
    return get_service(db).campaigns()


@app.get("/api/campaigns/{campaign_id}")
def campaign_detail(campaign_id: int, db: Session = Depends(get_db)) -> dict:
    return get_service(db).detail(campaign_id)


@app.post("/api/campaigns", status_code=201)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)) -> dict:
    result = get_service(db).create(data)
    db.add(Activity(kind="create", campaign_id=result["id"], summary=f"Создана кампания «{result['name']}»"))
    db.commit()
    return result


def _stream_offers(campaign_id: int, stream_id: int, db: Session) -> list[dict]:
    campaign = get_service(db).detail(campaign_id)
    stream = next((item for item in campaign["streams"] if item["id"] == stream_id), None)
    if not stream or not editable_stream(stream):
        raise ServiceError("Поток с офферами не найден", 404)
    return stream.get("offers", [])


def _save_offers(campaign_id: int, stream_id: int, offers: list[dict], kind: str, summary: str, db: Session) -> dict:
    result = get_service(db).update_offers(campaign_id, stream_id, offers)
    db.add(Activity(kind=kind, campaign_id=campaign_id, summary=summary))
    db.commit()
    return result


@app.post("/api/campaigns/{campaign_id}/streams/{stream_id}/offers")
def add_offer(campaign_id: int, stream_id: int, data: OfferAdd, db: Session = Depends(get_db)) -> dict:
    current = _stream_offers(campaign_id, stream_id, db)
    ids = [item["offer_id"] for item in current]
    if data.offer_id in ids:
        raise ServiceError("Оффер уже есть в этом потоке")
    return _save_offers(campaign_id, stream_id, equal_shares([*ids, data.offer_id]), "add_offer", f"Добавлен оффер #{data.offer_id}", db)


@app.delete("/api/campaigns/{campaign_id}/streams/{stream_id}/offers/{offer_id}")
def remove_offer(campaign_id: int, stream_id: int, offer_id: int, db: Session = Depends(get_db)) -> dict:
    current = _stream_offers(campaign_id, stream_id, db)
    ids = [item["offer_id"] for item in current]
    if offer_id not in ids:
        raise ServiceError("Оффер отсутствует в этом потоке", 404)
    if len(ids) == 1:
        raise ServiceError("В потоке должен остаться хотя бы один оффер")
    return _save_offers(campaign_id, stream_id, equal_shares([item for item in ids if item != offer_id]), "remove_offer", f"Удалён оффер #{offer_id}", db)


@app.put("/api/campaigns/{campaign_id}/streams/{stream_id}/offers")
def update_shares(campaign_id: int, stream_id: int, data: OfferShares, db: Session = Depends(get_db)) -> dict:
    ids = {item["offer_id"] for item in _stream_offers(campaign_id, stream_id, db)}
    if {item["offer_id"] for item in data.offers} != ids:
        raise ServiceError("Список офферов изменился. Обновите страницу")
    return _save_offers(campaign_id, stream_id, data.offers, "shares", "Обновлены доли офферов", db)


@app.get("/api/activity")
def activity(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Activity).order_by(Activity.id.desc()).limit(10)).all()
    return [{"id": row.id, "kind": row.kind, "campaign_id": row.campaign_id, "summary": row.summary, "created_at": row.created_at.isoformat()} for row in rows]
