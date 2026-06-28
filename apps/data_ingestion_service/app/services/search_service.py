import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.collectors.trendyol_search_collector import TrendyolSearchCollector
from app.collectors.hepsiburada_search_collector import HepsiburadaSearchCollector
from app.collectors.amazon_search_collector import AmazonSearchCollector
from app.services.variant_filter import build_query_suffix, filter_results

logger = logging.getLogger(__name__)

_COLLECTORS = {
    "trendyol": TrendyolSearchCollector,
    "hepsiburada": HepsiburadaSearchCollector,
    "amazon": AmazonSearchCollector,
}


async def run_search(
    query: str,
    marketplaces: List[str],
    max_results: int,
    connection_type: Optional[str] = None,
    ram_gb: Optional[int] = None,
    storage_gb: Optional[int] = None,
    sim_type: Optional[str] = None,
    keyboard_layout: Optional[str] = None,
) -> Dict[str, Any]:
    requested = [m.lower() for m in marketplaces]
    unknown = [m for m in requested if m not in _COLLECTORS]
    if unknown:
        raise ValueError(f"Bilinmeyen marketplace(ler): {unknown}. Geçerliler: {list(_COLLECTORS)}")

    has_filter = bool(connection_type or ram_gb or storage_gb or sim_type or keyboard_layout)
    suffix = build_query_suffix(connection_type, ram_gb, storage_gb, sim_type, keyboard_layout)
    search_query = f"{query} {suffix}".strip() if suffix else query
    # Filtreleme sonuc sayisini azaltacagi icin, filtre varsa scrape'i biraz
    # daha buyuk bir havuzdan yapip sonra max_results'a kirpiyoruz.
    fetch_count = min(max_results * 2, 50) if has_filter else max_results

    async def _search_one(name: str) -> tuple[str, Any]:
        collector = _COLLECTORS[name]()
        try:
            result = await collector.search(search_query, max_results=fetch_count)
            if has_filter:
                result["results"] = filter_results(
                    result["results"], connection_type, ram_gb, storage_gb, keyboard_layout
                )[:max_results]
                result["total_found"] = len(result["results"])
            result["query"] = query
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
