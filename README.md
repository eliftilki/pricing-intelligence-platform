# feraSet

feraSet; e-ticaret satıcıları için pazaryeri verilerini toplayan, rakipleri analiz eden ve açıklanabilir fiyat adayları üreten yapay zekâ destekli bir fiyatlandırma platformudur.

## Projenin amacı

Platformun temel amacı, tek bir “doğru fiyat” vermek yerine karar sürecinin her aşamasını ayrı ve izlenebilir bileşenlere ayırmaktır:

1. Pazaryerlerinden ürün ve rakip verileri toplanır.
2. Rakipler güç, fiyat agresifliği ve buybox tehdidine göre analiz edilir.
3. Fiyatlandırmada kullanılacak özellikler hazırlanır.
4. Pazar yapısına uygun strateji seçilerek birden fazla aday fiyat üretilir.
5. İlerleyen aşamalarda adaylar tahmin, optimizasyon ve risk kontrollerinden geçirilerek nihai öneriye dönüştürülür.

## Servisler

| Servis | Sorumluluk |
| --- | --- |
| `api_service` | Şirket, ürün, kimlik doğrulama, analiz ve öneri API'lerini sunar; diğer servislerle iletişimi yönetir. |
| `agent_service` | LangGraph tabanlı rakip analizi, feature engineering ve aday fiyat üretim akışlarını çalıştırır. |
| `data_ingestion_service` | Pazaryerlerinden rakip ve fiyat verilerini toplar ve normalize eder. |

Planlanan üst seviye akış:

```text
Veri Toplama
    ↓
Competitor Intelligence
    ↓
Feature Engineering
    ↓
Candidate Price Generator
    ↓
ML Prediction → Optimization → Risk Control
    ↓
Recommendation → SLM Explanation
```

## Agent Service mimarisi

```text
apps/agent_service/app/
│
├── core/
│   ├── config.py
│   └── database.py
│
├── graph/
│   ├── state.py
│   └── competitor_graph.py
│
├── models/
│   ├── base.py
│   ├── company.py
│   ├── product.py
│   ├── scrape.py
│   ├── competitor.py
│   ├── agent_run.py
│   ├── pricing_feature.py
│   └── candidate_price.py
│
├── nodes/
│   ├── competitor_intelligence_node.py
│   ├── feature_engineering_node.py
│   └── candidate_price_generator_node.py
│
├── repositories/
│   ├── competitor_intelligence_repository.py
│   ├── pricing_feature_repository.py
│   └── candidate_price_repository.py
│
├── routers/
│   ├── competitor_intelligence.py
│   └── candidate_price.py
│
├── schemas/
│   ├── competitor_intelligence_schema.py
│   ├── pricing_feature_schema.py
│   └── candidate_price_schema.py
│
├── services/
│   ├── competitor_scoring_service.py
│   ├── competitor_tiering_service.py
│   ├── pricing_feature_engineering_service.py
│   ├── candidate_price_generator_service.py
│   ├── candidate_strategy_selector.py
│   └── candidate_strategies/
│       ├── __init__.py
│       ├── base_candidate_strategy.py
│       ├── basic_range_strategy.py
│       ├── tier_based_strategy.py
│       └── adaptive_dense_strategy.py
│
└── main.py
```

> Bu ağaç, Agent Service için hedeflenen güncel modül sınırlarını gösterir. Bazı bileşenler geliştirme aşamasında olabilir.

### Modül sorumlulukları

#### Competitor Intelligence

- Güncel rakip ilanlarını ve fiyat geçmişini okur.
- Rakip gücü, fiyat agresifliği ve buybox tehdit skorlarını hesaplar.
- Rakipleri `TIER_1`, `TIER_2` gibi önem seviyelerine ayırır.
- Analiz sonucunu ve çalışma durumunu kalıcı olarak kaydeder.

#### Feature Engineering

- Competitor Intelligence çıktısını fiyatlandırmada kullanılabilecek özelliklere dönüştürür.
- Mevcut fiyat, rakip fiyat aralığı, pazar yoğunluğu ve ilgili rakipleri tek bir feature çıktısında birleştirir.
- Candidate Price Generator'ın ihtiyaç duyduğu veri sözleşmesini sağlar.

#### Candidate Price Generator

- Feature Engineering çıktısını tüketir.
- `AUTO` modunda pazar yapısına göre uygun stratejiyi seçer.
- Tek bir nihai fiyat yerine, sonraki optimizasyon aşamalarında değerlendirilecek aday fiyatlar üretir.
- Seçilen stratejiyi, uygulanan kısıtları ve üretim gerekçesini sonuçla birlikte döndürür.

Candidate üretimi mümkün olduğunda `seller_product_id` üzerinden yürütülür. Böylece aynı ürünün farklı pazaryerlerindeki mevcut fiyat, maliyet, komisyon ve marj koşulları birbirinden ayrılır.

### Candidate fiyat stratejileri

| Strateji | Kullanım amacı |
| --- | --- |
| `BASIC_COMPETITOR_RANGE` | Yeterli tier veya yoğunluk bilgisi olmadığında temel rakip fiyat aralığından aday üretir. |
| `TIER_BASED_COMPETITOR_WINDOW` | Öncelikli rakip tier'larını dikkate alarak daha hedefli bir fiyat penceresi oluşturur. |
| `ADAPTIVE_DENSE_MARKET_WINDOW` | Rakip fiyatlarının yoğunlaştığı bölgelerde daha küçük adımlarla aday üretir. |
| `AUTO` | Feature verisini inceleyerek yukarıdaki stratejilerden uygun olanı seçer. |

## Katmanların görevleri

- `routers`: HTTP isteklerini ve yanıt modellerini yönetir.
- `schemas`: Servisler arası veri sözleşmelerini Pydantic modelleriyle tanımlar.
- `graph`: Node'ların çalışma sırasını ve ortak state'i yönetir.
- `nodes`: Graph state ile servis katmanı arasındaki adaptasyonu yapar.
- `services`: İş kurallarını ve fiyat üretim algoritmalarını içerir.
- `repositories`: Veritabanı okuma ve yazma işlemlerini kapsüller.
- `models`: SQLAlchemy veritabanı modellerini tanımlar.

## Yerel kurulum

### Gereksinimler

- Python 3.11 veya üzeri
- PostgreSQL
- Playwright tarayıcıları (`data_ingestion_service` için)
- Supabase projesi veya geliştirme ortamına uygun Supabase bilgileri

### Ortam değişkenleri

Kök dizindeki örnek dosyayı kopyalayın:

```powershell
Copy-Item .env.example .env
```

Ardından `.env` içindeki veritabanı ve Supabase bilgilerini kendi ortamınıza göre düzenleyin. Temel değişkenler:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `AGENT_SERVICE_URL`
- `DATA_INGESTION_SERVICE_URL`
- `CORS_ORIGINS`

### Bağımlılıkların kurulması

Her servis için ayrı bir sanal ortam kullanılması önerilir:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r apps/api_service/requirements.txt
pip install -r apps/agent_service/requirements.txt
pip install -r apps/data_ingestion_service/requirements.txt
playwright install
```

### Servislerin çalıştırılması

Komutları proje kök dizininden, ayrı terminallerde çalıştırın:

```powershell
uvicorn app.main:app --app-dir apps/api_service --reload --port 8000
uvicorn app.main:app --app-dir apps/agent_service --reload --port 8001
uvicorn app.main:app --app-dir apps/data_ingestion_service --reload --port 8004
```

Servislerin sağlık kontrolü:

```text
GET http://localhost:8000/health
GET http://localhost:8001/health
GET http://localhost:8004/health
```

FastAPI dokümantasyonları `/docs` adresinden görüntülenebilir:

```text
http://localhost:8000/docs
http://localhost:8001/docs
http://localhost:8004/docs
```

## Geliştirme ilkeleri

- Her agent yalnızca kendi sorumluluğundaki çıktıyı üretir.
- Feature Engineering hesaplamaları Candidate Price Generator içinde tekrarlanmaz.
- Candidate Price Generator nihai fiyat seçmez; açıklanabilir fiyat seçenekleri üretir.
- Stratejiler veritabanına doğrudan erişmez; kendilerine verilen context üzerinden çalışır.
- Fiyat ve finansal hesaplamalarda kayan nokta hatalarını önlemek için `Decimal` kullanılması tercih edilir.
- Agent çalışmaları `agent_runs` üzerinden takip edilebilir olmalıdır.
- Üretilen adaylar, kullanılan feature kaydı ve stratejiyle ilişkilendirilerek geriye dönük izlenebilirlik korunmalıdır.

## Ekip sorumlulukları

| Alan | Sorumluluk |
| --- | --- |
| Competitor Intelligence | Rakip verilerinin skorlanması ve tier'lara ayrılması |
| Feature Engineering | Rakip analizi çıktılarından fiyatlandırma feature'larının hazırlanması |
| Candidate Price Generator | Uygun stratejinin seçilmesi ve aday fiyatların üretilmesi |
| Optimization / Recommendation | Adaylar arasından hedeflere ve risk kurallarına uygun nihai fiyatın seçilmesi |
