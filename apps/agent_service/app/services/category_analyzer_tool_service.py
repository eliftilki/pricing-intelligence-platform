import statistics


class CategoryAnalyzerToolService:
    """
    Tool 3 - Category Analyzer Tool. Pure: pytrends'i kendisi cagirmaz.
    MarketIntelligenceService, ayni kategorideki her peer urun icin
    GoogleTrendsToolService.get_interest(...) cagirip sonuclari (trend_score,
    interest_change_7d listesi) burada toplar. Boylece "urune ozel artis mi,
    kategori geneli artis mi" ayrimi yapilabilir.
    """

    def analyze(self, peer_trend_results: list[dict]) -> dict:
        valid_scores = [r["trend_score"] for r in peer_trend_results if r.get("trend_score") is not None]
        valid_changes = [
            r["interest_change_7d"] for r in peer_trend_results if r.get("interest_change_7d") is not None
        ]

        return {
            "category_trend_score": round(statistics.mean(valid_scores), 2) if valid_scores else None,
            "category_demand_change": round(statistics.mean(valid_changes), 4) if valid_changes else None,
        }
