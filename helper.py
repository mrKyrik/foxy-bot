"""
helper.py — DEPRECATED
-----------------------
Bu dosya artık kullanılmıyor.

Geçiş tamamlandı:
  • json_load / json_save  → core.utils.json_load / json_save
  • owner()                → os.getenv("OWNER_ID")
  • gifs()                 → sabit URL veya core.utils sabitleri

Tüm cog'lar artık bot.db (aiosqlite) üzerinden SQL kullanıyor.
Bu dosyayı güvenle silebilirsiniz.
"""

import warnings

warnings.warn(
    "helper.py is deprecated and will be removed. "
    "Use core.utils or bot.db instead.",
    DeprecationWarning,
    stacklevel=2,
)


def json_load(file):
    from core.utils import json_load as _jl
    return _jl(file)


def json_save(file, data):
    from core.utils import json_save as _js
    return _js(file, data)


def owner():
    import os
    return os.getenv("OWNER_ID", "")


def gifs(key: str = "") -> str:
    return "https://cdn.discordapp.com/banners/1505199750855659570/7b097c5d9cffbb17df26b5357adf92a1.png?size=512"
