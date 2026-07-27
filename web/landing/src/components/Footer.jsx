import React from 'react'
import { ArrowUpRight } from 'lucide-react'

const Footer = () => {
  return (
    <section id="footer" className="panel panel-light footer-panel">
      <div className="container footer-content">
        
        {/* CTA Area */}
        <div className="cta-area">
          <h2 className="section-title">Hemen Başlayın</h2>
          <p className="hero-desc" style={{ margin: '0 auto 2rem auto' }}>
            Sunucunuzu bir üst seviyeye taşımak için ihtiyacınız olan her şey Kumiho'da.
          </p>
          <a href="https://discord.com/oauth2/authorize?client_id=1514724443824328744&scope=bot" className="btn btn-primary cta-btn" target="_blank" rel="noreferrer">
            Kumiho'yu Sunucuna Ekle <ArrowUpRight size={18} />
          </a>
        </div>

        {/* Actual Footer Area */}
        <footer className="footer-bottom">
          <div className="footer-grid">
            <div className="footer-brand">
              <h3 style={{ fontSize: '1.5rem', fontWeight: '800', marginBottom: '1rem' }}>Kumiho</h3>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                Discord sunucuları için gelişmiş yapay zeka destekli yönetim ve eğlence botu.
              </p>
            </div>
            
            <div className="footer-links">
              <h4>Bağlantılar</h4>
              <a href="#hero">Ana Sayfa</a>
              <a href="#features">Özellikler</a>
              <a href="#commands">Komutlar</a>
              <a href="https://admin-foxy.duckdns.org">Admin Paneli</a>
            </div>

            <div className="footer-links">
              <h4>Destek</h4>
              <a href="https://docs-foxy.duckdns.org">Dokümantasyon</a>
              <a href="#">Gizlilik Politikası</a>
              <a href="#">Kullanım Şartları</a>
            </div>
          </div>
          
          <div className="footer-copyright">
            &copy; {new Date().getFullYear()} Kumiho. Tüm hakları saklıdır.
          </div>
        </footer>
      </div>
    </section>
  )
}

export default Footer
