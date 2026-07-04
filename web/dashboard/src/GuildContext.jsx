import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from './config';

export const GuildContext = createContext();

export const GuildProvider = ({ children }) => {
  const [guilds, setGuilds] = useState([]);
  const [activeGuildId, setActiveGuildId] = useState(localStorage.getItem('kumiho_active_guild') || null);

  useEffect(() => {
    const fetchGuilds = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/guilds`);
        if (res.data.guilds && res.data.guilds.length > 0) {
          setGuilds(res.data.guilds);
          if (!activeGuildId || !res.data.guilds.find(g => g.id === activeGuildId)) {
            setActiveGuildId(res.data.guilds[0].id);
            localStorage.setItem('kumiho_active_guild', res.data.guilds[0].id);
          }
        }
      } catch (error) {
        console.error("Guilds could not be fetched:", error);
      }
    };
    fetchGuilds();
  }, [activeGuildId]);

  const changeGuild = (id) => {
    setActiveGuildId(id);
    localStorage.setItem('kumiho_active_guild', id);
  };

  return (
    <GuildContext.Provider value={{ guilds, activeGuildId, changeGuild }}>
      {children}
    </GuildContext.Provider>
  );
};
