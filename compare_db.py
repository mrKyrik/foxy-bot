import sqlite3
import oracledb
import os
import subprocess

# SSH ve Uzak Sunucu Ayarları (Kendi sunucunuza göre düzenleyin)
SSH_HOST = "sunucu_ip_adresi"
SSH_USER = "root"
REMOTE_DB_PATH = "/root/kumiho/kumiho.db"
LOCAL_SQLITE_PATH = "remote_kumiho.db"

# Oracle Ayarları
DB_USER = "admin"
DB_PASSWORD = "$@P%5WCUgMnb"
DB_DSN = "kumihodb_high"
WALLET_DIR = os.path.join(os.path.dirname(__file__), "core", "wallet")

def download_remote_db():
    print(f"Sunucudan ({SSH_HOST}) kumiho.db dosyası çekiliyor...")
    # scp komutu ile dosyayı çek
    scp_cmd = f"scp {SSH_USER}@{SSH_HOST}:{REMOTE_DB_PATH} {LOCAL_SQLITE_PATH}"
    result = subprocess.run(scp_cmd, shell=True)
    if result.returncode != 0:
        print("SSH indirme işlemi başarısız oldu. Lütfen IP ve dosya yollarını kontrol edin.")
        return False
    print("Dosya başarıyla indirildi!")
    return True

def compare_databases():
    if not os.path.exists(LOCAL_SQLITE_PATH):
        print(f"{LOCAL_SQLITE_PATH} bulunamadı!")
        return

    print("Veritabanlarına bağlanılıyor...")
    
    # SQLite (Sunucudan Gelen)
    sqlite_conn = sqlite3.connect(LOCAL_SQLITE_PATH)
    sqlite_cursor = sqlite_conn.cursor()
    
    # Oracle (Anlık/Yeni DB)
    # oracledb.init_oracle_client(config_dir=WALLET_DIR) # Thin mod kullanıyorsak bu satırı silebiliriz
    # Thin mod bağlantısı:
    ora_conn = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR,
        wallet_password=DB_PASSWORD
    )
    ora_cursor = ora_conn.cursor()
    
    # Tüm tabloları al (SQLite'tan)
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    
    print("\n--- Veri Karşılaştırma Raporu ---")
    print(f"{'Tablo Adı':<25} | {'Sunucu (SQLite)':<15} | {'Anlık (Oracle)':<15} | {'Durum':<10}")
    print("-" * 70)
    
    for table in tables:
        # SQLite'daki satır sayısı
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = sqlite_cursor.fetchone()[0]
        
        # Oracle'daki satır sayısı
        ora_table = '"LEVEL"' if table.upper() == 'LEVEL' else table.upper()
        try:
            ora_cursor.execute(f"SELECT COUNT(*) FROM {ora_table}")
            ora_count = ora_cursor.fetchone()[0]
        except oracledb.DatabaseError as e:
            ora_count = "HATA (Tablo Yok?)"
            
        durum = "EŞİT" if sqlite_count == ora_count else "FARKLI"
        print(f"{table:<25} | {str(sqlite_count):<15} | {str(ora_count):<15} | {durum:<10}")

    sqlite_conn.close()
    ora_conn.close()
    print("-" * 70)

if __name__ == "__main__":
    # 1. Aşama: Dosyayı Çek
    # success = download_remote_db()
    
    # Eğer dosyayı manuel olarak klasöre attıysanız üstteki satırı yorum satırı yapıp sadece aşağıdaki satırı çalıştırın:
    # 2. Aşama: Karşılaştır
    # if success or os.path.exists(LOCAL_SQLITE_PATH):
    compare_databases()
