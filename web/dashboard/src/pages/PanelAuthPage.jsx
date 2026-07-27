import React, { useState, useEffect, useContext, useRef } from "react";
import { Shield, Plus, Trash2, User, Users, AlertTriangle, ChevronDown, Check, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API_BASE_URL } from "../config";
import { GuildContext } from "../GuildContext";

// --- Custom Select Component ---
const SearchableSelect = ({ items, type, value, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredItems = items.filter((item) => {
    const name = type === "role" ? item.name : item.username;
    return name.toLowerCase().includes(query.toLowerCase());
  });

  const selectedItem = items.find((i) => i.id === value);

  return (
    <div ref={wrapperRef} style={{ position: 'relative', width: '100%' }}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          background: 'rgba(0,0,0,0.2)',
          border: '1px solid var(--panel-border)',
          borderRadius: '8px',
          padding: '10px 12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer'
        }}
      >
        <span style={{ color: selectedItem ? '#fff' : 'var(--text-muted)' }}>
          {selectedItem
            ? type === "role"
              ? selectedItem.name
              : selectedItem.username
            : placeholder}
        </span>
        <ChevronDown size={18} style={{ color: 'var(--text-secondary)', transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            style={{
              position: 'absolute',
              zIndex: 50,
              width: '100%',
              marginTop: '8px',
              background: 'var(--panel-bg)',
              border: '1px solid var(--panel-border)',
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
            }}
          >
            <div style={{ padding: '8px', borderBottom: '1px solid var(--panel-border)', display: 'flex', alignItems: 'center' }}>
              <Search size={16} style={{ color: 'var(--text-secondary)', marginRight: '8px' }} />
              <input
                type="text"
                autoFocus
                placeholder="Ara..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ width: '100%', background: 'transparent', border: 'none', outline: 'none', color: '#fff', fontSize: '0.9rem' }}
              />
            </div>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {filteredItems.length === 0 ? (
                <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Sonuç bulunamadı.</div>
              ) : (
                filteredItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      onChange(item.id);
                      setIsOpen(false);
                      setQuery("");
                    }}
                    style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.02)' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {type === "user" ? (
                        <img
                          src={
                            item.avatar
                              ? `https://cdn.discordapp.com/avatars/${item.id}/${item.avatar}.png`
                              : "https://cdn.discordapp.com/embed/avatars/0.png"
                          }
                          alt="avatar"
                          style={{ width: '24px', height: '24px', borderRadius: '50%' }}
                        />
                      ) : (
                        <div
                          style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            backgroundColor: item.color
                              ? `#${item.color.toString(16).padStart(6, "0")}`
                              : "#99aab5",
                          }}
                        />
                      )}
                      <span style={{ color: '#fff', fontSize: '0.9rem' }}>
                        {type === "role" ? item.name : item.username}
                      </span>
                    </div>
                    {value === item.id && <Check size={16} color="var(--color-cyan)" />}
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

  const [newTargetId, setNewTargetId] = useState("");
  const [newTargetType, setNewTargetType] = useState("role");
  const [newPermission, setNewPermission] = useState("read");

  useEffect(() => {
    if (activeGuildId && guildPermission === "owner") {
      fetchData();
    } else if (guildPermission !== "owner") {
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
        axios.get(`${API_BASE_URL}/discord-members/${activeGuildId}`),
      ]);
      setPermissions(authRes.data.permissions || []);
      setDiscordRoles(Array.isArray(rolesRes.data) ? rolesRes.data : []);
      setDiscordMembers(Array.isArray(membersRes.data) ? membersRes.data : []);
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
        permission_level: newPermission,
      });
      setNewTargetId("");
      fetchData();
    } catch (err) {
      console.error(err);
      alert("Yetki eklenirken hata oluştu.");
    }
  };

  const handleDelete = async (targetId) => {
    if (!window.confirm("Bu yetkiyi silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(
        `${API_BASE_URL}/panel_auth/${activeGuildId}/${targetId}`,
      );
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
        permission_level: newLevel,
      });
      fetchData();
    } catch (err) {
      console.error(err);
      alert("Yetki güncellenirken hata oluştu.");
    }
  };

  const getEntityName = (id, type) => {
    if (type === "role") {
      const r = discordRoles.find((r) => r.id === id);
      return r ? r.name : id;
    } else {
      const u = discordMembers.find((m) => m.id === id);
      return u ? u.username : id;
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '32px', color: 'var(--text-secondary)' }}>Yükleniyor...</div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '32px', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="glass-panel"
          style={{ padding: '48px', textAlign: 'center', borderRadius: '16px', maxWidth: '400px' }}
        >
          <AlertTriangle size={64} style={{ color: 'var(--accent-red)', marginBottom: '24px', opacity: 0.8 }} />
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fff', marginBottom: '12px' }}>Erişim Engellendi</h2>
          <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div style={{ padding: '32px', height: '100%', overflowY: 'auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Shield size={32} color="var(--accent-orange)" /> Panel Yetkilendirme
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
            Kumiho Web Paneli'ne kimlerin erişebileceğini ve hangi düzeyde müdahale edebileceğini buradan güvenle yönetin.
          </p>
        </div>
      </header>

      {/* Ekleme Kartı */}
      <motion.div
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="glass-panel"
        style={{ padding: '24px', borderRadius: '16px', marginBottom: '32px', borderTop: '2px solid var(--accent-orange)' }}
      >
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
          <Plus size={20} color="var(--accent-orange)" /> Yeni Yetki Kuralı Oluştur
        </h2>

        <form onSubmit={handleAddPermission} style={{ display: 'flex', gap: '20px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 200px' }}>
            <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Hedef Türü</label>
            <select
              value={newTargetType}
              onChange={(e) => {
                setNewTargetType(e.target.value);
                setNewTargetId("");
              }}
              style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }}
            >
              <option value="role">Discord Rolü</option>
              <option value="user">Discord Kullanıcısı</option>
            </select>
          </div>

          <div style={{ flex: '2 1 300px' }}>
            <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>
              {newTargetType === "role" ? "Rol Seçin" : "Kullanıcı Seçin"}
            </label>
            <SearchableSelect
              type={newTargetType}
              items={newTargetType === "role" ? discordRoles : discordMembers}
              value={newTargetId}
              onChange={setNewTargetId}
              placeholder="Seçim yapın..."
            />
          </div>

          <div style={{ flex: '1 1 200px' }}>
            <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Yetki Seviyesi</label>
            <select
              value={newPermission}
              onChange={(e) => setNewPermission(e.target.value)}
              style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }}
            >
              <option value="read">👁️ Sadece Oku</option>
              <option value="write">✍️ Düzenleme Yetkisi</option>
            </select>
          </div>

          <div style={{ flex: '0 0 auto' }}>
            <button
              type="submit"
              disabled={!newTargetId}
              style={{ 
                background: 'var(--accent-orange)', 
                color: '#fff', 
                border: 'none', 
                padding: '10px 24px', 
                borderRadius: '8px', 
                fontWeight: 600, 
                cursor: newTargetId ? 'pointer' : 'not-allowed',
                opacity: newTargetId ? 1 : 0.5,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                height: '42px'
              }}
            >
              <Plus size={18} /> Ekle
            </button>
          </div>
        </form>
      </motion.div>

      {/* Yetki Listesi */}
      <motion.div
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="glass-panel"
        style={{ borderRadius: '16px', overflow: 'hidden' }}
      >
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#fff', margin: 0 }}>Mevcut İzinler</h3>
          <span style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)', fontSize: '0.8rem', padding: '4px 10px', borderRadius: '99px', border: '1px solid rgba(255,255,255,0.1)' }}>
            {permissions.length} Kural
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid var(--panel-border)' }}>
                <th style={{ padding: '16px 24px', fontWeight: 500 }}>Hedef</th>
                <th style={{ padding: '16px 24px', fontWeight: 500 }}>Tür</th>
                <th style={{ padding: '16px 24px', fontWeight: 500 }}>Yetki Seviyesi</th>
                <th style={{ padding: '16px 24px', fontWeight: 500, textAlign: 'right' }}>İşlem</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {permissions.length === 0 ? (
                  <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <td colSpan="4" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <Shield size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                      <p>Henüz özel bir yetki kuralı eklenmemiş.</p>
                      <p style={{ fontSize: '0.85rem', marginTop: '8px' }}>Sunucu sahibi haricindeki diğer yöneticiler varsayılan olarak "Sadece Oku" yetkisiyle paneli görür.</p>
                    </td>
                  </motion.tr>
                ) : (
                  permissions.map((p, index) => (
                    <motion.tr
                      key={`${p.target_type}-${p.target_id}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}
                    >
                      <td style={{ padding: '16px 24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {p.target_type === "role" ? <Users size={18} color="var(--accent-blue)" /> : <User size={18} color="var(--accent-green)" />}
                          </div>
                          <div>
                            <div style={{ color: '#fff', fontWeight: 500 }}>{getEntityName(p.target_id, p.target_type)}</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontFamily: 'monospace' }}>{p.target_id}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px' }}>
                        <span style={{ 
                          padding: '4px 10px', 
                          borderRadius: '99px', 
                          fontSize: '0.75rem', 
                          fontWeight: 600,
                          background: p.target_type === "role" ? 'rgba(59, 130, 246, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                          color: p.target_type === "role" ? 'var(--accent-blue)' : 'var(--accent-green)',
                          border: `1px solid ${p.target_type === "role" ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`
                        }}>
                          {p.target_type === "role" ? "Discord Rolü" : "Kullanıcı"}
                        </span>
                      </td>
                      <td style={{ padding: '16px 24px' }}>
                        <select
                          value={p.permission_level}
                          onChange={(e) => handlePermissionChange(p.target_id, p.target_type, e.target.value)}
                          style={{ 
                            background: 'transparent', 
                            border: 'none', 
                            color: p.permission_level === "write" ? 'var(--accent-orange)' : 'var(--text-secondary)',
                            fontWeight: p.permission_level === "write" ? 600 : 500,
                            outline: 'none',
                            cursor: 'pointer'
                          }}
                        >
                          <option value="read" style={{ background: 'var(--bg-color)', color: '#fff' }}>👁️ Sadece Oku</option>
                          <option value="write" style={{ background: 'var(--bg-color)', color: '#fff' }}>✍️ Düzenleme Yetkisi</option>
                        </select>
                      </td>
                      <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                        <button
                          onClick={() => handleDelete(p.target_id)}
                          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '8px' }}
                          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent-red)'; e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.borderRadius = '8px'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
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
        <div style={{ padding: '16px 24px', background: 'rgba(0,0,0,0.1)', borderTop: '1px solid var(--panel-border)', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={16} color="var(--accent-orange)" />
          <span><strong>Not:</strong> Sunucu Sahibi (Owner) her zaman <strong>Tam Yetki'ye</strong> sahiptir ve tablodan bağımsızdır.</span>
        </div>
      </motion.div>
    </div>
  );
};

export default PanelAuthPage;
