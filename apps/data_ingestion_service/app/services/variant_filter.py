import re
from typing import Any, Dict, List, Optional

# Baslik metninde gecen anahtar kelimelere gore kaba bir varyant tespiti.
# %100 dogru degil (heuristic) - ama marketplace filtre API'lerini tek tek
# reverse-engineer etmekten cok daha az risk tasiyor.

_WIRELESS_KEYWORDS = ["kablosuz", "bluetooth", "wireless", " bt "]
_WIRED_KEYWORDS = ["kablolu", "3.5mm", "3,5mm", " aux", "wired", "mikrofonlu kablo"]
_DUAL_SIM_KEYWORDS = ["dual sim", "dual-sim", "çift hat", "cift hat", "çift sim", "cift sim"]

_RAM_STORAGE_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)\s*gb", re.IGNORECASE)
_RAM_PATTERN = re.compile(r"(\d+)\s*gb\s*ram", re.IGNORECASE)
_GB_PATTERN = re.compile(r"(\d+)\s*gb", re.IGNORECASE)

# Klavye duzeni: kod (TR/US/UK) + harf (Q/F) ikilisi basliklarda genelde
# birlikte geciyor. "Turkce Q/F" Turkce dil adiyla da yazilabiliyor; US/UK
# icin dil adi tespiti daha belirsiz oldugundan sadece kod+harf kalibina
# guveniyoruz.
_LAYOUT_PATTERNS = {
    "TR Q": [r"\btr\s*-?\s*q\b", r"türkçe\s*q\b", r"q\s*türkçe\b"],
    "TR F": [r"\btr\s*-?\s*f\b", r"türkçe\s*f\b", r"f\s*türkçe\b"],
    "US Q": [r"\bus\s*-?\s*q\b", r"ngilizce\s*q\b"],
    "UK Q": [r"\buk\s*-?\s*q\b"],
}


def build_query_suffix(
    connection_type: Optional[str] = None,
    ram_gb: Optional[int] = None,
    storage_gb: Optional[int] = None,
    sim_type: Optional[str] = None,
    keyboard_layout: Optional[str] = None,
) -> str:
    parts = []
    if connection_type:
        parts.append(connection_type)
    if ram_gb:
        parts.append(f"{ram_gb}gb ram")
    if storage_gb:
        parts.append(f"{storage_gb}gb")
    if sim_type == "cift_hat":
        parts.append("çift hat")
    elif sim_type == "tek_hat":
        parts.append("tek hat")
    if keyboard_layout:
        parts.append(keyboard_layout)
    return " ".join(parts)


def _matches_connection_type(name: str, wanted: str) -> bool:
    name_l = name.lower()
    has_wireless = any(k in name_l for k in _WIRELESS_KEYWORDS)
    has_wired = any(k in name_l for k in _WIRED_KEYWORDS)
    if wanted == "kablosuz":
        return not (has_wired and not has_wireless)
    if wanted == "kablolu":
        return not (has_wireless and not has_wired)
    return True


def _matches_ram_storage(name: str, ram_gb: Optional[int], storage_gb: Optional[int]) -> bool:
    name_l = name.lower()

    combo = _RAM_STORAGE_PATTERN.search(name_l)
    if combo:
        found_ram, found_storage = int(combo.group(1)), int(combo.group(2))
        if ram_gb and found_ram != ram_gb:
            return False
        if storage_gb and found_storage != storage_gb:
            return False
        return True

    if ram_gb:
        ram_match = _RAM_PATTERN.search(name_l)
        if ram_match and int(ram_match.group(1)) != ram_gb:
            return False

    if storage_gb:
        gb_numbers = [int(m.group(1)) for m in _GB_PATTERN.finditer(name_l)]
        ram_match = _RAM_PATTERN.search(name_l)
        if ram_match:
            gb_numbers = [n for n in gb_numbers if n != int(ram_match.group(1))]
        if gb_numbers and storage_gb not in gb_numbers:
            return False

    return True


def _detect_keyboard_layout(name_l: str) -> Optional[str]:
    for layout, patterns in _LAYOUT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_l):
                return layout
    return None


def _matches_keyboard_layout(name: str, wanted: str) -> bool:
    detected = _detect_keyboard_layout(name.lower())
    if detected is None:
        return True
    return detected == wanted


def filter_results(
    results: List[Dict[str, Any]],
    connection_type: Optional[str] = None,
    ram_gb: Optional[int] = None,
    storage_gb: Optional[int] = None,
    keyboard_layout: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not (connection_type or ram_gb or storage_gb or keyboard_layout):
        return results

    filtered = []
    for item in results:
        name = item.get("name") or ""
        if not name:
            filtered.append(item)
            continue
        if connection_type and not _matches_connection_type(name, connection_type):
            continue
        if (ram_gb or storage_gb) and not _matches_ram_storage(name, ram_gb, storage_gb):
            continue
        if keyboard_layout and not _matches_keyboard_layout(name, keyboard_layout):
            continue
        filtered.append(item)

    return filtered
