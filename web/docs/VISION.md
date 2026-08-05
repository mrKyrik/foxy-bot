# Kumiho Bot Dokümantasyon Vizyonu (VISION)

Bu dosya, dokümantasyon sayfalarımızı oluştururken kullanacağımız standart şablonu (template) diğer geliştiriciler için açıklamaktadır. 

## 🎯 Hedef
Amacımız, her komut için sadece metin tabanlı kuru bir anlatım sunmak yerine, görsel açıdan zengin, Discord ortamını yansıtan ve aynı zamanda teknik detay (kaynak kod vb.) barındıran sayfalar oluşturmaktır.

## 📄 Standart Sayfa Yapısı

Tüm komut sayfaları **MDX (.mdx)** formatında olmalı ve şu sıralamayı izlemelidir:

1. **Komut Adı ve Temel Açıklaması**
   - Komut ne işe yarar?

2. **Kullanım (Usage)**
   - `f.komutadı <zorunlu_argüman> [opsiyonel_argüman]`
   
3. **Yetkiler ve Sınırlar (Permissions & Limits)**
   - **Kimler Kullanabilir:** (Örn: Yönetici, Üye)
   - **Bot Yetkisi:** Bot hangi yetkilere ihtiyaç duyar?
   - **Bekleme Süresi:** (Örn: 5 saniye)
   - **Alternatif Kullanımlar (Aliases):** (Örn: `f.bakiye`, `f.bal`)

4. **Görsel Çıktı (Discord Simülasyonu)**
   - `<DiscordMessage>` veya `<DiscordEmbed>` bileşenleri kullanılarak, botun başarılı veya başarısız senaryolarda verdiği cevaplar simüle edilmelidir. Ekran görüntüsü kullanmak yerine React bileşeni kullanılması tercih edilmelidir.

5. **Olası Hatalar ve Çözümleri**
   - Hangi durumlarda hata verir (örn: yeterli bakiye yok, yetki yok) ve çözümleri nelerdir?

6. **Kaynak Kod (Meraklısına)**
   - Botun deposundan `Commands/` altındaki ilgili Python bloğunun sadece o komut için olan kısmı kesilerek eklenmelidir. Bu kod ````python ... ```` tagları arasında verilmelidir.

7. **Önkoşullar ve İlgili Komutlar (Opsiyonel)**
   - Gerekliyse önkoşullar, SSS ve ilgili komut bağlantıları sayfa sonuna eklenebilir.

## 🛠️ MDX Bileşenleri
Sistemimizde `src/components/DiscordEmbed.jsx` içinde hazır bir React bileşeni bulunmaktadır. MDX sayfalarında `import DiscordEmbed from '@site/src/components/DiscordEmbed';` diyerek çağırabilir ve kullanabilirsiniz.

---
*Lütfen yeni bir dokümantasyon sayfası eklerken bu şablona sadık kalın.*
