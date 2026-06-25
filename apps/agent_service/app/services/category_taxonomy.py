"""
Urunun serbest metin `category` alanini (orn. "Telefon", "Televizyon",
"Gaming Headset") event_calendar.affected_categories'te kullanilan sabit
ust kategorilere (orn. "Elektronik") cevirir.

Neden gerekli: Product.category serbest metin oldugundan, kullanicilar
ayni ust kategori icin farkli alt kategori adlari girebilir ("Telefon",
"Bilgisayar", "Kulaklik" hepsi Elektronik). Event eslesmesi tam string
karsilastirmasiyla yapildigindan, bu mapping olmadan event_agent bu
urunleri hicbir kampanyaya eslestiremez.

Ust kategoriler event_calendar_generator_service.py'deki
affected_categories listeleriyle birebir ayni olmalidir: Elektronik,
Moda, Ev, Takı, Güzellik, Kırtasiye, Spor, Oyuncak, Hediye, Gıda,
Kozmetik, Aletler.
"""

_SUBCATEGORIES_BY_PARENT: dict[str, list[str]] = {
    "Elektronik": [
        "telefon", "televizyon", "bilgisayar", "laptop", "tablet",
        "kulaklık", "gaming headset", "klavye", "mouse", "webcam",
        "kamera", "akıllı saat", "powerbank", "hoparlör",
        "oyun konsolu", "yazıcı", "monitör", "soğutucu",
    ],
    "Moda": [
        "kıyafet", "ayakkabı", "çanta", "gömlek", "pantolon", "elbise",
        "ceket", "mont", "tişört", "kazak", "etek", "mayo", "iç giyim",
        "aksesuar", "sırt çantası",
    ],
    "Ev": [
        "mobilya", "mutfak", "dekorasyon", "ev tekstili", "banyo",
        "aydınlatma", "halı", "yatak", "nevresim", "bahçe",
    ],
    "Takı": [
        "kolye", "yüzük", "küpe", "bileklik", "kol saati",
    ],
    "Güzellik": [
        "bakım", "parfüm", "cilt bakımı", "saç bakımı",
    ],
    "Kozmetik": [
        "makyaj", "ruj", "fondöten", "oje", "makyaj fırçası",
    ],
    "Kırtasiye": [
        "defter", "kalem", "okul çantası",
    ],
    "Spor": [
        "spor giyim", "fitness", "koşu", "bisiklet", "yoga", "outdoor", "kamp",
    ],
    "Oyuncak": [
        "oyuncak", "lego", "bebek oyuncak", "peluş",
    ],
    "Hediye": [
        "hediyelik eşya",
    ],
    "Gıda": [
        "atıştırmalık", "içecek", "kuruyemiş",
    ],
    "Aletler": [
        "el aletleri", "beyaz eşya", "ev aletleri", "elektrikli ev aletleri",
        "süpürge", "ütü", "bulaşık makinesi", "çamaşır makinesi",
    ],
}

SUBCATEGORY_TO_PARENT: dict[str, str] = {
    subcategory: parent
    for parent, subcategories in _SUBCATEGORIES_BY_PARENT.items()
    for subcategory in subcategories
}


def normalize_category(category: str | None) -> str | None:
    """
    Bilinen bir alt kategori ise ust kategorisini, bilinmiyorsa oldugu
    gibi (degismeden) dondurur - boylece event_calendar'da dogrudan
    girilmis ust kategoriler (orn. "Elektronik") etkilenmez.
    """
    if not category:
        return category

    return SUBCATEGORY_TO_PARENT.get(category.strip().lower(), category)
