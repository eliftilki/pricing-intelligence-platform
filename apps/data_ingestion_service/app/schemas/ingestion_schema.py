from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# event_calendar seed data (agent_service) ile birebir ayni 12 kategori.
# Serbest metin kategori girisi (eski "Mouse", "headset", "Kulaklık" gibi
# tutarsizliklara yol acmisti) event matching'i kirdigi icin kapatildi.
ProductCategory = Literal[
    "Elektronik", "Moda", "Ev", "Gıda", "Kırtasiye", "Spor",
    "Takı", "Güzellik", "Hediye", "Aletler", "Oyuncak", "Kozmetik",
]


# ---------- Search ----------

class SearchRequest(BaseModel):
    query: str
    marketplaces: List[str] = Field(default_factory=lambda: ["trendyol", "hepsiburada", "amazon"])
    max_results: int = Field(default=10, ge=1, le=50)
    # Kategoriye gore fiyati buyuk olcude degistiren varyant secimleri.
    # Kulaklik: connection_type. Telefon: ram_gb / storage_gb / sim_type.
    connection_type: Optional[Literal["kablolu", "kablosuz"]] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    sim_type: Optional[Literal["tek_hat", "cift_hat"]] = None


class SearchResultItem(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    url: str
    asin: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None


class MarketplaceSearchResult(BaseModel):
    source: str
    query: str
    total_found: int
    results: List[SearchResultItem]


class SearchResponse(BaseModel):
    query: str
    marketplaces_searched: List[str]
    results: dict[str, MarketplaceSearchResult]


# ---------- Ingestion ----------

class IngestionRunRequest(BaseModel):
    product_id: UUID
    marketplaces: List[str] = ["TRENDYOL", "HEPSIBURADA", "AMAZON"]


class ProductCreateRequest(BaseModel):
    company_id: UUID
    name: str
    brand: Optional[str] = None
    category: Optional[ProductCategory] = None
    marketplace_urls: dict[str, str]


class ProductCreateResponse(BaseModel):
    product_id: UUID
    seller_product_ids: dict[str, UUID]


class IngestionRunResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
    scrape_counts: dict[str, int] = {}


class IngestionRunWithUrlsRequest(BaseModel):
    product_id: UUID
    company_id: UUID
    urls: dict[str, str]  # {"TRENDYOL": "https://...", "HEPSIBURADA": "https://...", "AMAZON": "https://..."}


class SearchAndRunRequest(BaseModel):
    product_id: UUID
    company_id: UUID
    query: str
    marketplaces: List[str] = Field(default_factory=lambda: ["trendyol", "hepsiburada", "amazon"])
