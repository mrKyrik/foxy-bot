import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, Trophy, ShieldCheck, Headphones, Activity, Bot, Zap, MessageSquare } from 'lucide-react'
import './App.css'

function App() {
  const [activeSection, setActiveSection] = useState('hero');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.5 }
    );

    const sections = document.querySelectorAll('section');
    sections.forEach((section) => observer.observe(section));

    return () => observer.disconnect();
  }, []);

  return (
    <div className="app-container">
      
      {/* Absolute Navbar */}
      <nav className="navbar">
        <div className="nav-pill">
          <a href="#hero" className={`nav-item ${activeSection === 'hero' ? 'active-text' : ''}`}>
            Ana Sayfa
            {activeSection === 'hero' && <motion.div layoutId="underline" className="nav-underline" />}
          </a>
          <a href="#features" className={`nav-item ${activeSection === 'features' ? 'active-text' : ''}`}>
            Özellikler
            {activeSection === 'features' && <motion.div layoutId="underline" className="nav-underline" />}
          </a>
          <a href="https://docs-foxy.duckdns.org" className="nav-item">Destek</a>
          <div className="nav-divider"></div>
          <a href="https://admin-foxy.duckdns.org" className="nav-item login-btn">
            Giriş Yap <ArrowUpRight size={16} />
          </a>
        </div>
      </nav>

      {/* PANEL 1: Hero (Light) */}
      <section id="hero" className="panel panel-light">
        <div className="container hero-content">
          
          {/* Left: Logo sliding in from left */}
          <motion.div 
            className="hero-left"
            initial={{ opacity: 0, x: -100 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, type: "spring", bounce: 0.4 }}
            viewport={{ once: false, amount: 0.5 }}
          >
            <img src="/foxy-bot-pp.webp" alt="Kumiho Logo" className="hero-image" />
          </motion.div>

          {/* Right: Text fading in and sliding up */}
          <motion.div 
            className="hero-right"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            viewport={{ once: false, amount: 0.5 }}
          >
            <div className="hero-subtitle">Yapay Zeka Destekli</div>
            <h1 className="hero-title">Meet <span>Kumiho</span></h1>
            <p className="hero-desc">
              Sunucu yönetimini akıllı moderasyon, dinamik etkileşimler ve eşsiz yapay zeka gücüyle kusursuzlaştırın.
            </p>
            <div className="hero-actions">
              <a href="https://discord.com/oauth2/authorize?client_id=1514724443824328744&scope=bot" className="btn btn-primary" target="_blank" rel="noreferrer">
                Sunucuya Ekle <ArrowUpRight size={18} />
              </a>
              <a href="#features" className="link-action">
                Özellikleri Keşfet
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* PANEL 2: Features (Dark) */}
      <section id="features" className="panel panel-dark">
        <div className="container features-content">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: false, amount: 0.3 }}
          >
            <div className="hero-subtitle" style={{ color: 'var(--color-text-muted)' }}>Gerçek Kumiho Farkı</div>
            <h2 className="section-title">Akıllıca, hepsi bir arada</h2>
            <p className="hero-desc" style={{ margin: '0 auto' }}>
              Temel özellikleri bile süper güçlere kavuşturan eşsiz bir altyapı.
            </p>
          </motion.div>

          <div className="features-grid">
            {[
              { icon: <Trophy />, title: "Seviye & Ekonomi", desc: "Üyelerinizi motive eden detaylı seviye sistemi ve tamamen özelleştirilebilir geniş kapsamlı ekonomi altyapısı." },
              { icon: <ShieldCheck />, title: "Moderasyon & Forum", desc: "Sarsılmaz moderasyon araçları ve sunucunuza özel, tamamen kişiselleştirilebilen gelişmiş forum sistemleri." },
              { icon: <Headphones />, title: "Dinamik Ses Odaları", desc: "Kullanıcıların kendi ses kanallarını oluşturup tam yetkiyle yönetebildiği otomatik ve sorunsuz ses odası ağı." },
              { icon: <Activity />, title: "Timeline Tabanlı Loglar", desc: "Web panel üzerinden anlık izlenebilen, dünyanın en okunaklı ve detaylı 'zaman çizelgesi' (Timeline) tabanlı log sistemi." },
              { icon: <Bot />, title: "Yapay Zeka Destekli", desc: "Sorulara yanıt veren, sohbet eden ve sunucunuzun kültürüne ayak uyduran gelişmiş AI asistan entegrasyonu." },
              { icon: <Zap />, title: "Gelişmiş Eğlence", desc: "Gelişmiş eğlence sistemleri, mini oyunlar ve reaksiyon tabanlı etkileşimlerle sunucunuzu daima aktif tutun." }
            ].map((feature, idx) => (
              <motion.div 
                className="feature-card" 
                key={idx}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: idx * 0.15 }}
                viewport={{ once: false, amount: 0.5 }}
              >
                <div className="feature-icon">{feature.icon}</div>
                <div>
                  <h3 className="feature-title">{feature.title}</h3>
                  <p className="feature-desc">{feature.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* PANEL 3: FAQ (Light) */}
      <section id="faq" className="panel panel-light" style={{ minHeight: '80vh', padding: '6rem 2rem' }}>
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
              <div key={i} style={{ background: 'rgba(0,0,0,0.03)', padding: '1.5rem', borderRadius: '16px', display: 'flex', gap: '1rem' }}>
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
      
    </div>
  )
}

export default App
