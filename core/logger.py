from __future__ import annotations
"""
core/logger.py
--------------
Merkezi logging yapılandırması.

Kullanım (her modülde):
    import logging
    log = logging.getLogger(__name__)
    log.info("Bir mesaj")
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def setup_logging(log_file: str = "Data/discord.log", level: int = logging.INFO) -> None:
    """
    Uygulamanın logging altyapısını bir kez kurar.
    Birden fazla çağrılsa da yalnızca ilk çağrı geçerlidir.

    Args:
        log_file: Log dosyasının yolu.
        level:    Kök logger'ın log seviyesi (varsayılan INFO).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    # Data/ klasörü yoksa oluştur
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # -------------------------------------------------------
    # Format
    # -------------------------------------------------------
    fmt = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # -------------------------------------------------------
    # Dosya handler — 5 MB × 3 yedek, UTF-8
    # -------------------------------------------------------
    file_handler = RotatingFileHandler(
        filename=log_file,
        encoding="utf-8",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        mode="a",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)  # Dosyaya her şeyi yaz

    # -------------------------------------------------------
    # Konsol handler — sadece INFO ve üzeri
    # -------------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    # -------------------------------------------------------
    # Kök logger
    # -------------------------------------------------------
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Alt handler'lar filtreler
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # discord.py'nin kendi loglarını DEBUG yerine WARNING'de tut
    # (yoksa log dosyası discord internal mesajlarla dolar)
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging sistemi başlatıldı → %s", log_file)
