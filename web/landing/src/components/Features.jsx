import React from 'react'
import { motion } from 'framer-motion'
import { Trophy, ShieldCheck, Headphones, Activity, Ticket, Zap } from 'lucide-react'

const Features = () => {
  return (
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
            { icon: <Ticket />, title: "Ticket & Form Sistemi", desc: "Kullanıcıların destek alabileceği, dinamik butonlu ve forum entegreli gelişmiş başvuru ve talep yönetimi." },
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
  )
}

export default Features
