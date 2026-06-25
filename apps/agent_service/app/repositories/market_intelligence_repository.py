from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.market_event import EventCalendar, MarketEventFeatures
from app.models.product import Product
from app.services.category_taxonomy import normalize_category


class MarketIntelligenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_product(self, product_id: UUID) -> Product | None:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_active_event(self, category: str | None, today: date | None = None) -> EventCalendar | None:
        """
        Bugun aktif olan veya en yakinda baslayacak, urunun kategorisiyle
        eslesen kampanyayi getirir. affected_categories JSONB bir liste
        oldugundan, kategori eslesmesi Postgres'in @> (contains) operatoru
        ile yapilir. Kategori bilinmiyorsa (None) hangi kampanyanin ilgili
        oldugu belirlenemeyecegi icin hic event aranmaz - aksi halde
        kategoriyle ilgisiz bir kampanya "tespit edildi" sayilip yanlis
        demand sinyali uretilir.
        """
        if not category:
            return None

        today = today or datetime.now(timezone.utc).date()
        parent_category = normalize_category(category)

        return (
            self.db.query(EventCalendar)
            .filter(
                EventCalendar.end_date >= today,
                EventCalendar.affected_categories.contains([parent_category]),
            )
            .order_by(EventCalendar.start_date.asc())
            .first()
        )

    def get_category_peer_products(
        self,
        category: str,
        exclude_product_id: UUID,
        limit: int = 5,
    ) -> list[Product]:
        """
        Secenek A: Ayni kategoride, ayni urun haric, bizim platformda
        takip edilen diger urunler. Category Analyzer Tool bu listenin
        her birini Google Trends'te sorgulayip kategori ortalamasini cikarir.
        """
        if not category:
            return []

        return (
            self.db.query(Product)
            .filter(Product.category == category, Product.id != exclude_product_id)
            .order_by(Product.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_fresh_market_event_features(
        self,
        product_id: UUID,
        max_age_hours: int = 24,
    ) -> MarketEventFeatures | None:
        """Trend cache: bu sureden daha taze bir kayit varsa pytrends'e tekrar gidilmez."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        return (
            self.db.query(MarketEventFeatures)
            .filter(
                MarketEventFeatures.product_id == product_id,
                MarketEventFeatures.generated_at >= cutoff,
            )
            .order_by(MarketEventFeatures.generated_at.desc())
            .first()
        )

    def create_market_event_features(self, **fields) -> MarketEventFeatures:
        obj = MarketEventFeatures(**fields)
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_agent_run(self, product_id: UUID, input_payload: dict) -> AgentRun:
        run = AgentRun(
            product_id=product_id,
            run_type="MARKET_INTELLIGENCE",
            status="STARTED",
            input_payload=input_payload,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish_agent_run(
        self,
        run: AgentRun,
        status: str,
        output_payload: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        run.status = status
        run.output_payload = output_payload
        run.error_message = error_message
        run.finished_at = datetime.now(timezone.utc)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
