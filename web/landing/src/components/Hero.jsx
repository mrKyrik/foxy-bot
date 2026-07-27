import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight } from 'lucide-react'

const Hero = () => {
  return (
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
  )
}

export default Hero
