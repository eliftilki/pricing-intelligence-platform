from datetime import date

from app.services.event_calendar_generator_service import EventCalendarGeneratorService

svc = EventCalendarGeneratorService(db=None)


def test_nth_sunday_of_month():
    # Mayis 2026: 1 Mayis Cuma -> ilk Pazar 3 Mayis, 2. Pazar 10 Mayis
    mothers_day = svc._nth_sunday_of_month(2026, 5, 2)
    assert mothers_day == date(2026, 5, 10)
    assert mothers_day.weekday() == 6  # Pazar


def test_islamic_holidays_fall_within_target_gregorian_year():
    for year in [2024, 2025, 2026, 2027, 2028, 2030]:
        events = svc._islamic_holidays(year)
        ramadan = next(e for e in events if e["event_type"] == "RAMADAN")
        eid = next(e for e in events if e["event_type"] == "EID_AL_ADHA")

        assert date(year, 1, 1) <= ramadan["start_date"] <= date(year, 12, 31), (
            f"{year}: Ramazan baslangici yil disina tasti: {ramadan['start_date']}"
        )
        assert date(year, 1, 1) <= eid["start_date"] <= date(year, 12, 31), (
            f"{year}: Kurban Bayrami baslangici yil disina tasti: {eid['start_date']}"
        )


def test_known_ramadan_2025_start_date_matches_real_calendar():
    # Regresyon testi: eski yaklasik formul (year-622)*1.03 bu tarihi 2024-03-11
    # olarak hesapliyordu (1 yil hatali). Gercek tarih 2025-03-01'dir.
    events = svc._islamic_holidays(2025)
    ramadan = next(e for e in events if e["event_type"] == "RAMADAN")

    assert ramadan["start_date"] == date(2025, 3, 1)


def test_hijri_years_overlapping_gregorian_year_returns_two_candidates():
    years = svc._hijri_years_overlapping_gregorian_year(2026)

    assert len(years) == 2
    assert years[0] < years[1]


def test_fixed_events_always_within_their_year():
    for year in [2025, 2026, 2027]:
        events = svc._fixed_events(year)
        for event in events:
            assert event["start_date"].year == year
            assert event["end_date"] >= event["start_date"]
