# 🦊 Azalea Discord Bot

Güçlü, modüler ve SQL destekli bir Discord botu. Prefix: `f.`

---

## 🚀 Kurulum

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. .env dosyasını oluştur
cp .env.example .env   # veya elle oluştur

# 3. Botu başlat
python main.py
```

> **Not:** Müzik komutları (`f.play`) için `ffmpeg` ayrıca kurulmalıdır.  
> İndirme: https://ffmpeg.org/download.html

---

## ⚙️ .env Yapılandırması

```env
DISCORD_TOKEN=your_bot_token_here
OWNER_ID=your_discord_id,second_owner_id
STATUS=f.help
MY_TWITCH_ACCOUNT=your_twitch_channel
```

---

## 🗂️ Proje Yapısı

```
kumiho/
├── main.py                    # Bot giriş noktası, help sistemi
├── requirements.txt           # Python bağımlılıkları
│
├── core/                      # Çekirdek altyapı
│   ├── database.py            # aiosqlite wrapper (USER-DB.db + ADMIN-EVENTS.db)
│   ├── logger.py              # Merkezi log sistemi (RotatingFileHandler)
│   ├── utils.py               # Ortak yardımcı fonksiyonlar
│   └── embed.py               # EmbedBuilder yardımcısı
│
├── Commands/                  # Komut cog'ları
│   ├── economy.py             # 💰 Ekonomi sistemi (SQL)
│   ├── leveling.py            # 📈 XP/Seviye sistemi (SQL)
│   ├── fun.py                 # 🎉 Eğlence komutları
│   ├── utils.py               # 🛠️ Yardımcı komutlar
│   ├── owner.py               # 👑 Sahip/Admin komutları
│   ├── music.py               # 🎵 Müzik çalar (yt-dlp)
│   ├── nsfw.py                # 🔞 NSFW komutları
│   ├── automod.py             # 🤖 Otomatik moderasyon
│   ├── giveaways.py           # 🎁 Çekiliş sistemi
│   ├── tickets.py             # 🎫 Destek ticket sistemi
│   ├── suggestions.py         # 💡 Öneri sistemi
│   └── administration/        # Yönetim alt paketi
│       ├── moderation.py      # 🛡️ Moderasyon komutları
│       ├── permissions.py     # 🔐 İzin yönetimi
│       └── permission_check.py
│
├── Events/                    # Event listener'lar
│   └── members.py             # Üye giriş/çıkış, saved_roles
│
└── Data/                      # Veritabanı dosyaları (git'te yok)
    ├── USER-DB.db             # Kullanıcı/Sunucu verileri
    └── ADMIN-EVENTS.db        # Moderasyon log'ları
```

---

## 🗃️ Veritabanı Şeması

### USER-DB.db Tabloları

| Tablo | İçerik |
|-------|---------|
| `guild_settings` | Sunucu prefix, log/welcome kanalları |
| `roles` | Kayıtlı roller |
| `role_permissions` | Rol bazlı komut izinleri |
| `warns` | Kullanıcı uyarı kayıtları |
| `economy` | Cüzdan, banka, cooldown'lar, padlock |
| `economy_extras` | Evlilik, çiftçilik, özel başlık, master_crown |
| `inventory` | Kullanıcı envanteri |
| `levels` | XP, seviye, mesaj sayacı |
| `level_rewards` | Seviye ödül rolleri |
| `level_ignores` | XP kazanılmayan kanallar |
| `saved_roles` | Sunucu terk eden üyelerin rolleri |
| `bot_bans` | Global bot yasakları |
| `eco_bans` | Ekonomi yasakları |

### ADMIN-EVENTS.db Tabloları

| Tablo | İçerik |
|-------|---------|
| `admin_events` | Moderasyon eylemleri (kick, ban, timeout...) |

---

## 📋 Komut Kategorileri

| Kategori | Prefix Örneği |
|----------|---------------|
| 💰 Ekonomi | `f.balance`, `f.daily`, `f.shop` |
| 📈 Seviye | `f.rank`, `f.leaderboard_xp` |
| 🎉 Eğlence | `f.trivia`, `f.8ball`, `f.meme` |
| 🛡️ Moderasyon | `f.kick`, `f.ban`, `f.warn` |
| 🎵 Müzik | `f.play`, `f.queue`, `f.skip` |
| 🎁 Çekiliş | `f.gcreate`, `f.gend` |
| 🎫 Ticket | `f.ticket`, `f.close` |
| 💡 Öneri | `f.suggest` |
| 👑 Sahip | `f.givemoney`, `f.botban` |

---

## 📄 Lisans

Bu proje özel kullanım içindir.
