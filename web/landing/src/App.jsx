import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, Trophy, ShieldCheck, Headphones, Activity } from 'lucide-react'
import './App.css'

function App() {
  return (
    <div className="app-container">
      
      {/* Absolute Navbar */}
      <nav className="navbar">
        <div className="nav-pill">
          <a href="#hero" className="nav-item active">Ana Sayfa</a>
          <a href="#features" className="nav-item">Özellikler</a>
          <a href="#pricing" className="nav-item">Premium</a>
          <a href="#faq" className="nav-item">SSS</a>
          <a href="https://docs-foxy.duckdns.org" className="nav-item">Destek</a>
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
              <a href="https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot" className="btn btn-primary">
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
              { icon: <Activity />, title: "Timeline Tabanlı Loglar", desc: "Web panel üzerinden anlık izlenebilen, dünyanın en okunaklı ve detaylı 'zaman çizelgesi' (Timeline) tabanlı log sistemi." }
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

      {/* PANEL 3: Pricing Dummy (Light) */}
      <section id="pricing" className="panel panel-light">
         <div className="container features-content">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: false, amount: 0.5 }}
          >
            <div className="hero-subtitle">Premium</div>
            <h2 className="section-title">Hangi Paket Size Göre?</h2>
            <p className="hero-desc" style={{ margin: '0 auto', marginBottom: '2rem' }}>
              Gelecek güncellemelerle Premium ayrıcalıklarına sahip olun.
            </p>
            <button className="btn btn-outline">Çok Yakında</button>
          </motion.div>
        </div>
      </section>
      
    </div>
  )
}

export default App
