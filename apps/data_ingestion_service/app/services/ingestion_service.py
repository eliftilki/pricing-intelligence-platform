import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.collectors.amazon_collector import AmazonCollector
from app.collectors.hepsiburada_collector import HepsiburadaCollector
from app.collectors.trendyol_collector import TrendyolCollector
from app.core.circuit_breaker import MarketplaceCircuitBreaker
from app.normalizers.competitor_normalizer import CompetitorNormalizer
from app.repositories.competitor_repository import CompetitorRepository
from app.collectors.trendyol_search_collector import TrendyolSearchCollector
from app.collectors.hepsiburada_search_collector import HepsiburadaSearchCollector
from app.collectors.amazon_search_collector import AmazonSearchCollector
from app.schemas.ingestion_schema import IngestionRunRequest, IngestionRunResponse, IngestionRunWithUrlsRequest, SearchAndRunRequest

SEARCH_COLLECTOR_MAP = {
    "TRENDYOL": TrendyolSearchCollector,
    "HEPSIBURADA": HepsiburadaSearchCollector,
    "AMAZON": AmazonSearchCollector,
}

logger = logging.getLogger(__name__)

COLLECTOR_MAP = {
    "TRENDYOL": TrendyolCollector,
    "HEPSIBURADA": HepsiburadaCollector,
    "AMAZON": AmazonCollector,
}


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompetitorRepository(db)
        self.normalizer = CompetitorNormalizer()

        # Circuit breakers per marketplace
        self.cb_trendyol = MarketplaceCircuitBreaker("TRENDYOL", failure_threshold=5, reset_timeout=60)
        self.cb_hepsiburada = MarketplaceCircuitBreaker("HEPSIBURADA", failure_threshold=5, reset_timeout=60)
        self.cb_amazon = MarketplaceCircuitBreaker("AMAZON", failure_threshold=5, reset_timeout=60)

        self.circuit_breakers = {
            "TRENDYOL": self.cb_trendyol,
            "HEPSIBURADA": self.cb_hepsiburada,
            "AMAZON": self.cb_amazon,
        }

    async def search_and_run(self, payload: SearchAndRunRequest) -> IngestionRunResponse:
        """Ürün adıyla 3 sitede URL arar, seller_products'a kaydeder, ardından scrape çalıştırır."""
        marketplaces = [m.upper() for m in payload.marketplaces]

        # Her marketplace için paralel arama
        async def _search_one(marketplace: str) -> tuple[str, str | None]:
            collector_cls = SEARCH_COLLECTOR_MAP.get(marketplace)
            if not collector_cls:
                return marketplace, None
            try:
                result = await collector_cls().search(payload.query, max_results=1)
                results = result.get("results", [])
                if results:
                    return marketplace, results[0]["url"]
            except Exception as e:
                logger.error(f"{marketplace} arama hatası: {e}")
            return marketplace, None

        pairs = await asyncio.gather(*[_search_one(m) for m in marketplaces])
        found_urls = {m: url for m, url in pairs if url}

        if not found_urls:
            return IngestionRunResponse(
                job_id=payload.product_id,
                status="FAILED",
                message=f"'{payload.query}' için hiçbir sitede ürün bulunamadı.",
                scrape_counts={},
            )

        logger.info(f"Bulunan URL'ler: {found_urls}")

        # Bulunan URL'leri seller_products'a kaydet
        for marketplace, url in found_urls.items():
            self.repo.get_or_create_seller_product(
                company_id=payload.company_id,
                product_id=payload.product_id,
                marketplace=marketplace,
                url=url,
            )
        self.db.commit()

        # Scrape çalıştır
        return await self._run_internal(IngestionRunRequest(
            product_id=payload.product_id,
            marketplaces=list(found_urls.keys()),
        ))

    async def run_with_urls(self, payload: IngestionRunWithUrlsRequest) -> IngestionRunResponse:
        """URL'leri doğrudan parametre olarak alır, DB'de seller_product yoksa oluşturur."""
        urls = {k.upper(): v for k, v in payload.urls.items()}

        seller_products = []
        for marketplace, url in urls.items():
            sp = self.repo.get_or_create_seller_product(
                company_id=payload.company_id,
                product_id=payload.product_id,
                marketplace=marketplace,
                url=url,
            )
            seller_products.append(sp)
        self.db.commit()

        run_request = IngestionRunRequest(
            product_id=payload.product_id,
            marketplaces=list(urls.keys()),
        )
        return await self._run_internal(run_request)

    async def run(self, payload: IngestionRunRequest) -> IngestionRunResponse:
        try:
            return await asyncio.wait_for(self._run_internal(payload), timeout=180.0)
        except asyncio.TimeoutError:
            logger.error(f"Ingestion timeout for product_id={payload.product_id}")
            return IngestionRunResponse(
                job_id=payload.product_id,
                status="FAILED",
                message="Ingestion operation timed out after 180 seconds",
                scrape_counts={},
            )

    async def _run_internal(self, payload: IngestionRunRequest) -> IngestionRunResponse:
        product_id = payload.product_id
        marketplaces = [m.upper() for m in payload.marketplaces]

        seller_products = self.repo.get_seller_products_for_marketplaces(product_id, marketplaces)
        if not seller_products:
            return IngestionRunResponse(
                job_id=product_id,
                status="FAILED",
                message=f"No seller_products found for product_id={product_id} and marketplaces={marketplaces}",
                scrape_counts={},
            )

        session = self.repo.create_session(product_id)
        self.db.commit()

        sp_map = {sp.marketplace: sp for sp in seller_products}
        scrape_records = {}
        for marketplace, sp in sp_map.items():
            ms = self.repo.create_marketplace_scrape(
                session_id=session.id,
                seller_product_id=sp.id,
                product_id=product_id,
                marketplace=marketplace,
                url=sp.marketplace_url,
            )
            scrape_records[marketplace] = ms
        self.db.commit()

        tasks = {}
        skipped_marketplaces = {}
        for marketplace, sp in sp_map.items():
            cb = self.circuit_breakers.get(marketplace)

            # Check circuit breaker availability
            if cb and not cb.is_available():
                logger.warning(f"Circuit breaker OPEN for {marketplace}, skipping scrape")
                skipped_marketplaces[marketplace] = scrape_records[marketplace]
                continue

            collector_cls = COLLECTOR_MAP.get(marketplace)
            if collector_cls:
                tasks[marketplace] = asyncio.wait_for(
                    collector_cls().scrape_product_by_url(sp.marketplace_url), timeout=60.0
                )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        raw_by_marketplace = dict(zip(tasks.keys(), results))

        scrape_counts: dict[str, int] = {}
        success_count = 0

        # Handle skipped marketplaces (circuit breaker OPEN)
        for marketplace, ms in skipped_marketplaces.items():
            self.repo.update_marketplace_scrape(
                scrape_id=ms.id,
                status="FAILED",
                error_message="Skipped because circuit breaker is open: marketplace temporarily unavailable",
            )
            scrape_counts[marketplace] = 0

        for marketplace, raw in raw_by_marketplace.items():
            ms = scrape_records.get(marketplace)
            if ms is None:
                continue

            if isinstance(raw, Exception):
                logger.error("Scrape failed for %s: %s", marketplace, raw)
                # Record failure in circuit breaker
                cb = self.circuit_breakers.get(marketplace)
                if cb:
                    cb.record_failure()

                self.repo.update_marketplace_scrape(
                    scrape_id=ms.id,
                    status="FAILED",
                    error_message=str(raw),
                )
                scrape_counts[marketplace] = 0
                continue

            product_info = raw.get("product", {})
            scraped_at_str = raw.get("scraped_at")
            scraped_at: Optional[datetime] = None
            if scraped_at_str:
                try:
                    scraped_at = datetime.fromisoformat(scraped_at_str)
                except ValueError:
                    pass

            self.repo.update_marketplace_scrape(
                scrape_id=ms.id,
                status="SUCCESS",
                product_name=product_info.get("name"),
                product_sku=product_info.get("sku"),
                product_brand=product_info.get("brand"),
                product_rating=product_info.get("rating"),
                product_review_count=product_info.get("review_count"),
                scraped_at=scraped_at or datetime.now(timezone.utc),
                raw_payload=raw,
            )

            # Record success in circuit breaker
            cb = self.circuit_breakers.get(marketplace)
            if cb:
                cb.record_success()

            listings, price_histories = self.normalizer.normalize(
                raw=raw,
                scrape_id=ms.id,
                product_id=product_id,
            )

            if listings:
                self.repo.bulk_create_listings(listings)
            if price_histories:
                self.repo.bulk_create_price_history(price_histories)

            scrape_counts[marketplace] = len(listings)
            success_count += 1

        self.db.commit()

        total = sum(scrape_counts.values())
        attempted_count = len(scrape_records)
        if success_count == 0:
            status = "FAILED"
        elif success_count < attempted_count:
            status = "PARTIAL"
        else:
            status = "COMPLETED"

        self.repo.update_session_status(
            session_id=session.id,
            status=status,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.commit()

        marketplace_summary = ", ".join(
            f"{m}: {c}" for m, c in scrape_counts.items()
        )
        message = f"Scraped {success_count}/{attempted_count} marketplaces. {total} competitors found. ({marketplace_summary})"

        return IngestionRunResponse(
            job_id=session.id,
            status=status,
            message=message,
            scrape_counts=scrape_counts,
        )
