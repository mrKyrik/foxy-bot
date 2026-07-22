import sqlite3
import os

print("Bozuk dump dosyasından yeni bir SQLite veritabanı inşa ediliyor...")

# Eğer daha önce varsa sil
if os.path.exists('rescued_kumiho.db'):
    os.remove('rescued_kumiho.db')

conn = sqlite3.connect('rescued_kumiho.db')

with open('kumiho_dump.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

try:
    conn.executescript(sql_script)
    conn.commit()
    print("Veriler başarıyla kurtarıldı ve rescued_kumiho.db oluşturuldu!")
except Exception as e:
    print(f"Hata oluştu: {e}")
finally:
    conn.close()
