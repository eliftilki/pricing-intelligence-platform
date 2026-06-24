from datetime import date, timedelta

from hijri_converter import Hijri, Gregorian
from sqlalchemy.orm import Session

from app.models.market_event import EventCalendar


class EventCalendarGeneratorService:
    """
    Türkiye'nin önemli günlerini otomatik olarak generate edip event_calendar
    tablosuna yazan service. Sabit günler (yılbaşı), dini günler (Ramazan/Bayram),
    ve formüllü günler (Anneler Günü = Mayıs 2. Pazar) otomatik hesaplanır.
    Her yıl için bir kez çalıştırılması yeterli.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_for_year(self, year: int) -> dict:
        """
        Verilen yıl için tüm önemli günleri generate edip DB'ye yazar. Ayni
        event_type + yil icin zaten bir satir varsa, atlanmaz - yeniden
        hesaplanan alanlarla (tarih, kategori, etki skoru) GUNCELLENIR. Bu
        sayede formul/seed-data degisikliklerinde (orn. Hijri tarih hesabi
        duzeltmesi) generate_for_year tekrar calistirildiginda eski satirlar
        elle SQL ile duzeltilmek zorunda kalinmaz.
        Doner: {"inserted": int, "updated": int}
        """
        events = []

        # Sabit günler (her yıl aynı tarih)
        events.extend(self._fixed_events(year))

        # Dini günler (Hijri takvime göre hesaplanan)
        events.extend(self._islamic_holidays(year))

        # Formüllü günler (2. Pazar vb.)
        events.extend(self._calculated_events(year))

        inserted = 0
        updated = 0
        for event_data in events:
            existing = self.db.query(EventCalendar).filter(
                EventCalendar.event_type == event_data["event_type"],
                EventCalendar.start_date.between(date(year, 1, 1), date(year, 12, 31)),
            ).first()

            if existing:
                for field, value in event_data.items():
                    setattr(existing, field, value)
                updated += 1
            else:
                self.db.add(EventCalendar(**event_data))
                inserted += 1

        self.db.commit()
        return {"inserted": inserted, "updated": updated}

    def _fixed_events(self, year: int) -> list[dict]:
        """Sabit günler (her yıl aynı tarih)."""
        return [
            {
                "event_type": "NEW_YEAR",
                "event_name": "Yılbaşı",
                "start_date": date(year, 1, 1),
                "end_date": date(year, 1, 10),
                "affected_categories": ["Elektronik", "Moda", "Ev"],
                "base_impact_score": 0.35,
            },
            {
                "event_type": "VALENTINES_DAY",
                "event_name": "Sevgililer Günü",
                "start_date": date(year, 2, 10),
                "end_date": date(year, 2, 15),
                "affected_categories": ["Moda", "Takı", "Elektronik", "Güzellik"],
                "base_impact_score": 0.40,
            },
            {
                "event_type": "BACK_TO_SCHOOL",
                "event_name": "Okula Dönüş",
                "start_date": date(year, 8, 15),
                "end_date": date(year, 9, 10),
                "affected_categories": ["Elektronik", "Moda", "Kırtasiye", "Spor"],
                "base_impact_score": 0.50,
            },
            {
                "event_type": "SINGLES_DAY",
                "event_name": "11.11 Festivali",
                "start_date": date(year, 11, 8),
                "end_date": date(year, 11, 15),
                "affected_categories": ["Elektronik", "Moda", "Ev", "Spor", "Güzellik"],
                "base_impact_score": 0.75,
            },
            {
                "event_type": "BLACK_FRIDAY",
                "event_name": "Black Friday",
                "start_date": date(year, 11, 20),
                "end_date": date(year, 11, 30),
                "affected_categories": ["Elektronik", "Moda", "Ev", "Spor", "Oyuncak"],
                "base_impact_score": 0.95,
            },
            {
                "event_type": "YEAR_END",
                "event_name": "Yılsonu Alışverişi",
                "start_date": date(year, 12, 15),
                "end_date": date(year, 12, 31),
                "affected_categories": ["Elektronik", "Moda", "Ev", "Oyuncak", "Hediye"],
                "base_impact_score": 0.60,
            },
        ]

    def _islamic_holidays(self, year: int) -> list[dict]:
        """
        Dini günler (Hijri takvime göre hesaplanan). Ramazan ve Kurban Bayramı.
        Hijri yıl, dogrusal bir formulle TAHMIN EDILMEZ - hedef Gregorian yilin
        baslangic/bitis tarihleri gercekten Hijri'ye cevrilip (hijri_converter),
        o yila denk gelen gercek Hijri yil(lar) bulunur. Boylece ay dongusundeki
        kayma (yaklasik formulun +-1 yil hata payi) ortadan kalkar.
        """
        events = []
        candidate_hijri_years = self._hijri_years_overlapping_gregorian_year(year)

        ramadan_start = self._pick_date_in_year(
            year, [Hijri(hy, 9, 1).to_gregorian() for hy in candidate_hijri_years]
        )
        ramadan_end = ramadan_start + timedelta(days=30)

        events.append(
            {
                "event_type": "RAMADAN",
                "event_name": "Ramazan",
                "start_date": ramadan_start,
                "end_date": ramadan_end,
                "affected_categories": ["Elektronik", "Moda", "Ev", "Gıda"],
                "base_impact_score": 0.45,
            }
        )

        eid_start = self._pick_date_in_year(
            year, [Hijri(hy, 12, 8).to_gregorian() for hy in candidate_hijri_years]
        )
        eid_end = eid_start + timedelta(days=5)

        events.append(
            {
                "event_type": "EID_AL_ADHA",
                "event_name": "Kurban Bayramı",
                "start_date": eid_start,
                "end_date": eid_end,
                "affected_categories": ["Elektronik", "Moda", "Ev", "Hediye"],
                "base_impact_score": 0.50,
            }
        )

        return events

    @staticmethod
    def _hijri_years_overlapping_gregorian_year(year: int) -> list[int]:
        """Verilen Gregorian yilin Ocak 1'i ve Aralik 31'i hangi Hijri yil(lar)a
        denk geliyorsa onlari dondurur (Hijri yil ~354 gun oldugundan bir
        Gregorian yil ic ice iki Hijri yila denk gelebilir)."""
        start_hijri = Gregorian(year, 1, 1).to_hijri()
        end_hijri = Gregorian(year, 12, 31).to_hijri()
        return sorted({start_hijri.year, end_hijri.year})

    @staticmethod
    def _pick_date_in_year(year: int, candidates) -> date:
        """Aday Gregorian tarihler arasindan, verilen yilin icine denk geleni
        secer. Hicbiri tam icine denk gelmiyorsa (nadir sinir durumu) yila en
        yakin olani secer."""
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        converted = [date(c.year, c.month, c.day) for c in candidates]
        in_year = [d for d in converted if year_start <= d <= year_end]
        if in_year:
            return in_year[0]

        return min(converted, key=lambda d: min(abs((d - year_start).days), abs((d - year_end).days)))

    def _calculated_events(self, year: int) -> list[dict]:
        """Formüllü günler (2. Pazar, vs.)."""
        events = []

        # Anneler Günü: Mayıs 2. Pazar
        mothers_day = self._nth_sunday_of_month(year, 5, 2)

        events.append(
            {
                "event_type": "MOTHERS_DAY",
                "event_name": "Anneler Günü",
                "start_date": mothers_day,
                "end_date": mothers_day + timedelta(days=7),
                "affected_categories": ["Moda", "Takı", "Elektronik", "Güzellik", "Kozmetik"],
                "base_impact_score": 0.45,
            }
        )

        # Babalar Günü: Haziran 3. Pazar
        fathers_day = self._nth_sunday_of_month(year, 6, 3)

        events.append(
            {
                "event_type": "FATHERS_DAY",
                "event_name": "Babalar Günü",
                "start_date": fathers_day,
                "end_date": fathers_day + timedelta(days=7),
                "affected_categories": ["Moda", "Elektronik", "Spor", "Aletler"],
                "base_impact_score": 0.35,
            }
        )

        return events

    @staticmethod
    def _nth_sunday_of_month(year: int, month: int, n: int) -> date:
        """Belirli bir ayın n. Pazarını bulur."""
        first_day = date(year, month, 1)
        # Pazara kaç gün kaldığını hesapla (Pazar = 6)
        days_until_sunday = (6 - first_day.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 0
        first_sunday = first_day + timedelta(days=days_until_sunday)
        return first_sunday + timedelta(weeks=n - 1)
