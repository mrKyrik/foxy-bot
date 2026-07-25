# 🦊 Kumiho Bot (Azalea)

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![Discord.py](https://img.shields.io/badge/discord.py-2.4.0-blue?style=for-the-badge&logo=discord&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle_DB-Red?style=for-the-badge&logo=oracle&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)

Kumiho (eski adıyla Azalea), gelişmiş özelliklere sahip, modüler, tam kapsamlı ve **Oracle Cloud Autonomous Database** destekli profesyonel bir Discord botudur. Hem gelişmiş sunucu içi komutlara, hem de sunucunuzu tek bir tıkla yönetebileceğiniz modern bir **Web Dashboard**'a sahiptir.

---

## 🌟 Temel Özellikler

- **📈 Gelişmiş Seviye Sistemi (Leveling):** Kullanıcılar mesaj yazdıkça veya ses kanallarında durdukça XP kazanır. Dinamik rol ödülleri, kişiselleştirilebilir Rank (Seviye) kartları (arkaplan ve renk destekli) ve ses/yazı XP çarpanları sunar. Yönetimi tamamen Dashboard veya interaktif Embed'ler üzerinden yapılabilir.
- **💰 Kapsamlı Ekonomi Sistemi:** Gelişmiş bir sanal ekonomi. Kullanıcılar para kazanabilir (daily, work, fish), evlenebilir, özel eşyalar satın alabilir ve birbirleriyle etkileşime girebilirler.
- **🌐 Web Dashboard & API:** FastAPI tabanlı bir backend ve React/Vite tabanlı şık bir frontend ile sunucu ayarlarını (level kanalları, prefix, otoroller) tarayıcı üzerinden kolayca yönetin.
- **🛡️ Moderasyon ve Loglama:** Timeout, kick, ban gibi temel komutların yanında tüm sunucu içi olayları loglayabilen detaylı kayıt sistemi.
- **📝 Form & Başvuru Sistemi (Forms):** Discord forum kanallarına veya log kanallarına yönlendirilebilen, dinamik butonlu (Onayla/Reddet/Yanıtla) form sistemleri oluşturabilirsiniz. Form gönderimlerini zamanlayabilirsiniz.
- **🎫 Destek Talepleri (Tickets):** Kullanıcıların yetkililerle özel olarak iletişime geçebileceği hızlı destek sistemi.
- **🎲 Eğlence & Ekstralar:** Müzik çalma, özel ses kanalları (Private Voice), çekilişler, öneriler sistemi ve daha fazlası.

---

## 🏗️ Teknoloji Yığını

- **Bot Çekirdeği:** `discord.py` (Python 3.12)
- **Veritabanı:** `oracledb` (Oracle Cloud Autonomous Database)
- **Web API:** `FastAPI`, `Uvicorn`
- **Frontend (Panel):** `React`, `Vite`, `Tailwind CSS` (isteğe bağlı)
- **Process Manager:** `PM2` (Sunucuda 7/24 barındırma)

---

## 🚀 Kurulum & Çalıştırma

Bot, Oracle DB gerektirdiği için doğrudan çalıştırılmadan önce Wallet (Cüzdan) dosyalarına ve doğru `.env` yapılandırmasına ihtiyaç duyar.

```bash
# 1. Repoyu klonlayın
git clone https://github.com/mrKyrik/foxy-bot.git
cd foxy-bot

# 2. Sanal ortam (venv) oluşturun ve aktif edin
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. .env dosyasını oluşturun (aşağıdaki şablona bakın)
cp .env.example .env

# 5. Oracle cüzdanını ayarlayın
# 'wallet' adında bir klasör oluşturup Oracle Cloud'dan indirdiğiniz cüzdan dosyalarını buraya çıkartın.

# 6. Botu başlatın (Geliştirme için)
python main.py

# 7. PM2 ile Başlatın (Sunucu ortamı için önerilir)
pm2 start main.py --name "Kumiho-Bot" --interpreter python3
pm2 start web/api/main.py --name "Kumiho-API" --interpreter python3
pm2 start npm --name "Kumiho-Dashboard" -- run dev --prefix web/dashboard
```

---

## ⚙️ Çevre Değişkenleri (.env)

Proje dizininde yer alması gereken örnek `.env` yapılandırması:

```env
# Bot Kimlik Bilgileri
DISCORD_TOKEN=your_bot_token_here
OWNER_ID=your_discord_id
STATUS=f.help

# Oracle Veritabanı Bilgileri
DB_USER=admin
DB_PASSWORD=your_oracle_password
DB_DSN=your_database_dsn_name (ör: db_high)
WALLET_LOCATION=./wallet
WALLET_PASSWORD=your_wallet_password

# Web Dashboard (FastAPI & React) OAuth2
CLIENT_ID=your_discord_client_id
CLIENT_SECRET=your_discord_client_secret
JWT_SECRET=a_random_secure_jwt_secret

# URL Ayarları
VITE_API_URL=http://localhost:8000
VITE_DISCORD_REDIRECT_URI=http://localhost:5173/login
```

---

## 🗂️ Klasör Yapısı

```
foxy-bot/
├── main.py                     # Botun ana giriş noktası (Events, Cogs yüklenir)
├── requirements.txt            # Python modülleri
├── Commands/                   # Komut modülleri (Economy, Leveling, Fun, Moderation...)
├── Events/                     # Discord event dinleyicileri (on_message, on_member_join...)
├── core/                       # Veritabanı ve yardımcı sınıf/fonksiyonlar
│   ├── database.py             # Oracle DB bağlantı havuzu yönetimi
│   └── logger.py               # Konsol ve dosya loglama altyapısı
├── web/                        # Web Dashboard dosyaları
│   ├── api/                    # FastAPI backend
│   └── dashboard/              # React (Vite) frontend
└── wallet/                     # (Git'te yok) Oracle Autonomous DB cüzdan dosyaları
```

---

## 📋 Önemli Komutlar (Prefix: `f.`)

- **Yönetim:** `f.setup` (Tüm modülleri UI ile yönetir), `f.setprefix`
- **Seviye:** `f.rank` (Profil kartını gösterir), `f.toprank` (Liderlik tablosu)
- **Ekonomi:** `f.bal`, `f.daily`, `f.shop`, `f.lb`
- **Müzik:** `f.play`, `f.stop`, `f.skip`
- **Kullanıcı:** `f.help`, `f.avatar`, `f.ping`

---

## 📄 Lisans

Bu proje, **Pishi-lab** ve **mrKyrik** iş birliği ile özel olarak geliştirilmiştir.
