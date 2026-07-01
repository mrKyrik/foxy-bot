import os
import sys
import time
import uuid
import requests
import asyncio
import logging

try:
    import jwt
except ImportError:
    print("\n[!] HATA: PyJWT kütüphanesi eksik! Lütfen 'pip install PyJWT' çalıştırın.")
    sys.exit(1)

log = logging.getLogger(__name__)

AWS_LAMBDA_URL = os.getenv(
    "AWS_LAMBDA_URL",
    "https://cres7wfwbl.execute-api.us-east-1.amazonaws.com/default/dcBotAuth",
)

# HMAC GIZLI ANAHTARI — .env dosyasindaki LICENSE_SECRET_KEY ile eslesmeli
SECRET_KEY = os.getenv("LICENSE_SECRET_KEY")
if not SECRET_KEY:
    print("\n[!] HATA: .env dosyasinda LICENSE_SECRET_KEY bulunamadi!")
    print("Ornek: LICENSE_SECRET_KEY=guclu_bir_anahtar_buraya")
    sys.exit(1)

def get_hwid():
    """Bilgisayarin MAC adresinden HWID (Cihaz Kimligi) uretir."""
    mac = uuid.getnode()
    # Basit bir hash ile MAC'i maskele
    import hashlib
    hwid_raw = f"KUMIHO-HWID-{mac}"
    return hashlib.sha256(hwid_raw.encode()).hexdigest()[:16].upper()

def verify_token_and_start(license_key, hwid):
    """Sunucudan JWT token alir ve RSA imzasiyla dogrular."""
    try:
        response = requests.post(
            AWS_LAMBDA_URL,
            json={"license_key": license_key, "hwid": hwid},
            timeout=10
        )
        
        if response.status_code != 200:
            error_msg = response.json().get("message", "Bilinmeyen sunucu hatasi")
            print(f"\n[!] LISANS HATASI: {error_msg}")
            return False

        token = response.json().get("token")
        if not token:
            print("\n[!] LISANS HATASI: Sunucudan token alinamadi!")
            return False
            
        # Token'i HMAC SECRET_KEY ile Çöz ve Doğrula
        try:
            decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], leeway=60)
        except jwt.ExpiredSignatureError:
            print("\n[!] LISANS HATASI: Token suresi dolmus (6 saatlik süre asildi)!")
            return False
        except jwt.InvalidSignatureError:
            print("\n[!] LISANS HATASI: SAHTE TOKEN! Gecersiz HMAC imzasi tespit edildi.")
            return False
        except Exception as e:
            print(f"\n[!] LISANS HATASI: Token dogrulanamadi ({str(e)})")
            return False
            
        # Donanim kontrolu (HWID tokenin icindeki HWID ile ayni mi?)
        token_hwid = decoded_payload.get("hwid")
        if token_hwid != hwid:
            print(f"\n[!] LISANS HATASI: Bu lisans baska bir cihaza (HWID: {token_hwid}) aittir!")
            print("Korsan veya izinsiz kullanim engellendi.")
            return False
            
        print("\n[+] LISANS DOGRULANDI (JWT/RSA)")
        print(f" -> Cihaz Kimligi (HWID): {hwid}")
        return True
        
    except requests.exceptions.RequestException:
        print("\n[!] HATA: Lisans sunucusuna baglanilamadi! Internet baglantinizi kontrol edin.")
        return False
    except Exception as e:
        print(f"\n[!] BEKLENMEYEN HATA: {str(e)}")
        return False

def check_license_sync():
    """Bot baslamadan once yapilan senkron lisans kontrolu."""
    print("[!] Lisans kontrolü geliştirme modu için geçici olarak devre dışı bırakıldı.")
    return True
    
    license_key = os.getenv("LICENSE_KEY")
    if not license_key:
        print("\n[!] HATA: .env dosyasinda LICENSE_KEY bulunamadi!")
        print("Lutfen size verilen lisans anahtarini .env dosyasina ekleyin.")
        time.sleep(5)
        # sys.exit(1)
        
    print("Lisans kontrol ediliyor, lutfen bekleyin...")
    hwid = get_hwid()
    
    if not verify_token_and_start(license_key, hwid):
        time.sleep(5)
        # sys.exit(1)

async def license_check_loop():
    """Bot calisirken her 5 saatte bir (6 saatlik token bitmeden) yeni token alan dongu."""
    return
    await asyncio.sleep(3600 * 5) # 5 saat bekle
    
    while True:
        license_key = os.getenv("LICENSE_KEY")
        hwid = get_hwid()
        
        if not license_key:
            log.critical("Lisans anahtari silinmis! Bot kapatiliyor.")
            # sys.exit(1)
            
        try:
            # Senkron fonksiyonu asenkron ortamda calistir
            is_valid = await asyncio.to_thread(verify_token_and_start, license_key, hwid)
            if not is_valid:
                log.critical("Arka plan lisans yenilemesi basarisiz! Bot kapatiliyor.")
                # sys.exit(1)
        except Exception as e:
            log.warning(f"Arka plan lisans yenilemesinde hata: {e}")
            
        # Sonraki yenileme icin 5 saat bekle
        await asyncio.sleep(3600 * 5)
