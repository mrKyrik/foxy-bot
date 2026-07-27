import React from 'react'
import { MessageSquare } from 'lucide-react'

const FAQ = () => {
  return (
    <section id="faq" className="panel panel-dark" style={{ minHeight: '100vh', paddingTop: '6rem' }}>
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <h2 className="section-title">Sıkça Sorulan Sorular</h2>
          <p className="hero-desc" style={{ margin: '0 auto' }}>Aklınıza takılan soruların yanıtları</p>
        </div>
        <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {[
            { q: "Kumiho tamamen ücretsiz mi?", a: "Temel sunucu yönetim özelliklerinin tamamı ücretsizdir. Özel AI limitleri ve ileri düzey log tutma süreleri için premium seçeneklerimiz bulunmaktadır." },
            { q: "Verilerim güvende mi?", a: "Tüm loglarınız ve sunucu ayarlarınız uçtan uca şifrelenmiş veritabanlarımızda güvenle saklanır ve kimseyle paylaşılmaz." },
            { q: "Kurulumu ne kadar sürüyor?", a: "Sadece tek bir tıklamayla sunucunuza ekleyip saniyeler içinde web panelinden yönetmeye başlayabilirsiniz." },
          ].map((item, i) => (
            <div key={i} className="faq-card">
              <MessageSquare style={{ color: 'var(--color-cyan)', flexShrink: 0 }} />
              <div>
                <h4 style={{ fontSize: '1.1rem', fontWeight: '700', marginBottom: '0.5rem' }}>{item.q}</h4>
                <p style={{ color: 'var(--color-text-muted)' }}>{item.a}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FAQ
