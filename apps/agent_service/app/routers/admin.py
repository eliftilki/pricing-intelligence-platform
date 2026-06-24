from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.event_calendar_generator_service import EventCalendarGeneratorService

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_key(x_admin_key: str | None = Header(default=None)):
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY tanimli degil, admin endpoint'leri kapali.")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik X-Admin-Key.")


@router.post("/generate-events", dependencies=[Depends(verify_admin_key)])
def generate_events(year: int = 2026, db: Session = Depends(get_db)):
    """
    Türkiye'nin belirli bir yılı için önemli günleri otomatik olarak
    event_calendar tablosuna ekler. Startup'ta veya admin panelden çağrılır.

    Örnek: POST /admin/generate-events?year=2026
    """
    service = EventCalendarGeneratorService(db)
    result = service.generate_for_year(year)
    return {
        "status": "SUCCESS",
        "year": year,
        "events_created": result["inserted"],
        "events_updated": result["updated"],
        "message": f"{year} yılı için {result['inserted']} event eklendi, {result['updated']} event güncellendi.",
    }
