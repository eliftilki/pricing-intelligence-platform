import logging
import os
from datetime import timedelta

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class GoogleTrendsToolService:
    """
    Tool 1 - Google Trends Tool (SerpApi ile). SerpApi resmi bir proxy/scraping
    servisi oldugu icin Google'in bot tespitini onlar yonetiyor - biz sadece
    API key ile istelik gonderiyoruz. Yine de network/rate-limit hatasina
    aciktir: bu metod hicbir zaman exception firlatmaz, hata durumunda noter
    (None) deger dondurerek cagiran tarafin pipeline'i dusurmeden devam
    etmesini saglar.
    """

    API_BASE = "https://serpapi.com/search"
    TIMEOUT = 10

    def __init__(self, country: str = "TR"):
        self._country = country
        self._api_key = os.getenv("SERPAPI_KEY")
        if not self._api_key:
            logger.warning("SERPAPI_KEY ortam degiskeni tanimlanimadi - SerpApi calistigini test etmek mumkun olmayacak")

    def get_interest(self, search_term: str) -> dict:
        try:
            if not self._api_key:
                logger.warning("SERPAPI_KEY yok, trend verisi alamiyor: search_term=%s", search_term)
                return self._empty()

            params = {
                "engine": "google_trends",
                "q": search_term,
                "data_type": "TIMESERIES",
                "timeframe": "3m",
                "geo": self._country,
                "hl": "tr",
                "api_key": self._api_key,
            }

            response = requests.get(self.API_BASE, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.warning("SerpApi hata dondu: search_term=%s error=%s", search_term, data["error"])
                return self._empty()

            if "interest_over_time" not in data or not data["interest_over_time"]:
                logger.warning("SerpApi'den veri gelmedi: search_term=%s", search_term)
                return self._empty()

            timeline_data = data["interest_over_time"].get("timeline_data", [])
            if not timeline_data:
                logger.warning("SerpApi timeline_data boş: search_term=%s", search_term)
                return self._empty()

            series = pd.Series(
                [int(point["values"][0]["extracted_value"]) for point in timeline_data],
                index=pd.to_datetime([int(point["timestamp"]) for point in timeline_data], unit="s"),
            )

            if series.empty:
                return self._empty()

            trend_score = float(series.iloc[-1])

            return {
                "trend_score": trend_score,
                "interest_change_7d": self._pct_change(series, 7),
                "interest_change_30d": self._pct_change(series, 30),
            }
        except requests.exceptions.Timeout:
            logger.warning("SerpApi timeout: search_term=%s", search_term)
            return self._empty()
        except requests.exceptions.RequestException as exc:
            logger.warning("SerpApi network hata: search_term=%s error=%s", search_term, exc)
            return self._empty()
        except Exception:
            logger.warning("SerpApi sorgusu basarisiz oldu: search_term=%s", search_term, exc_info=True)
            return self._empty()

    def _pct_change(self, series, days: int) -> float | None:
        """
        Satir sayisina gore degil tarihe gore geriye gider: "days gun
        onceye en yakin veri noktasi" ne ise onu kullanir.
        """
        if series.empty:
            return None

        last_date = series.index[-1]
        target_date = last_date - timedelta(days=days)

        past_points = series[series.index <= target_date]
        if past_points.empty:
            return None

        current = float(series.iloc[-1])
        previous = float(past_points.iloc[-1])

        if previous == 0:
            return None

        return round((current - previous) / previous, 4)

    def _empty(self) -> dict:
        return {"trend_score": None, "interest_change_7d": None, "interest_change_30d": None}
