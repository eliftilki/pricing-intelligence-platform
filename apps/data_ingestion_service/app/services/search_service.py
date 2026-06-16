import asyncio
import logging
from typing import Any, Dict, List

from app.collectors.trendyol_search_collector import TrendyolSearchCollector
from app.collectors.hepsiburada_search_collector import HepsiburadaSearchCollector
from app.collectors.amazon_search_collector import AmazonSearchCollector

logger = logging.getLogger(__name__)

_COLLECTORS = {
    "trendyol": TrendyolSearchCollector,
    "hepsiburada": HepsiburadaSearchCollector,
    "amazon": AmazonSearchCollector,
}


async def run_search(query: str, marketplaces: List[str], max_results: int) -> Dict[str, Any]:
    requested = [m.lower() for m in marketplaces]
    unknown = [m for m in requested if m not in _COLLECTORS]
    if unknown:
        raise ValueError(f"Bilinmeyen marketplace(ler): {unknown}. Geçerliler: {list(_COLLECTORS)}")

    async def _search_one(name: str) -> tuple[str, Any]:
        collector = _COLLECTORS[name]()
        try:
            result = await collector.search(query, max_results=max_results)
            return name, result
        except Exception as e:
            logger.error(f"{name} arama hatası: {e}")
            return name, {"source": name, "query": query, "total_found": 0, "results": [], "error": str(e)}

    tasks = [_search_one(m) for m in requested]
    pairs = await asyncio.gather(*tasks)

    return {
        "query": query,
        "marketplaces_searched": requested,
        "results": {name: data for name, data in pairs},
    }
