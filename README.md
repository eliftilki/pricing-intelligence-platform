# feraSet

feraSet, e-ticaret saticilari icin pazaryeri verilerini toplayan, rakipleri analiz eden, aday fiyatlar ureten ve bu adaylari komisyon/maliyet/marj kurallarina gore optimize eden fiyatlandirma platformudur.

Platform tek bir "sihirli fiyat" uretmek yerine fiyat kararini izlenebilir asamalara ayirir:

1. Pazaryerlerinden rakip ve fiyat verileri toplanir.
2. Rakipler guc, fiyat agresifligi ve buybox tehdidine gore analiz edilir.
3. Pazar yapisina gore birden fazla aday fiyat uretilir.
4. Marketplace ve sirket ozel komisyonlari ayri Commission Service katmanindan cozulur.
5. Aday fiyatlar beklenen satis ve kar kurallariyla optimize edilir.
6. SLM servisinden fiyat kararini kullaniciya aciklayan metin alinabilir.

## Servisler

| Servis | Sorumluluk |
| --- | --- |
| `apps/web` | Next.js tabanli yonetim arayuzu. Sirket urunleri, analiz baslatma ve sonuc goruntuleme ekranlarini sunar. |
| `apps/api_service` | Kimlik, sirket, urun, analiz, competitor, recommendation API'lerini sunar; diger servislerle HTTP uzerinden konusur. |
| `apps/agent_service` | Pricing pipeline orchestration, competitor intelligence, candidate price generation, commission lookup, optimization ve SLM explanation client katmanlarini calistirir. |
| `apps/data_ingestion_service` | Trendyol, Hepsiburada ve Amazon icin arama/scrape akisini calistirir; rakip ilanlarini normalize eder. |
| `apps/slm_service` | Hugging Face tabanli lokal SLM ile fiyat onerisi aciklamasi uretir. |
| `apps/ml_service` | Su anda placeholder klasordur; aktif FastAPI servisi veya endpoint icermiyor. |

## Ana Akis

```text
Pricing Pipeline Graph
    |
    +-- Data Ingestion Node (opsiyonel HTTP cagrisi)
    |
    +-- Competitor Intelligence Node + Event Agent (paralel)
    |
    +-- Feature Engineering Node
    |
    +-- Candidate Price Generator Node
    |
    +-- Optimization Node
    |       |
    |       +-- Commission Service
    |               |
    |               +-- Commission Repository
    |                       |
    |                       +-- Database
    |
    +-- SLM Explanation Node
```

`/pricing-intelligence/run` ana agent pipeline girisidir. Graph her zaman `data_ingestion` node ile baslar. Ingestion service son 12 saat icinde basarili veri varsa DB/cache sonucunu kullanir; eski veya eksik marketplace verisini otomatik scrape eder. `run_candidate_prices` ve `run_optimization` bayraklariyla sonraki adimlar acilip kapatilabilir.

`/competitor-intelligence/run` endpoint'i korunur, ancak graph orkestrasyonu calistirmaz; sadece rakip analizini dogrudan calistirir.

## Agent Service Mimarisi

```text
apps/agent_service/app/
|
+-- core/
|   +-- config.py
|   +-- database.py
|
+-- graph/
|   +-- state.py
|   +-- pricing_pipeline_graph.py
|
+-- nodes/
|   +-- data_ingestion_node.py
|   +-- competitor_intelligence_node.py
|   +-- event_agent_node.py
|   +-- feature_engineering_node.py
|   +-- candidate_price_generator_node.py
|   +-- optimization_node.py
|   +-- slm_explanation_node.py
|   +-- pipeline_finalizer_node.py
|
+-- services/
|   +-- data_ingestion_client.py
|   +-- competitor_intelligence_service.py
|   +-- competitor_scoring_service.py
|   +-- candidate_price_generator_service.py
|   +-- candidate_strategy_selector.py
|   +-- candidate_strategies/
|   +-- commission_service.py
|   +-- optimization_service.py
|   +-- slm_explanation_client.py
|
+-- repositories/
|   +-- competitor_repository.py
|   +-- candidate_price_repository.py
|   +-- commission_repository.py
|   +-- optimization_repository.py
|
+-- routers/
|   +-- competitor_intelligence.py
|   +-- candidate_price.py
|   +-- optimization.py
|   +-- pricing_intelligence.py
|
+-- schemas/
|   +-- data_ingestion_schema.py
|   +-- competitor_schema.py
|   +-- candidate_price_schema.py
|   +-- optimization_schema.py
|   +-- pricing_intelligence_schema.py
|   +-- slm_explanation_schema.py
|
+-- models/
|   +-- base.py
|   +-- product.py
|   +-- competitor.py
|   +-- candidate_price.py
|   +-- commission.py
|   +-- optimization.py
|   +-- agent_run.py
|
+-- main.py
```

### Pricing Pipeline Graph

Graph dosyasi:

```text
apps/agent_service/app/graph/pricing_pipeline_graph.py
```

Mevcut graph sirasi:

```text
START
  -> data_ingestion              12 saatlik cache kontrolu + gerekirse scrape
  -> competitor_intelligence + event_agent (paralel)
  -> feature_engineering
  -> candidate_price_generator   run_candidate_prices=true ise
  -> optimization                run_optimization=true ise
  -> slm_explanation             optimization calisirsa
  -> END
```

`run_optimization=false` ise pipeline rakip analizi veya aday fiyat adimindan sonra biter; bu durumda SLM explanation node calismaz.

Data ingestion `COMPLETED` durumunda normal devam eder. `PARTIAL` durumunda sonucu `warnings` alanina ekleyerek devam eder; `FAILED` veya servis erisim hatasinda competitor intelligence calismadan pipeline sonlanir. Ingestion service'in 12 saatlik cache politikasi korunur.

Pipeline'in tum cikis yollari `pipeline_finalizer` node'unda birlesir. Genel `status` ve `message` son calisan node'a gore degil tum istenen asamalara gore uretilir: kritik hata `FAILED`, SLM/persistence/partial ingestion gibi ikincil sorunlar `PARTIAL_SUCCESS`, eksiksiz akis `SUCCESS` doner. `pipeline_summary` tamamlanan ve basarisiz olan asamalari listeler.

Not: `slm_explanation_node` su anda `state["recommendation"]` bekler. Recommendation node henuz eklenmedigi icin SLM node calissa bile recommendation yoksa `RECOMMENDATION_NOT_FOUND_FOR_SLM` hatasini `state["errors"]` icine yazar.

## Modul Sorumluluklari

### Competitor Intelligence

- Guncel rakip ilanlarini ve fiyat gecmisini okur.
- Rakip gucu, fiyat agresifligi ve buybox tehdit skorlarini hesaplar.
- Rakipleri `TIER_1`, `TIER_2`, `NOISE` gibi siniflara ayirir.
- Sonuclari `competitor_tiers` ve `agent_runs` ile izlenebilir hale getirir.

### Candidate Price Generator

- Rakip fiyat araligi ve mevcut fiyattan aday fiyatlar uretir.
- `AUTO` modunda pazar yapisina gore strateji secer.
- Nihai fiyat secmez; optimization asamasina verilecek fiyat adaylarini uretir.

Desteklenen stratejiler:

| Strateji | Amac |
| --- | --- |
| `BASIC_COMPETITOR_RANGE` | Temel rakip fiyat araligindan aday uretir. |
| `TIER_BASED_COMPETITOR_WINDOW` | Oncelikli rakip tier'larini dikkate alir. |
| `ADAPTIVE_DENSE_MARKET_WINDOW` | Yogun fiyat bolgelerinde daha ince adimlarla aday uretir. |
| `AUTO` | Uygun stratejiyi otomatik secer. |

### Commission Service

Optimization agent komisyonu kendisi hesaplamaz. Komisyon orani ayri `CommissionService` uzerinden cozulur.

Oncelik sirasi:

1. `company_marketplace_commission_overrides`
2. `marketplace_commission_rules`
3. Hicbiri yoksa `COMMISSION_RATE_NOT_FOUND`

Komisyon eslesmesi `category` text degeriyle degil, `category_id` ile yapilir. Bu nedenle `products.category_id`, `marketplace_commission_rules.category_id` ve override tablosundaki `category_id` alanlari dolu olmalidir.

### Optimization

- Demand prediction ciktisini ve marketplace cost context'ini alir.
- Komisyon, kargo, paketleme, maliyet ve minimum marj kurallarini uygular.
- Her marketplace icin en yuksek beklenen kar adayini secer.
- Sonuclari `pricing_optimization_results` tablosuna kaydedebilir.

### SLM Explanation

`slm_service`, fiyat onerisi icin kullaniciya okunabilir Turkce aciklama uretir.

Agent service, SLM service'e su endpoint uzerinden gider:

```text
POST http://localhost:8003/explanations/generate
```

SLM servisinin model yuklemesi runtime'da Hugging Face model erisimi, disk, RAM/GPU durumuna baglidir.

## Onemli Endpointler

### API Service

```text
POST /analysis/run
POST /analysis/search-and-run
GET  /products
POST /products
GET  /recommendations/seller-products/{seller_product_id}
```

### Agent Service

```text
POST /competitor-intelligence/run
POST /pricing-intelligence/run
POST /candidate-prices/generate
POST /optimization/run
POST /optimization/run-from-db/{seller_product_id}
```

Ornek pricing pipeline istegi:

```json
{
  "product_id": "PRODUCT_UUID",
  "seller_product_id": "SELLER_PRODUCT_UUID",
  "lookback_hours": 12,
  "ingestion_marketplaces": ["TRENDYOL", "HEPSIBURADA", "AMAZON"],
  "run_candidate_prices": true,
  "run_optimization": true,
  "persist_optimization": true,
  "demand_predictions": [
    { "price": 1000, "expected_sales": 12 },
    { "price": 1100, "expected_sales": 10 }
  ]
}
```

### Data Ingestion Service

```text
POST /ingestion/search-and-run
POST /ingestion/run
POST /ingestion/run-with-urls
POST /search
```

Scrape cache su anda 12 saattir. Tum marketplace'ler cache'ten gelirse yeni scraping calismaz. Kismi cache durumunda sadece eksik marketplace'ler scrape edilir.

Pipeline mevcut seller product URL'leriyle `/ingestion/run` endpoint'ini kullanir. URL bulunmasi da isteniyorsa pricing request'e `ingestion_query` ve `ingestion_company_id` birlikte verilerek `/ingestion/search-and-run` akisi secilir.

### SLM Service

```text
GET  /health
POST /explanations/generate
```

## Veritabani Beklentileri

Kodun guncel hali su tablolarin varligini bekler:

- `product_categories`
- `products.category_id`
- `marketplace_commission_rules.category_id`
- `company_marketplace_commission_overrides`
- `pricing_optimization_results`
- `competitor_tiers`
- `agent_runs`

Komisyon lookup icin kritik alanlar:

```text
products.category_id
marketplace_commission_rules.marketplace
marketplace_commission_rules.category_id
company_marketplace_commission_overrides.company_id
company_marketplace_commission_overrides.marketplace
company_marketplace_commission_overrides.category_id
```

Default komisyon ornegi:

```sql
INSERT INTO public.marketplace_commission_rules
    (marketplace, category_id, category, commission_rate, is_active)
SELECT 'TRENDYOL', id, code, 0.18, true
FROM public.product_categories
WHERE code = 'HEADSET';
```

Sirket ozel komisyon ornegi:

```sql
INSERT INTO public.company_marketplace_commission_overrides
    (company_id, marketplace, category_id, commission_rate, is_active)
SELECT 'COMPANY_UUID_HERE', 'TRENDYOL', id, 0.14, true
FROM public.product_categories
WHERE code = 'HEADSET';
```

## Ortam Degiskenleri

Kok dizindeki `.env.example` dosyasindan `.env` olusturun:

```powershell
Copy-Item .env.example .env
```

Kok `.env.example` icindeki temel degiskenler:

```text
DATABASE_URL
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
AGENT_SERVICE_URL
DATA_INGESTION_SERVICE_URL
CORS_ORIGINS
```

Agent service icin ek SLM ayarlari opsiyoneldir; verilmezse kod varsayilan olarak `http://localhost:8003` ve `60` saniye kullanir:

```text
SLM_SERVICE_URL=http://localhost:8003
SLM_EXPLANATION_TIMEOUT_SECONDS=60
DATA_INGESTION_SERVICE_URL=http://localhost:8004
DATA_INGESTION_REQUEST_TIMEOUT_SECONDS=180
DATA_INGESTION_MAX_RETRIES=2
```

SLM service icin:

```text
HF_TOKEN
HF_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct
MAX_NEW_TOKENS=350
TEMPERATURE=0.3
TOP_P=0.9
```

## Yerel Kurulum

Python servisleri icin ayri sanal ortam kullanilmasi onerilir:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r apps/api_service/requirements.txt
pip install -r apps/agent_service/requirements.txt
pip install -r apps/data_ingestion_service/requirements.txt
pip install -r apps/slm_service/requirements.txt
```

Web uygulamasi:

```powershell
cd apps/web
npm install
```

Playwright tabanli collector kullanimi icin:

```powershell
playwright install
```

## Servisleri Calistirma

Proje kok dizininden ayri terminallerde:

```powershell
uvicorn app.main:app --app-dir apps/api_service --reload --port 8000
uvicorn app.main:app --app-dir apps/agent_service --reload --port 8001
uvicorn app.main:app --app-dir apps/slm_service --reload --port 8003
uvicorn app.main:app --app-dir apps/data_ingestion_service --reload --port 8004
```

Web:

```powershell
cd apps/web
npm run dev
```

Saglik kontrolleri:

```text
GET http://localhost:8000/health
GET http://localhost:8001/health
GET http://localhost:8003/health
GET http://localhost:8004/health
```

FastAPI dokumantasyonu:

```text
http://localhost:8000/docs
http://localhost:8001/docs
http://localhost:8003/docs
http://localhost:8004/docs
```

## Test ve Dogrulama

Agent service testleri:

```powershell
$env:PYTHONPATH='apps/agent_service'
python -m unittest discover apps/agent_service/tests
```

Web production build:

```powershell
cd apps/web
npm run build
```

## Gelistirme Ilkeleri

- Orchestration sadece `pricing_pipeline_graph.py` icinde tutulur.
- Node'lar yalnizca graph state ile servis katmani arasinda adaptor gorevi gorur.
- Business logic servislerde, veritabani erisimi repository katmaninda kalir.
- Candidate price generator nihai fiyat secmez; sadece aday uretir.
- Optimization komisyonu hesaplamaz; komisyonu `CommissionService` ister.
- Finansal hesaplamalarda `Decimal` tercih edilir.
- Category eslesmeleri text ile degil `category_id` ile yapilir.
- SLM servis fiyat secmez; yalnizca verilen oneriyi aciklar.
