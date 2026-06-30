from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.competitor_repository import CompetitorRepository
from app.services.competitor_scoring_service import CompetitorScoringService


class CompetitorIntelligenceService:
    def __init__(self, db: Session):
        self.repository = CompetitorRepository(db)
        self.scoring_service = CompetitorScoringService()

    def analyze_product_competitors(self, product_id: UUID, lookback_hours: int = 24) -> dict:
        agent_run = self.repository.create_agent_run(
            product_id=product_id,
            input_payload={"product_id": str(product_id), "lookback_hours": lookback_hours},
        )

        try:
            listings = self.repository.get_latest_competitor_listings(product_id, lookback_hours)

            if not listings:
                result = {
                    "product_id": product_id,
                    "status": "SUCCESS",
                    "analyzed_count": 0,
                    "inserted_count": 0,
                    "message": "No competitor listings found for selected product.",
                    "results": [],
                }
                self.repository.finish_agent_run(agent_run, "SUCCESS", output_payload=self._serialize_result(result))
                self.repository.commit()
                return result

            market_prices = self.scoring_service.calculate_market_prices(listings)
            listing_ids = [item.id for item in listings]
            results = []
            inserted_count = 0

            self.repository.delete_existing_tiers_for_listings(listing_ids)

            for listing in listings:
                price_is_outlier = self.scoring_service.is_price_outlier(
                    price=self.scoring_service.safe_float(listing.price),
                    median_price=market_prices["median_price"],
                    mad_price=market_prices["mad_price"],
                    price_count=int(market_prices["price_count"]),
                )
                price_history_summary = self.repository.get_price_history_summary(
                    product_id=product_id,
                    marketplace=listing.marketplace,
                    seller_name=listing.seller_name,
                    lookback_hours=168,
                )

                strength_score, strength_reasons = self.scoring_service.calculate_competitor_strength_score(
                    listing=listing,
                    min_price=market_prices["min_price"],
                    avg_price=market_prices["avg_price"],
                )

                aggression_score, aggression_reasons = self.scoring_service.calculate_price_aggression_score(
                    listing=listing,
                    min_price=market_prices["min_price"],
                    avg_price=market_prices["avg_price"],
                    price_history_summary=price_history_summary,
                )

                buybox_score, buybox_reasons = self.scoring_service.calculate_buybox_threat_score(
                    listing=listing,
                    strength_score=strength_score,
                    price_aggression_score=aggression_score
                )

                tier, tier_reasons = self.scoring_service.assign_tier(
                    listing=listing,
                    strength_score=strength_score,
                    buybox_threat_score=buybox_score,
                    price_aggression_score=aggression_score,
                    price_is_outlier=price_is_outlier,
                )

                reason_codes = list(dict.fromkeys(strength_reasons + aggression_reasons + buybox_reasons + tier_reasons))

                self.repository.create_competitor_tier(
                    product_id=product_id,
                    listing=listing,
                    tier=tier,
                    competitor_strength_score=round(strength_score, 2),
                    buybox_threat_score=round(buybox_score, 2),
                    price_aggression_score=round(aggression_score, 2),
                    reason_codes=reason_codes,
                )

                inserted_count += 1

                results.append(
                    {
                        "competitor_listing_id": listing.id,
                        "competitor_seller_id": listing.competitor_seller_id,
                        "marketplace": listing.marketplace,
                        "seller_name": listing.seller_name,
                        "tier": tier,
                        "competitor_strength_score": round(strength_score, 2),
                        "buybox_threat_score": round(buybox_score, 2),
                        "price_aggression_score": round(aggression_score, 2),
                        "reason_codes": reason_codes,
                        "price": (
                            float(listing.price)
                            if listing.price is not None
                            else None
                        ),
                        "original_price": (
                            float(listing.original_price)
                            if listing.original_price is not None
                            else None
                        ),
                        "currency": listing.currency,
                        "rank": listing.rank,
                        "stock": listing.stock,
                        "is_in_stock": listing.is_in_stock,
                        "free_shipping": listing.free_shipping,
                        "fast_shipping": listing.fast_shipping,
                        "shipment_days": listing.shipment_days,
                        "scraped_at": listing.scraped_at,
                    }
                )

            result = {
                "product_id": product_id,
                "status": "SUCCESS",
                "analyzed_count": len(listings),
                "inserted_count": inserted_count,
                "message": "Competitor intelligence analysis completed successfully.",
                "results": results,
            }

            self.repository.finish_agent_run(agent_run, "SUCCESS", output_payload=self._serialize_result(result))
            self.repository.commit()
            return result

        except Exception as exc:
            self.repository.rollback()
            failed_result = {
                "product_id": product_id,
                "status": "FAILED",
                "analyzed_count": 0,
                "inserted_count": 0,
                "message": str(exc),
                "results": [],
            }
            return failed_result

    def _serialize_result(self, result: dict) -> dict:
        serialized = dict(result)
        serialized["product_id"] = str(serialized["product_id"])
        serialized["results"] = [
            {
                **item,
                "competitor_listing_id": str(item["competitor_listing_id"]),
                "competitor_seller_id": str(item["competitor_seller_id"]) if item.get("competitor_seller_id") else None,
                "scraped_at": (
                    item["scraped_at"].isoformat()
                    if item.get("scraped_at") is not None
                    else None
                ),
            }
            for item in serialized.get("results", [])
        ]
        return serialized
