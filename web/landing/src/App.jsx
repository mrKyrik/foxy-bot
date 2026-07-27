import React, { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import Features from './components/Features'
import CommandsPreview from './components/CommandsPreview'
import FAQ from './components/FAQ'
import Footer from './components/Footer'
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
      <Navbar activeSection={activeSection} />
      
      {/* PANEL 1: Hero */}
      <Hero />

      {/* PANEL 2: Features */}
      <Features />

      {/* PANEL 3: Commands */}
      <CommandsPreview />

      {/* PANEL 4: FAQ */}
      <FAQ />

      {/* PANEL 5: Footer & CTA */}
      <Footer />
      
    </div>
  )
}

export default App
