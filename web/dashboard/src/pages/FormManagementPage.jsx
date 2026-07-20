import React, { useState, useEffect, useContext } from 'react';
import { FileText, Plus, Trash2, Send, Edit, Save, X, Server, Hash, Shield, Settings } from 'lucide-react';
import { motion } from 'framer-motion';
import { GuildContext } from '../GuildContext';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const FormManagementPage = () => {
  const { activeGuildId, guildPermission } = useContext(GuildContext);
  const [forms, setForms] = useState([]);
  const [channels, setChannels] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [formError, setFormError] = useState("");
  const [isSummonModalOpen, setIsSummonModalOpen] = useState(false);
  const [activeForm, setActiveForm] = useState(null);
  
  const [formData, setFormData] = useState({
    form_id: '',
    title: '',
    channel_id: '',
    form_type: 1,
    action_target: '',
    auto_approve: 1,
    questions: [''],
    roles: []
  });
  const [summonChannel, setSummonChannel] = useState('');

  useEffect(() => {
    if (activeGuildId) {
      fetchData();
    }
  }, [activeGuildId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [formsRes, channelsRes, rolesRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/forms/${activeGuildId}`),
        axios.get(`${API_BASE_URL}/discord-channels/${activeGuildId}`),
        axios.get(`${API_BASE_URL}/discord-roles/${activeGuildId}`)
      ]);
      setForms(formsRes.data);
      setChannels(channelsRes.data.channels || []);
      setRoles(rolesRes.data.roles || []);
    } catch (error) {
      console.error("Error fetching form data", error);
    }
    setLoading(false);
  };

  const handleCreateForm = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.form_id || !formData.title || !formData.channel_id) {
      setFormError("Lütfen Form ID, Başlık ve Hedef Kanal alanlarını doldurun.");
      return;
    }
    try {
      // Filter out empty questions
      const cleanedData = {
         ...formData,
         questions: formData.questions.filter(q => q.trim() !== '')
      };
      if (isEditing) {
        await axios.put(`${API_BASE_URL}/forms/${activeGuildId}/${formData.form_id}`, cleanedData);
      } else {
        await axios.post(`${API_BASE_URL}/forms/${activeGuildId}`, cleanedData);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) {
      setFormError("Form kaydedilemedi: " + (error.response?.data?.detail || error.message));
    }
  };

  const openEditModal = (form) => {
    setFormData({
      form_id: form.form_id,
      title: form.title,
      channel_id: form.channel_id,
      form_type: form.form_type,
      action_target: form.action_target || '',
      auto_approve: form.auto_approve || 1,
      questions: form.questions && form.questions.length > 0 ? form.questions : [''],
      roles: form.roles || []
    });
    setFormError("");
    setIsEditing(true);
    setIsModalOpen(true);
  };

  const handleDelete = async (form_id) => {
    if (window.confirm(`${form_id} formunu silmek istediğinize emin misiniz?`)) {
      try {
        await axios.delete(`${API_BASE_URL}/forms/${activeGuildId}/${form_id}`);
        fetchData();
      } catch (err) {
        alert("Silinirken hata oluştu.");
      }
    }
  };

  const openSummon = (form) => {
    setActiveForm(form);
    setIsSummonModalOpen(true);
    setSummonChannel('');
  };

  const handleSummon = async () => {
    if (!summonChannel) {
        alert("Lütfen formun gönderileceği kanalı seçin.");
        return;
    }
    try {
      await axios.post(`${API_BASE_URL}/forms/${activeGuildId}/${activeForm.form_id}/summon`, { target_channel_id: summonChannel });
      setIsSummonModalOpen(false);
      alert("Form başarıyla kanala gönderildi!");
    } catch (error) {
      alert("Gönderim başarısız: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleQuestionChange = (index, value) => {
    const newQ = [...formData.questions];
    newQ[index] = value;
    setFormData({ ...formData, questions: newQ });
  };
  const addQuestion = () => setFormData({ ...formData, questions: [...formData.questions, ''] });
  const removeQuestion = (index) => {
    const newQ = formData.questions.filter((_, i) => i !== index);
    setFormData({ ...formData, questions: newQ });
  };

  const handleRoleToggle = (roleId) => {
      let newRoles = [...formData.roles];
      if (newRoles.includes(roleId)) newRoles = newRoles.filter(r => r !== roleId);
      else if (newRoles.length < 25) newRoles.push(roleId);
      setFormData({ ...formData, roles: newRoles });
  };

  const getFormTypeName = (type) => {
    if (type === 1) return "Normal Başvuru Formu";
    if (type === 2) return "Rol Seçimli Form";
    if (type === 4) return "Otomatik Yayın Formu";
    return "Bilinmeyen Tip";
  };

  return (
    <div style={{ padding: '32px', height: '100%', overflowY: 'auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <FileText size={32} color="var(--accent-blue)" /> Form Yönetimi
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>Sunucunuz için başvuru, kayıt veya itiraf formları oluşturun ve yönetin.</p>
        </div>
        {(guildPermission === 'owner' || guildPermission === 'write') && (
          <button 
            className="action-btn"
            style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--accent-blue)', color: '#fff', padding: '10px 20px', borderRadius: '12px', border: 'none', fontWeight: 600, cursor: 'pointer' }}
            onClick={() => {
              setFormData({ form_id: '', title: '', channel_id: '', form_type: 1, action_target: '', auto_approve: 1, questions: [''], roles: [] });
              setIsEditing(false);
              setIsModalOpen(true);
            }}
          >
            <Plus size={18} /> Yeni Form Oluştur
          </button>
        )}
      </header>

      {loading ? (
        <div style={{ color: 'var(--text-secondary)' }}>Yükleniyor...</div>
      ) : forms.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', borderRadius: '16px' }}>
          <FileText size={48} color="var(--text-muted)" style={{ marginBottom: '16px', opacity: 0.5 }} />
          <h3 style={{ color: '#fff', fontSize: '1.25rem', marginBottom: '8px' }}>Henüz Form Yok</h3>
          <p style={{ color: 'var(--text-secondary)' }}>Yukarıdaki butonu kullanarak yeni bir form oluşturabilirsiniz.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '24px' }}>
          {forms.map(form => (
            <motion.div key={form.form_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel" style={{ padding: '24px', borderRadius: '16px', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <h3 style={{ color: '#fff', fontSize: '1.25rem', margin: 0, fontWeight: 700 }}>{form.title}</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {(guildPermission === 'owner' || guildPermission === 'write') && (
                    <button
                      onClick={() => openEditModal(form)}
                      style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--accent-blue)'}
                      onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
                      title="Ayarları Düzenle"
                    >
                      <Settings size={18} />
                    </button>
                  )}
                  <span style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.1)', padding: '4px 8px', borderRadius: '6px', color: 'var(--text-secondary)' }}>ID: {form.form_id}</span>
                </div>
              </div>
              
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px', flex: 1 }}>
                <p style={{ marginBottom: '4px' }}><strong>Tip:</strong> {getFormTypeName(form.form_type)}</p>
                <p style={{ marginBottom: '4px' }}><strong>Soru Sayısı:</strong> {form.questions?.length || 0}</p>
                <p style={{ marginBottom: '0' }}><strong>Hedef Kanal:</strong> {form.channel_id === "0" ? "Log Yok (Sadece DB)" : (channels.find(c => c.channel_id === form.channel_id)?.channel_name || form.channel_id)}</p>
              </div>
              
              <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                <button 
                  onClick={() => openSummon(form)}
                  style={{ flex: 1, background: 'rgba(16, 185, 129, 0.15)', color: 'var(--accent-green)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '10px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontWeight: 600, transition: 'all 0.2s' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.25)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)'}
                >
                  <Send size={16} /> Gönder (Summon)
                </button>
                {(guildPermission === 'owner' || guildPermission === 'write') && (
                  <button 
                    onClick={() => handleDelete(form.form_id)}
                    style={{ background: 'rgba(239, 68, 68, 0.15)', color: 'var(--accent-red)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '10px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'}
                    title="Formu Sil"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* --- FORM CREATE MODAL --- */}
      {isModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'var(--panel-bg)', width: '600px', maxWidth: '90%', borderRadius: '16px', border: '1px solid var(--panel-border)', display: 'flex', flexDirection: 'column', maxHeight: '90vh' }}>
            <div style={{ padding: '24px', borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.4rem', color: '#fff' }}>{isEditing ? 'Formu Düzenle' : 'Yeni Form Oluştur'}</h2>
              <button onClick={() => setIsModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <X size={24} />
              </button>
            </div>
            
            <form onSubmit={handleCreateForm} style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {formError && (
                <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#ef4444', borderRadius: '8px', fontSize: '0.9rem' }}>
                  {formError}
                </div>
              )}
              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Form ID (Benzersiz)</label>
                  <input type="text" required disabled={isEditing} value={formData.form_id} onChange={e => setFormData({...formData, form_id: e.target.value.replace(/[^a-zA-Z0-9_-]/g, '')})} placeholder="orn-basvuru-1" style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: isEditing ? 'var(--text-muted)' : '#fff', borderRadius: '8px', outline: 'none' }} />
                </div>
                <div style={{ flex: 2 }}>
                  <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Başlık</label>
                  <input type="text" required value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} placeholder="Moderatör Başvurusu" style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }} />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Form Tipi</label>
                <select value={formData.form_type} onChange={e => setFormData({...formData, form_type: parseInt(e.target.value), roles: []})} style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }}>
                  <option value={1}>Normal Başvuru / Sadece Log (Onay/Ret sistemi)</option>
                  <option value={2}>Rol Seçimli Form (Onayda rol verir)</option>
                  <option value={4}>Otomatik Yayın Formu (İtiraf sistemi vb.)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>
                  Sonuç / Log Kanalı <span style={{color: 'var(--text-muted)'}}>(Doldurulan form nereye düşecek?)</span>
                </label>
                <select required value={formData.channel_id} onChange={e => setFormData({...formData, channel_id: e.target.value})} style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }}>
                  <option value="">-- Kanal Seç --</option>
                  <option value="0">Log İstemiyorum (Sadece DB/Web Panel)</option>
                  {channels.map(c => <option key={c.channel_id} value={c.channel_id}># {c.channel_name}</option>)}
                </select>
              </div>

              {formData.form_type === 4 && (
                <div>
                  <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Yayın Kanalı (Kullanıcı gönderdiğinde nerede paylaşılsın?)</label>
                  <select required value={formData.action_target} onChange={e => setFormData({...formData, action_target: e.target.value})} style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none', marginBottom: '12px' }}>
                    <option value="">-- Kanal Seç --</option>
                    {channels.map(c => <option key={c.channel_id} value={c.channel_id}># {c.channel_name}</option>)}
                  </select>
                  
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem', cursor: 'pointer' }}>
                    <input 
                      type="checkbox" 
                      checked={formData.auto_approve === 1}
                      onChange={e => setFormData({...formData, auto_approve: e.target.checked ? 1 : 0})}
                      style={{ width: '16px', height: '16px', accentColor: 'var(--accent-blue)' }}
                    />
                    İtirafları Otomatik Onayla (Kapatılırsa admin onayı gerekir)
                  </label>
                </div>
              )}

              {formData.form_type === 2 && (
                <div>
                  <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Seçilebilecek Roller (Max 25)</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', maxHeight: '120px', overflowY: 'auto', padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
                    {roles.map(r => (
                      <div key={r.id} onClick={() => handleRoleToggle(r.id)} style={{ padding: '6px 12px', background: formData.roles.includes(r.id) ? 'var(--accent-blue)' : 'rgba(255,255,255,0.05)', color: formData.roles.includes(r.id) ? '#fff' : 'var(--text-secondary)', borderRadius: '16px', fontSize: '0.8rem', cursor: 'pointer', border: `1px solid ${formData.roles.includes(r.id) ? 'transparent' : 'rgba(255,255,255,0.1)'}` }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                           <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: r.color || '#99aab5' }} />
                           {r.name}
                        </div>
                      </div>
                    ))}
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem', cursor: 'pointer', marginTop: '12px' }}>
                    <input 
                      type="checkbox" 
                      checked={formData.auto_approve === 1}
                      onChange={e => setFormData({...formData, auto_approve: e.target.checked ? 1 : 0})}
                      style={{ width: '16px', height: '16px', accentColor: 'var(--accent-blue)' }}
                    />
                    Rolü Otomatik Ver (Kapatılırsa admin onayı gerekir)
                  </label>
                </div>
              )}

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Sorular (Max 5)</label>
                  {formData.questions.length < 5 && (
                    <button type="button" onClick={addQuestion} style={{ background: 'none', border: 'none', color: 'var(--accent-green)', fontSize: '0.85rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Plus size={14} /> Soru Ekle
                    </button>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {formData.questions.map((q, index) => (
                    <div key={index} style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" 
                        required 
                        value={q} 
                        onChange={e => handleQuestionChange(index, e.target.value)} 
                        placeholder={`${index + 1}. Soruyu girin...`} 
                        style={{ flex: 1, padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }} 
                      />
                      {formData.questions.length > 1 && (
                        <button type="button" onClick={() => removeQuestion(index)} style={{ padding: '10px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-red)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', cursor: 'pointer' }}>
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '12px', borderTop: '1px solid var(--panel-border)', paddingTop: '24px' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} style={{ padding: '10px 20px', background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--panel-border)', borderRadius: '8px', cursor: 'pointer' }}>
                  İptal
                </button>
                <button type="submit" style={{ padding: '10px 20px', background: 'var(--accent-blue)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}>
                  {isEditing ? 'Kaydet' : 'Oluştur'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* --- SUMMON MODAL --- */}
      {isSummonModalOpen && activeForm && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass-panel" style={{ width: '400px', maxWidth: '90%', padding: '24px', borderRadius: '16px' }}>
            <h2 style={{ margin: '0 0 16px 0', fontSize: '1.25rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Send size={20} color="var(--accent-green)" /> Formu Discord'a Gönder
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
              <strong>{activeForm.title}</strong> isimli formu kullanıcıların doldurabilmesi için bir kanala mesaj ve buton olarak göndereceksiniz.
            </p>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '8px' }}>Hangi Kanala Gönderilsin?</label>
              <select value={summonChannel} onChange={e => setSummonChannel(e.target.value)} style={{ width: '100%', padding: '10px 12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '8px', outline: 'none' }}>
                <option value="">-- Kanal Seç --</option>
                {channels.map(c => <option key={c.channel_id} value={c.channel_id}># {c.channel_name}</option>)}
              </select>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button type="button" onClick={() => setIsSummonModalOpen(false)} style={{ padding: '8px 16px', background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--panel-border)', borderRadius: '8px', cursor: 'pointer' }}>
                İptal
              </button>
              <button type="button" onClick={handleSummon} disabled={!summonChannel} style={{ padding: '8px 16px', background: 'var(--accent-green)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: summonChannel ? 'pointer' : 'not-allowed', opacity: summonChannel ? 1 : 0.5 }}>
                Şimdi Gönder
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default FormManagementPage;
