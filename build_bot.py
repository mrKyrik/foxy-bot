import os
import sys
import shutil
import subprocess

def get_all_modules():
    """Commands, Events ve core dizinlerindeki tum Python dosyalarini module path formatinda dondurur."""
    hidden_imports = []
    
    for folder in ["Commands", "Events", "core"]:
        if not os.path.exists(folder):
            continue
            
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    # Ornek: Commands/administration/moderation.py -> Commands.administration.moderation
                    rel_path = os.path.relpath(os.path.join(root, file), ".")
                    module_name = rel_path.replace(os.sep, ".")[:-3]
                    hidden_imports.append(module_name)
                    
    return hidden_imports

def main():
    print("="*50)
    print("Kumiho Bot - EXE Derleyici (PyInstaller + Firebase)")
    print("="*50)
    
    # 1. PyInstaller Kurulumu Kontrolu
    try:
        import pyinstaller
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        print("[!] Gerekli derleme araclari (PyInstaller, PyJWT, Cryptography) yuklu degil. Yukleniyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "requests", "PyJWT", "cryptography"], check=True)
        
    dist_dir = "dist_exe"
    if os.path.exists(dist_dir):
        print(f"[+] Eski {dist_dir} klasoru temizleniyor...")
        shutil.rmtree(dist_dir, ignore_errors=True)
        
    os.makedirs(dist_dir, exist_ok=True)

    print("\n[Adım 1/3] Gizli moduller (Cogs) taraniyor...")
    hidden_imports = get_all_modules()
    print(f"-> {len(hidden_imports)} adet modül bulundu.")

    print("\n[Adım 2/3] PyInstaller ile EXE derleniyor. Bu islem birkac dakika surebilir...")
    
    # PyInstaller komutlari
    import tempfile
    work_dir = os.path.join(tempfile.gettempdir(), "kumiho_build")
    
    command = [
        sys.executable, "-m", "PyInstaller",
        "--name", "KumihoBot",
        "--onefile", # Tek bir exe dosyasi
        "--console", # Terminal penceresi acik kalsin
        "--clean",
        "--distpath", dist_dir,
        "--workpath", work_dir
    ]
    
    # Butun coglari ve eventleri hidden-import olarak ekle
    for mod in hidden_imports:
        command.extend(["--hidden-import", mod])
        
    # main.py dosyasini ekle
    command.append("main.py")
    
    try:
        subprocess.run(command, check=True)
        print("\n[+] Derleme basarili! KumihoBot.exe olusturuldu.")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Derleme sirasinda hata olustu: {e}")
        sys.exit(1)
        
    print("\n[Adım 3/3] Gerekli bağımlılık dosyaları kopyalanıyor...")
    
    # Musteriye sadece EXE ve .env lazim, bir de varsa DATA klasoru lazim mi?
    # Aslinda Data klasorunu veritabanı olarak kullandigi icin exe yanina kopyalamaliyiz.
    if os.path.exists("Data"):
        dest_data = os.path.join(dist_dir, "Data")
        shutil.copytree("Data", dest_data, dirs_exist_ok=True)
        print(" -> Data klasörü kopyalandı.")
        
    if os.path.exists(".example-env"):
        shutil.copy(".example-env", os.path.join(dist_dir, ".env"))
        print(" -> .env sablonu kopyalandı.")
        
    # Musteri Talimatlari
    readme_content = """# Kumiho Bot - Müşteri Sürümü

Bu bot size özel .exe formatında derlenerek teslim edilmiştir.

## Kurulum Talimatları

1. `.env` dosyasını Not Defteri ile açın.
2. `DISCORD_TOKEN` alanına botunuzun token'ını yazın.
3. `LICENSE_KEY` alanına size verdiğimiz lisans anahtarını yazın.
4. `KumihoBot.exe` dosyasına çift tıklayarak botu çalıştırın!

Python yüklemenize veya terminal komutları girmenize gerek yoktur.

> [!WARNING]
> Lisans süreniz dolduğunda bot otomatik olarak kapanacaktır. Yenilemek için iletişim kurunuz.
"""
    with open(os.path.join(dist_dir, "MUSTERI_KURULUM.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    print("\n" + "="*50)
    print(f" BAŞARILI! Müşteriye gönderilecek klasör: '{dist_dir}'")
    print(" Lütfen bu klasörü ZIP yapıp müşterinize verin.")
    print(" Not: core/license.py icindeki FIREBASE_URL'yi degistirmeyi unutmayin!")
    print("="*50)

if __name__ == "__main__":
    main()
