import React from 'react'
import { motion } from 'framer-motion'
import { Settings, BarChart3, Terminal } from 'lucide-react'

const CommandsPreview = () => {
  return (
    <section id="commands" className="panel panel-light">
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: '4rem', paddingTop: '4rem' }}>
          <div className="hero-subtitle">Kolay ve Güçlü</div>
          <h2 className="section-title">Temel Komutlarımız</h2>
          <p className="hero-desc" style={{ margin: '0 auto' }}>Kumiho'yu sunucunuzda kullanmak sadece birkaç tuş uzaklıkta.</p>
        </div>
        
        <div className="commands-showcase">
          {/* f.setup Command */}
          <motion.div 
            className="command-box"
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: false, amount: 0.5 }}
          >
            <div className="command-header">
              <Settings size={24} className="command-icon" />
              <div className="command-title-area">
                <h3>Sunucu Kurulumu</h3>
                <p>Her şeyi saniyeler içinde hazırlayın.</p>
              </div>
            </div>
            <div className="terminal-window">
              <div className="terminal-header">
                <span className="dot dot-red"></span>
                <span className="dot dot-yellow"></span>
                <span className="dot dot-green"></span>
              </div>
              <div className="terminal-body">
                <p className="typing-text"><span className="prefix">/</span>setup</p>
                <div className="terminal-response">
                  <BotIcon /> <span>Kumiho kurulum sihirbazı başlatıldı. Lütfen log kanalını etiketleyin...</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* f.rank Command */}
          <motion.div 
            className="command-box"
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            viewport={{ once: false, amount: 0.5 }}
          >
            <div className="command-header">
              <BarChart3 size={24} className="command-icon" style={{ color: 'var(--color-cyan)' }} />
              <div className="command-title-area">
                <h3>Seviye Sistemi</h3>
                <p>Üyelerinizin durumunu anında görüntüleyin.</p>
              </div>
            </div>
            <div className="terminal-window">
              <div className="terminal-header">
                <span className="dot dot-red"></span>
                <span className="dot dot-yellow"></span>
                <span className="dot dot-green"></span>
              </div>
              <div className="terminal-body">
                <p className="typing-text"><span className="prefix">/</span>rank</p>
                <div className="terminal-response rank-response">
                  <div className="rank-card-mockup">
                    <div className="rank-avatar"></div>
                    <div className="rank-info">
                      <div className="rank-name">User#1234</div>
                      <div className="rank-bar"><div className="rank-fill" style={{width: '75%'}}></div></div>
                      <div className="rank-level">Seviye 12 • Sıra #3</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

const BotIcon = () => (
  <Terminal size={16} style={{ color: 'var(--color-cyan)', display: 'inline-block', marginRight: '8px' }} />
)

export default CommandsPreview
