import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight } from 'lucide-react'

const Navbar = ({ activeSection }) => {
  return (
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
        <a href="#commands" className={`nav-item ${activeSection === 'commands' ? 'active-text' : ''}`}>
          Komutlar
          {activeSection === 'commands' && <motion.div layoutId="underline" className="nav-underline" />}
        </a>
        <a href="https://docs-foxy.duckdns.org" className="nav-item">Destek</a>
        <div className="nav-divider"></div>
        <a href="https://admin-foxy.duckdns.org" className="nav-item login-btn">
          Giriş Yap <ArrowUpRight size={16} />
        </a>
      </div>
    </nav>
  )
}

export default Navbar
