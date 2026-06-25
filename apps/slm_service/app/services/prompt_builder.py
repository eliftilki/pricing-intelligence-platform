from app.schemas.explanation_schema import ExplanationRequest


class PromptBuilder:
    @staticmethod
    def build(request: ExplanationRequest) -> list[dict[str, str]]:
        user_prompt = f"""
Aşağıdaki fiyat önerisini kullanıcıya profesyonel ama anlaşılır Türkçe ile açıkla.

Ürün: {request.product_name}
Marketplace: {request.marketplace}

Mevcut fiyat: {request.current_price} TL
Önerilen fiyat: {request.recommended_price} TL

Beklenen satış: {request.expected_sales}
Birim kâr: {request.unit_profit} TL
Beklenen toplam kâr: {request.expected_profit} TL
Komisyon oranı: {request.commission_rate}

Minimum rakip fiyatı: {request.competitor_min_price}
Ortalama rakip fiyatı: {request.competitor_avg_price}
Tier-1 minimum rakip fiyatı: {request.tier1_min_price}

Risk seviyesi: {request.risk_level}
Karar nedeni: {request.selected_reason}

Cevabı şu başlıklarla ver:

1. Önerilen fiyat
2. Neden bu fiyat seçildi?
3. Kâr ve rekabet yorumu
4. Dikkat edilmesi gereken risk

Kurallar:
- Kısa ve net yaz.
- Kesin olmayan şeyleri kesinmiş gibi söyleme.
- Fiyat kararını değiştirme.
- Sadece verilen verilere göre açıklama yap.
"""

        return [
            {
                "role": "system",
                "content": (
                    "Sen bir pazaryeri fiyatlandırma asistanısın. "
                    "Görevin fiyatı seçmek değil, verilen fiyat önerisini "
                    "kullanıcıya anlaşılır şekilde açıklamaktır."
                ),
            },
            {
                "role": "user",
                "content": user_prompt.strip(),
            },
        ]