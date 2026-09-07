# 🦊 Kumiho Bot & Web Dashboard — Geliştirici Yönergesi ve Yol Haritası

Bu belge, **Kumiho Discord Bot**, **Oracle Cloud Autonomous Database**, **FastAPI Web API** ve **React Dashboard** ekosistemine yeni bir komut veya fonksiyon ekleneceğinde takip edilmesi gereken **uçtan uca (end-to-end) standart çalışma yönergesidir**.

Tüm geliştirmelerin sürdürülebilir, güvenli, test edilebilir ve dokümante edilmiş olması için bu yönergedeki adımların sırasıyla takip edilmesi zorunludur.

---

## 🏛️ 1. Mimari Genel Bakış

Kumiho projesi 4 ana katmandan oluşur:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           KUMIHO EKOSİSTEMİ                             │
├───────────────────┬───────────────────┬─────────────────────────────────┤
│ 1. Discord Bot    │ 2. Web API        │ 3. Web Dashboard                │
│    (discord.py)   │    (FastAPI)      │    (React + Vite + TailwindCSS) │
├───────────────────┴───────────────────┴─────────────────────────────────┤
│                  4. Oracle Cloud Autonomous Database                    │
│                     (Thin Mode + Connection Pool)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Discord Bot (`Commands/`, `core/`, `main.py`)**: Discord kullanıcı etkileşimlerini yönetir, olayları işler ve veritabanına loglar.
- **Web API (`web/api/main.py`)**: Dashboard ile veritabanı arasındaki REST API köprüsüdür; yetki kontrollerini ve veri alışverişini sağlar.
- **Web Dashboard (`web/dashboard/`)**: Sunucu yöneticilerinin komut yetkilerini, logları ve formları yönettiği web arayüzüdür.
- **Oracle DB (`core/database.py`)**: Canlı verilerin (46+ tablo) saklandığı Oracle Autonomous Cloud Veritabanıdır.

---

## 🗺️ 2. Adım Adım Yeni Komut Ekleme Yol Haritası

Bir komut geliştirilirken aşağıdaki **8 aşamalı yaşam döngüsü** eksiksiz tamamlanmalıdır:

```
[1. Tasarım & Cog] ➔ [2. Yetkilendirme] ➔ [3. Help & Docstring] ➔ [4. Veritabanı & Log]
       │
       ▼
[5. Web Panel]     ➔ [6. Testler]      ➔ [7. Commit & Rapor]    ➔ [8. Git Push]
```

---

### 📌 Aşama 1: Komut Tasarımı ve Doğru Cog Seçimi

Yeni eklenecek komutun amacına uygun dosya ve kategori belirlenir:

| Dizin / Dosya | Kategori (`category`) | Kategori Emojisi (`category_emoji`) | Komut Türleri |
|---|---|---|---|
| `Commands/administration/moderation.py` | `Moderasyon` | 🔨 | Ban, Kick, Mute, Warn, Purge |
| `Commands/administration/setup.py` | `Yönetim ve Ayarlar` | ⚙️ | Log kurulum, rol tanımları, kanal ayarları |
| `Commands/administration/permissions.py` | `Yetkilendirme` | 🛡️ | Komut izinleri, panel erişimleri |
| `Commands/economy.py` | `Gelişim ve Ekonomi` | 💰 | Para, bakiye, market, günlük ödül |
| `Commands/leveling.py` | `Gelişim ve Ekonomi` | ⭐ | XP, rank, seviye rolleri |
| `Commands/tickets.py` | `Destek ve İletişim` | 🎫 | Destek talebi açma/kapama |
| `Commands/forms.py` | `Başvuru ve Formlar` | 📝 | Özel form oluşturma ve yanıtlama |
| `Commands/private_voice.py` | `Özel Ses Odaları` | 🎙️ | Oda açma, kilitleme, kişi sınırı |
| `Commands/fun.py` | `Eğlence ve Araçlar` | 🎮 | Mini oyunlar, şakalar, hesaplamalar |
| `Commands/utils.py` | `Genel Araçlar` | 🔧 | Sunucu bilgisi, kullanıcı profili, avatar |

#### Cog Başlığı Standardı
```python
class Moderation(commands.Cog):
    category = "Moderasyon"
    category_emoji = "🔨"

    def __init__(self, bot):
        self.bot = bot
```

---

### 📌 Aşama 2: Merkezi Yetkilendirme (`core.checks`)

Her komut, Web Panel ile senkronize çalışan `@kumiho_check` dekoratörü ile korunmalıdır:

```python
from core.checks import kumiho_check

@commands.command(name="uyar", aliases=["warn"])
@kumiho_check(default_access="owner")  # 'owner' veya 'public'
async def warn_command(self, ctx, member: discord.Member, *, reason: str = "Sebep belirtilmedi"):
    ...
```

- **`default_access="public"`**: Tüm kullanıcıların çalıştırabileceği genel komutlar (Örn: `f.rank`, `f.help`, `f.daily`).
- **`default_access="owner"`**: Varsayılan olarak yalnızca Yöneticilerin ve Sunucu Sahibinin çalıştırabileceği yönetim komutları (Örn: `f.ban`, `f.setup`, `f.automod`).
- **Web Panel Uyumluluğu**: Sunucu sahibi veya admin panelden (`CommandManagementPage`) bir role özel izin verirse veya komutu tamamen kapatırsa (`is_enabled = 0`), `@kumiho_check` otomatik olarak veritabanını okur ve bu kuralı anında uygular.

---

### 📌 Aşama 3: Help Sistemi ve Docstring Standartları

Kumiho Bot'un interaktif `f.help` menüsü ve Web API komut registry'si docstring üzerinden beslenir.

#### Zorunlu Docstring Formatı
```python
@commands.command(name="para-ver", aliases=["givemoney", "pay"])
@kumiho_check(default_access="public")
async def give_money(self, ctx, member: discord.Member, miktar: int):
    """
    Belirtilen kullanıcıya cüzdanınızdan para transfer eder.

    Kullanım:
      f.para-ver @Kullanıcı <miktar>
      f.pay @Kullanıcı <miktar>

    Parametreler:
      @Kullanıcı: Paranın gönderileceği sunucu üyesi.
      miktar: Gönderilmek istenen pozitif tam sayı tutar.

    Örnekler:
      f.para-ver @Ahmet 150
      f.pay @Mehmet 500

    Kurallar:
      - Gönderen kişinin bakiyesi transfer tutarından fazla olmalıdır.
      - Kendinize para gönderemezsiniz.
    """
```

- **İlk Satır**: `cmd.short_doc` olarak kullanılır; hem interaktif yardım menüsünde hem de Web Panelde kısa açıklama olarak gösterilir.
- **Detaylı Bölüm**: `f.help <komut_adi>` yazıldığında kullanıcıya ayrıntılı kullanım rehberi olarak sunulur.

---

### 📌 Aşama 4: Veritabanı ve Loglama Entegrasyonu

1. **Sorgu Standartları**:
   - Parametreli sorgu formatı `?` kullanılır (`core.database` otomatik olarak Oracle `:1, :2` formatına çevirir).
   - `LIMIT N` yerine Oracle uyumlu `FETCH FIRST N ROWS ONLY` sözdizimi kullanılır.
   - `level` sütunu Oracle'da ayrılmış sözcük olduğundan `"LEVEL"` olarak tırnaklanır.
2. **Loglama (`DB_EVENT_LOGS` & `ADMIN_EVENTS`)**:
   - İşlem bir moderasyon/yönetim eylemi ise:
     ```python
     await self.bot.db.log_admin_event(
         guild_id=str(ctx.guild.id),
         admin_id=str(ctx.author.id),
         action_type="WARN",
         target_id=str(member.id),
         reason=reason
     )
     ```
   - İşlem genel bir olay ise (ses, mesaj vb.):
     ```python
     await self.bot.db.log_event(
         guild_id=str(guild.id),
         event_type="role_add",
         user_id=str(member.id),
         details=json.dumps({"role_id": str(role.id), "role_name": role.name}, ensure_ascii=False),
         channel_id=str(channel.id) if channel else None
     )
     ```

---

### 📌 Aşama 5: Web Panel & API Senkronizasyonu

Bot başlatıldığında (`main.py on_ready`), tüm komutları otomatik olarak `BOT_COMMANDS_REGISTRY` tablosuna kaydeder:
- **`command_name`**: Komut adı (Örn: `para-ver`)
- **`category`**: Cog kategorisi (Örn: `Gelişim ve Ekonomi`)
- **`description`**: Kısa açıklama
- **`default_access`**: `public` veya `owner`

#### Web Dashboard Yansıması
- Komut eklendiğinde **ekstra frontend kod yazmaya gerek kalmadan** `https://kyrik.duckdns.org` üzerindeki **"Komut Yönetimi"** sayfasına otomatik olarak düşer.
- Sunucu yöneticileri komutu tek tıkla açıp kapatabilir veya belirli Discord rollerine bağlayabilir.

---

### 📌 Aşama 6: Test ve Doğrulama Protokolü

Kod tamamlandıktan sonra testler çalıştırılmadan commit atılamaz.

1. **Birim & Mantık Testleri**:
   - `scratch/test_<komut_adi>.py` altında bağımsız bir test dosyası oluşturulur.
   - Başarı ve hata senaryoları (yetersiz bakiye, yetkisiz kullanıcı, geçersiz parametre vb.) test edilir.
2. **Veritabanı Entegrasyon Testi**:
   - Oracle Cloud veritabanı ile sorgunun doğru çalıştığı, constraint hatası vermediği teyit edilir.
3. **API & Web Testi**:
   - `fastapi.testclient.TestClient` ile API endpoint'lerinin doğru yanıt (`HTTP 200`) döndüğü doğrulanır.
4. **Yerel DB Explorer ile Doğrulama**:
   - `python run_db_viewer.py` çalıştırılarak veritabanına yazılan kayıtlar görsel olarak teyit edilir.

---

### 📌 Aşama 7: Raporlama Standardı (`docs/` Klasörü)

> [!IMPORTANT]
> **Zorunlu Kural**: Yapılan her önemli geliştirme, hata düzeltmesi veya yeni özellik için `docs/` klasörü altına bir rapor dosyası yazılmalıdır.
> Rapor dosyasının adı ve ana başlığı **kesinlikle o anki Commit ID (veya commit hash) ile başlamalıdır.**

#### Dosya İsimlendirme Formatı:
`docs/<commit_hash>-<özellik_veya_konu>_report.md`  
*(Örnek: `docs/8f44e5d-overview-stats-fix-report.md`)*

#### Rapor Şablonu:
```markdown
# 📋 Geliştirme ve Test Raporu — Commit `<commit_hash>`

**Tarih:** YYYY-MM-DD  
**Modül / Kapsam:** (Örn: `Commands/economy.py`, `web/api/main.py`)  
**Geliştirici / Rol:** (Örn: Antigravity Assistant)  
**Durum:** Başarılı / Test Edildi ✅

---

## 🎯 1. Amaç ve Kapsam
Bu geliştirmede ne yapıldığı, hangi sorunun çözüldüğü veya hangi yeni fonksiyonun eklendiği kısaca açıklanır.

---

## 🛠️ 2. Yapılan Değişiklikler
- **Değiştirilen/Eklenen Dosyalar:**
  - `Commands/yeni_modul.py` (Yeni komut mantığı)
  - `web/api/main.py` (API entegrasyonu)
- **Teknik Detaylar:**
  - Yetki kontrolü (`kumiho_check`) tanımlandı.
  - Oracle DB sorguları optimize edildi.

---

## 🧪 3. Yapılan Testler ve Çıktılar

### Test 1: Komut Parametre ve Mantık Testi
- **Komut:** `python scratch/test_yeni_komut.py`
- **Sonuç:** Başarılı (`PASSED`)
- **Çıktı Özeti:**
  ```text
  Testing valid parameters -> OK
  Testing invalid authorization -> Caught CommandNotAllowed as expected.
  ```

### Test 2: Veritabanı ve API Entegrasyonu
- **Sonuç:** `HTTP 200 OK`
- **Eklenen Kayıt Sayısı:** 1 satır (`DB_EVENT_LOGS`)

---

## ✅ 4. Doğrulama Kontrol Listesi
- [x] Docstring ve Help açıklamaları yazıldı.
- [x] `@kumiho_check` ile yetki sınırları belirlendi.
- [x] Veritabanı loglama çağrıları eklendi.
- [x] Web API komut senkronizasyonu doğrulandı.
- [x] Tüm testler sıfır hata ile geçti.
```

---

### 📌 Aşama 8: Git & Dağıtım Standartları

1. **`.gitignore` Kontrolü**:
   - `git status` çalıştırılarak yerel araçların (`db_viewer/`, `run_db_viewer.py`), geçici dosyaların (`scratch/`, `*.db`) depoya dahil edilmediği teyit edilir.
2. **Commit Mesaj Formatı (Conventional Commits)**:
   - `feat(kategori): yeni komut ve help açıklaması eklendi`
   - `fix(modül): x hatası düzeltildi ve test edildi`
   - `docs(rapor): <commit_hash> geliştirme raporu eklendi`
3. **Uzak Sunucu Güvenlik Kuralları**:
   - Kullanıcıdan açık onay alınmadan **kesinlikle VPS'e SSH (`ssh ubuntu@...`, `scp`) bağlantısı yapılmaz**.
   - Sunucuda manuel build komutları (`npm run build`) **asla çalıştırılmaz** (dosya izin ve `dist` çökme sorunlarını önlemek için).

---

## 💡 3. A'dan Z'ye Referans Komut Geliştirme Örneği

Aşağıda tüm kurallara uygun eksiksiz bir örnek komut yer almaktadır:

```python
import discord
from discord.ext import commands
from core.checks import kumiho_check
import json

class ServerUtilities(commands.Cog):
    category = "Genel Araçlar"
    category_emoji = "🔧"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="sunucu-ozet", aliases=["serverstats", "sozet"])
    @kumiho_check(default_access="public")
    async def server_summary(self, ctx):
        """
        Sunucunun anlık üye, kanal ve rol istatistiklerini özet embed olarak gösterir.

        Kullanım:
          f.sunucu-ozet
          f.serverstats

        Yetki:
          Herkese açık (Public). Web panelden sınırlandırılabilir.
        """
        guild = ctx.guild
        total_members = guild.member_count
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        roles_count = len(guild.roles)

        embed = discord.Embed(
            title=f"📊 {guild.name} — İstatistik Özeti",
            color=discord.Color.purple(),
            timestamp=ctx.message.created_at
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="👥 Toplam Üye", value=str(total_members), inline=True)
        embed.add_field(name="💬 Metin Kanalları", value=str(text_channels), inline=True)
        embed.add_field(name="🔊 Ses Kanalları", value=str(voice_channels), inline=True)
        embed.add_field(name="🛡️ Rol Sayısı", value=str(roles_count), inline=True)
        embed.set_footer(text=f"Talep eden: {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

        # Olayı veritabanına logla
        await self.bot.db.log_event(
            guild_id=str(guild.id),
            event_type="cmd_server_summary",
            user_id=str(ctx.author.id),
            details=json.dumps({"channel_id": str(ctx.channel.id)}, ensure_ascii=False),
            channel_id=str(ctx.channel.id)
        )

async def setup(bot):
    await bot.add_cog(ServerUtilities(bot))
```

---

## 📋 4. Geliştirici Kontrol Listesi (Checklist)

Her geliştirmede bu listeyi zihninizde veya raporda onaylayın:

- [ ] **1. Kategori & Cog**: Komut doğru dosyaya ve doğru `category` altına eklendi mi?
- [ ] **2. Docstring**: Kısa özet, Kullanım (`Usage:`), Parametreler ve Örnekler yazıldı mı?
- [ ] **3. Yetki**: `@kumiho_check(default_access="...")` eklendi mi?
- [ ] **4. Oracle Uyumu**: Sorgularda `FETCH FIRST`, `"LEVEL"`, ve `?` bağlayıcıları doğru mu?
- [ ] **5. Loglama**: Önemli olaylar `log_admin_event` veya `log_event` ile kaydedildi mi?
- [ ] **6. Test**: `scratch/` testleri başarıyla çalıştırıldı mı?
- [ ] **7. Rapor**: `docs/<commit_hash>-..._report.md` dosyası oluşturuldu mu?
- [ ] **8. Git**: Sadece gerekli dosyalar stage edildi, `git status` temiz mi?
