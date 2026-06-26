from app.services.category_taxonomy import SUBCATEGORY_TO_PARENT, normalize_category


def test_known_subcategories_map_to_parent():
    assert normalize_category("Telefon") == "Elektronik"
    assert normalize_category("gaming headset") == "Elektronik"
    assert normalize_category("Kozmetik") == "Kozmetik"


def test_each_parent_category_has_at_least_one_mapped_subcategory():
    expected_parents = {
        "Elektronik", "Moda", "Ev", "Takı", "Güzellik", "Kırtasiye",
        "Spor", "Oyuncak", "Hediye", "Gıda", "Kozmetik", "Aletler",
    }
    mapped_parents = set(SUBCATEGORY_TO_PARENT.values())
    assert expected_parents <= mapped_parents


def test_turkish_diacritics_are_matched_correctly():
    assert normalize_category("Kıyafet") == "Moda"
    assert normalize_category("Çanta") == "Moda"
    assert normalize_category("Kulaklık") == "Elektronik"
    assert normalize_category("Süpürge") == "Aletler"


def test_unknown_category_is_returned_unchanged():
    assert normalize_category("Bahçe Mobilyası") == "Bahçe Mobilyası"


def test_none_and_empty_pass_through():
    assert normalize_category(None) is None
    assert normalize_category("") == ""
