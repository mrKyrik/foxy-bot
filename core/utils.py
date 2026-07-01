"""
core/utils.py
-------------
Ortak yardımcı fonksiyonlar — tüm cog'ların import ettiği merkezi util modülü.

Bu dosya şunları içerir:
  • json_load / json_save  — migration aşamasında eski JSON verilerini okumak için
  • parse_duration          — "10m", "2h", "1d" gibi süre string'lerini saniyeye çevirir
  • Ortak sabitler
"""

import json
import logging
import os
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON helpers (migration / eski veri okuma)
# ---------------------------------------------------------------------------

def json_load(file) -> dict:
    """
    JSON dosyasını güvenli şekilde oku. Dosya yoksa ya da bozuksa {} döndür.

    Args:
        file: Dosya yolu (str veya Path)

    Returns:
        dict: Okunan veriler ya da boş dict
    """
    path = str(file)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        log.warning("json_load başarısız (%s): %s", path, e)
        return {}


def json_save(file, data: dict) -> None:
    """
    dict'i JSON dosyasına yaz. Gerekirse dizini oluşturur.

    Args:
        file: Dosya yolu (str veya Path)
        data: Kaydedilecek veriler
    """
    path = str(file)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except OSError as e:
        log.error("json_save başarısız (%s): %s", path, e)


# ---------------------------------------------------------------------------
# Duration parser
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"(?P<value>\d+)\s*(?P<unit>[smhd]?)", re.IGNORECASE)
_UNIT_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(duration_str: str) -> int:
    """
    "10m", "2h30m", "1d" gibi süre string'lerini toplam saniyeye çevirir.
    Birim belirtilmezse dakika varsayılır.

    Args:
        duration_str: Süre string'i

    Returns:
        int: Toplam saniye (parse edilemezse 0)

    Örnekler:
        >>> parse_duration("30s")  →  30
        >>> parse_duration("2h")   →  7200
        >>> parse_duration("1d")   →  86400
        >>> parse_duration("10")   →  600   (varsayılan dakika)
    """
    if not duration_str:
        return 0

    total = 0
    for match in _DURATION_RE.finditer(duration_str.strip().lower()):
        value = int(match.group("value"))
        unit = match.group("unit") or "m"  # birim yoksa dakika
        total += value * _UNIT_MAP.get(unit, 60)

    return total


# ---------------------------------------------------------------------------
# Ortak sabitler
# ---------------------------------------------------------------------------

# Onay kelimeleri (konfirmasyon gerektiren komutlarda)
CONFIRM_WORDS = {"evet", "yes", "onayla", "confirm", "kabul"}
