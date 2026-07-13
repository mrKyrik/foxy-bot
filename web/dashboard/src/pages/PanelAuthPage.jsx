import React, { useState, useEffect, useContext, useRef } from 'react';
import { Shield, Plus, Trash2, User, Users, AlertTriangle, ChevronDown, Check, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { GuildContext } from '../GuildContext';

// --- Custom Select Component with Search ---
const SearchableSelect = ({ items, type, value, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredItems = items.filter(item => {
    const name = type === 'role' ? item.name : item.username;
    return name.toLowerCase().includes(query.toLowerCase());
  });

  const selectedItem = items.find(i => i.id === value);

  return (
    <div ref={wrapperRef} className="relative w-full">
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-gray-900/50 backdrop-blur-md border border-gray-600/50 rounded-xl p-3 flex justify-between items-center cursor-pointer hover:border-kumiho-primary/50 transition-colors"
      >
        <span className={selectedItem ? "text-white" : "text-gray-400"}>
          {selectedItem 
            ? (type === 'role' ? selectedItem.name : selectedItem.username) 
            : placeholder}
        </span>
        <ChevronDown size={18} className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute z-50 w-full mt-2 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden"
          >
            <div className="p-2 border-b border-gray-700 flex items-center">
              <Search size={16} className="text-gray-400 mr-2" />
              <input 
                type="text" 
                autoFocus
                placeholder="Ara..." 
                value={query}
                onChange={e => setQuery(e.target.value)}
                className="w-full bg-transparent border-none outline-none text-white text-sm"
              />
            </div>
            <div className="max-h-60 overflow-y-auto">
              {filteredItems.length === 0 ? (
                <div className="p-3 text-sm text-gray-400 text-center">Sonuç bulunamadı.</div>
              ) : (
                filteredItems.map(item => (
                  <div 
                    key={item.id}
                    onClick={() => {
                      onChange(item.id);
                      setIsOpen(false);
                      setQuery('');
                    }}
                    className="p-3 hover:bg-gray-700/50 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {type === 'user' ? (
                        <img 
                          src={item.avatar ? `https://cdn.discordapp.com/avatars/${item.id}/${item.avatar}.png` : 'https://cdn.discordapp.com/embed/avatars/0.png'} 
                          alt="avatar" 
                          className="w-6 h-6 rounded-full"
                        />
                      ) : (
                        <div 
                          className="w-4 h-4 rounded-full" 
                          style={{ backgroundColor: item.color ? `#${item.color.toString(16).padStart(6, '0')}` : '#99aab5' }}
                        />
                      )}
                      <span className="text-white text-sm">{type === 'role' ? item.name : item.username}</span>
                    </div>
                    {value === item.id && <Check size={16} className="text-kumiho-primary" />}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const PanelAuthPage = () => {
  const { activeGuildId, guildPermission } = useContext(GuildContext);
  const [permissions, setPermissions] = useState([]);
  const [discordRoles, setDiscordRoles] = useState([]);
  const [discordMembers, setDiscordMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [newTargetId, setNewTargetId] = useState('');
  const [newTargetType, setNewTargetType] = useState('role');
  const [newPermission, setNewPermission] = useState('read');

  useEffect(() => {
    if (activeGuildId && guildPermission === 'owner') {
      fetchData();
    } else if (guildPermission !== 'owner') {
      setLoading(false);
      setError("Bu sayfayı görüntülemek için Sunucu Sahibi (Owner) yetkisine sahip olmalısınız.");
    }
  }, [activeGuildId, guildPermission]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [authRes, rolesRes, membersRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/panel_auth/${activeGuildId}`),
        axios.get(`${API_BASE_URL}/discord-roles/${activeGuildId}`),
        axios.get(`${API_BASE_URL}/discord-members/${activeGuildId}`)
      ]);
      setPermissions(authRes.data.permissions || []);
      setDiscordRoles(rolesRes.data || []);
      setDiscordMembers(membersRes.data || []);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Veriler yüklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddPermission = async (e) => {
    e.preventDefault();
    if (!newTargetId) return;

    try {
      await axios.post(`${API_BASE_URL}/panel_auth/${activeGuildId}`, {
        target_id: newTargetId,
        target_type: newTargetType,
        permission_level: newPermission
      });
      setNewTargetId('');
      fetchData();
    } catch (err) {
      console.error(err);
      alert("Yetki eklenirken hata oluştu.");
    }
  };

  const handleDelete = async (targetId) => {
    if (!window.confirm("Bu yetkiyi silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(`${API_BASE_URL}/panel_auth/${activeGuildId}/${targetId}`);
      fetchData();
    } catch (err) {
      console.error(err);
      alert("Yetki silinirken hata oluştu.");
    }
  };

  const handlePermissionChange = async (targetId, targetType, newLevel) => {
    try {
      await axios.post(`${API_BASE_URL}/panel_auth/${activeGuildId}`, {
        target_id: targetId,
        target_type: targetType,
        permission_level: newLevel
      });
      fetchData();
    } catch (err) {
      console.error(err);
      alert("Yetki güncellenirken hata oluştu.");
    }
  };

  const getEntityName = (id, type) => {
    if (type === 'role') {
      const r = discordRoles.find(r => r.id === id);
      return r ? r.name : id;
    } else {
      const u = discordMembers.find(m => m.id === id);
      return u ? u.username : id;
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="w-12 h-12 border-4 border-kumiho-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 h-full flex flex-col items-center justify-center">
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-red-500/10 border border-red-500/20 p-8 rounded-2xl flex flex-col items-center max-w-lg text-center"
        >
          <AlertTriangle size={64} className="text-red-400 mb-6" />
          <h2 className="text-2xl font-bold text-white mb-2">Erişim Engellendi</h2>
          <p className="text-gray-400">{error}</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto w-full">
      <motion.div 
        initial={{ y: -20, opacity: 0 }} 
        animate={{ y: 0, opacity: 1 }}
        className="mb-10"
      >
        <h1 className="text-4xl font-bold flex items-center mb-4 text-white">
          <Shield className="mr-4 text-kumiho-primary drop-shadow-[0_0_15px_rgba(234,88,12,0.5)]" size={36} />
          Panel Yetkilendirme
        </h1>
        <p className="text-gray-400 text-lg leading-relaxed max-w-3xl">
          Kumiho Web Paneli'ne kimlerin erişebileceğini ve hangi düzeyde müdahale edebileceğini buradan güvenle yönetin.
        </p>
      </motion.div>

      {/* Ekleme Kartı */}
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="glass-panel p-8 mb-10 relative overflow-hidden group"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-kumiho-primary to-orange-400 opacity-80" />
        
        <h2 className="text-xl font-semibold mb-6 text-white flex items-center">
          <Plus size={20} className="mr-2 text-kumiho-primary" />
          Yeni Yetki Kuralı Oluştur
        </h2>
        
        <form onSubmit={handleAddPermission} className="grid grid-cols-1 md:grid-cols-12 gap-6 items-end">
          <div className="md:col-span-3">
            <label className="block text-sm font-medium text-gray-400 mb-2">Hedef Türü</label>
            <div className="relative">
              <select 
                value={newTargetType} 
                onChange={e => { setNewTargetType(e.target.value); setNewTargetId(''); }}
                className="w-full bg-gray-900/50 backdrop-blur-md border border-gray-600/50 rounded-xl p-3 text-white appearance-none focus:border-kumiho-primary focus:ring-1 focus:ring-kumiho-primary outline-none transition-all cursor-pointer"
              >
                <option value="role">Discord Rolü</option>
                <option value="user">Discord Kullanıcısı</option>
              </select>
              <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>

          <div className="md:col-span-4 z-20">
            <label className="block text-sm font-medium text-gray-400 mb-2">
              {newTargetType === 'role' ? 'Rol Seçin' : 'Kullanıcı Seçin'}
            </label>
            <SearchableSelect 
              type={newTargetType}
              items={newTargetType === 'role' ? discordRoles : discordMembers}
              value={newTargetId}
              onChange={setNewTargetId}
              placeholder="Seçim yapın..."
            />
          </div>

          <div className="md:col-span-3">
            <label className="block text-sm font-medium text-gray-400 mb-2">Yetki Seviyesi</label>
            <div className="relative">
              <select 
                value={newPermission} 
                onChange={e => setNewPermission(e.target.value)}
                className="w-full bg-gray-900/50 backdrop-blur-md border border-gray-600/50 rounded-xl p-3 text-white appearance-none focus:border-kumiho-primary focus:ring-1 focus:ring-kumiho-primary outline-none transition-all cursor-pointer"
              >
                <option value="read">👁️ Sadece Oku</option>
                <option value="write">✍️ Düzenleme Yetkisi</option>
              </select>
              <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>

          <div className="md:col-span-2">
            <button 
              type="submit"
              disabled={!newTargetId}
              className="w-full bg-kumiho-primary hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-[0_0_15px_rgba(234,88,12,0.3)] hover:shadow-[0_0_25px_rgba(234,88,12,0.5)] flex justify-center items-center h-[46px]"
            >
              <Plus size={18} className="mr-2" />
              Ekle
            </button>
          </div>
        </form>
      </motion.div>

      {/* Yetki Listesi */}
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="glass-panel overflow-hidden"
      >
        <div className="p-6 border-b border-gray-700/50 bg-gray-800/30 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-white">Mevcut İzinler</h3>
          <span className="bg-gray-800 text-gray-300 text-xs py-1 px-3 rounded-full border border-gray-700">
            {permissions.length} Kural
          </span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-900/40 text-gray-400 text-xs uppercase tracking-wider">
                <th className="py-4 px-6 font-medium">Hedef</th>
                <th className="py-4 px-6 font-medium">Tür</th>
                <th className="py-4 px-6 font-medium">Yetki Seviyesi</th>
                <th className="py-4 px-6 font-medium text-right">İşlem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              <AnimatePresence>
                {permissions.length === 0 ? (
                  <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <td colSpan="4" className="py-12 text-center text-gray-500">
                      <div className="flex flex-col items-center justify-center">
                        <Shield size={48} className="mb-4 opacity-20" />
                        <p className="text-base">Henüz özel bir yetki kuralı eklenmemiş.</p>
                        <p className="text-sm mt-1">Sunucu sahibi haricindeki diğer yöneticiler varsayılan olarak "Sadece Oku" yetkisiyle paneli görür.</p>
                      </div>
                    </td>
                  </motion.tr>
                ) : (
                  permissions.map((p, index) => (
                    <motion.tr 
                      key={`${p.target_type}-${p.target_id}`}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-gray-800/40 transition-colors group"
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center border border-gray-700">
                            {p.target_type === 'role' ? <Users size={16} className="text-blue-400" /> : <User size={16} className="text-green-400" />}
                          </div>
                          <div>
                            <p className="text-white font-medium">{getEntityName(p.target_id, p.target_type)}</p>
                            <p className="text-xs text-gray-500 font-mono">{p.target_id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${p.target_type === 'role' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-green-500/10 text-green-400 border-green-500/20'}`}>
                          {p.target_type === 'role' ? 'Discord Rolü' : 'Kullanıcı'}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <div className="relative inline-block w-48">
                          <select 
                            value={p.permission_level}
                            onChange={e => handlePermissionChange(p.target_id, p.target_type, e.target.value)}
                            className={`w-full appearance-none bg-transparent border-b ${p.permission_level === 'write' ? 'border-orange-500/50 text-orange-400 focus:border-orange-500' : 'border-gray-600 text-gray-300 focus:border-gray-400'} py-1.5 pr-8 outline-none transition-colors cursor-pointer font-medium`}
                          >
                            <option value="read" className="bg-gray-900 text-white">👁️ Sadece Oku</option>
                            <option value="write" className="bg-gray-900 text-white">✍️ Düzenleme Yetkisi</option>
                          </select>
                          <ChevronDown size={14} className="absolute right-0 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <button 
                          onClick={() => handleDelete(p.target_id)}
                          className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 outline-none"
                          title="Yetkiyi Kaldır"
                        >
                          <Trash2 size={18} />
                        </button>
                      </td>
                    </motion.tr>
                  ))
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
        <div className="p-4 bg-gray-900/50 border-t border-gray-700/50 text-sm text-gray-400 flex items-start gap-2">
          <Shield size={16} className="text-kumiho-primary shrink-0 mt-0.5" />
          <p>
            <strong>Not:</strong> Sunucu Sahibi (Owner) ve Bot Geliştiricisi her zaman <strong>Tam Yetki'ye</strong> sahiptir ve tüm sınırlandırmalardan muaftır. Bu kişileri tabloya eklemenize gerek yoktur.
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default PanelAuthPage;
