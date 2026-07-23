import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Cropper from 'react-cropper';
import 'cropperjs/dist/cropper.css';
import { Upload, Check, AlertCircle, RefreshCw, Settings2, Eye, Sliders } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'https://kyrik.duckdns.org/api';

// --- Canvas Preview Renderer ---
const CARD_W = 900;
const CARD_H = 250;

function hexToRgb(hex) {
  const clean = hex.replace('#', '');
  const bigint = parseInt(clean.length === 3
    ? clean.split('').map(c => c + c).join('')
    : clean, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

function drawRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function renderPreview(canvas, bgImage, avatarUrl, opts) {
  const ctx = canvas.getContext('2d');
  const { barColor, borderColor, borderWidth, overlayOpacity, nameColor, username, level, rank, xp, needed } = opts;

  canvas.width = CARD_W;
  canvas.height = CARD_H;

  // Background
  if (bgImage) {
    ctx.drawImage(bgImage, 0, 0, CARD_W, CARD_H);
  } else {
    ctx.fillStyle = '#0F172A';
    ctx.fillRect(0, 0, CARD_W, CARD_H);
  }

  // Dark overlay
  ctx.fillStyle = `rgba(0,0,0,${overlayOpacity / 100})`;
  ctx.fillRect(0, 0, CARD_W, CARD_H);

  // Avatar circle clip
  const avSize = 180;
  const ax = 35, ay = (CARD_H - avSize) / 2;
  const cx = ax + avSize / 2, cy = ay + avSize / 2, radius = avSize / 2;

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.clip();
  if (avatarUrl) {
    try { ctx.drawImage(avatarUrl, ax, ay, avSize, avSize); } catch (e) { /* skip */ }
  } else {
    ctx.fillStyle = '#334155';
    ctx.fillRect(ax, ay, avSize, avSize);
  }
  ctx.restore();

  // Avatar border ring
  const bw = parseInt(borderWidth) || 6;
  ctx.strokeStyle = borderColor;
  ctx.lineWidth = bw;
  ctx.beginPath();
  ctx.arc(cx, cy, radius + bw / 2 + 1, 0, Math.PI * 2);
  ctx.stroke();

  // Name
  ctx.fillStyle = nameColor;
  ctx.font = `bold 57px "Segoe UI", Arial, sans-serif`;
  ctx.textBaseline = 'top';
  ctx.fillText(username || 'Kullanıcı', 250, 40);

  // Level | Rank (right-aligned)
  const lvlText = `Lvl ${level}  |  #${rank}`;
  ctx.fillStyle = barColor;
  ctx.font = `bold 45px "Segoe UI", Arial, sans-serif`;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'top';
  ctx.fillText(lvlText, CARD_W - 60, 40);
  ctx.textAlign = 'left';

  // XP bar background
  const bx = 250, by = 150, bWidth = 600, bHeight = 30, br = 15;
  ctx.fillStyle = 'rgba(30,41,59,0.9)';
  drawRoundRect(ctx, bx, by, bWidth, bHeight, br);
  ctx.fill();

  // XP bar fill
  const ratio = Math.min(Math.max(xp / (needed || 1), 0), 1);
  const fillW = Math.max(ratio * bWidth, 0);
  if (fillW > 0) {
    ctx.fillStyle = barColor;
    drawRoundRect(ctx, bx, by, fillW, bHeight, br);
    ctx.fill();
  }

  // XP text
  ctx.fillStyle = '#C8C8C8';
  ctx.font = `500 24px "Segoe UI", Arial, sans-serif`;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'bottom';
  ctx.fillText(`${xp} / ${needed} XP`, bx + bWidth, by - 4);
  ctx.textAlign = 'left';
}

// --- Color Picker Component ---
function ColorPicker({ label, value, onChange, icon }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
        {icon && <span>{icon}</span>}
        {label}
      </label>
      <div className="flex items-center gap-2">
        <div className="relative w-10 h-10 rounded-lg overflow-hidden border-2 border-white/10 shadow-inner flex-shrink-0">
          <input
            type="color"
            value={value}
            onChange={e => onChange(e.target.value)}
            className="absolute inset-0 w-[150%] h-[150%] -top-2 -left-2 cursor-pointer border-0 p-0 m-0 bg-transparent"
          />
        </div>
        <input
          type="text"
          value={value}
          onChange={e => { if (/^#[0-9a-fA-F]{0,6}$/.test(e.target.value)) onChange(e.target.value); }}
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-indigo-500/60 transition-colors"
          maxLength={7}
          placeholder="#000000"
        />
      </div>
    </div>
  );
}

// --- Slider Component ---
function SliderPicker({ label, value, onChange, min, max, unit, icon }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
        <span className="flex items-center gap-1.5">{icon && <span>{icon}</span>}{label}</span>
        <span className="text-indigo-400 font-bold">{value}{unit}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-full appearance-none cursor-pointer accent-indigo-500"
        style={{ background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${((value - min) / (max - min)) * 100}%, #ffffff1a ${((value - min) / (max - min)) * 100}%, #ffffff1a 100%)` }}
      />
    </div>
  );
}

// --- Main Component ---
const BannerUpload = () => {
  const { token } = useParams();
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [activeTab, setActiveTab] = useState('crop'); // 'crop' | 'customize'
  const cropperRef = useRef(null);
  const canvasRef = useRef(null);
  const bgImgRef = useRef(null);
  const avatarImgRef = useRef(null);
  const previewTimerRef = useRef(null);

  // Customization state
  const [barColor, setBarColor] = useState('#10B981');
  const [borderColor, setBorderColor] = useState('#00C8FF');
  const [borderWidth, setBorderWidth] = useState(6);
  const [overlayOpacity, setOverlayOpacity] = useState(60);
  const [nameColor, setNameColor] = useState('#FFFFFF');

  // --- Avatar fetch (Discord CDN placeholder) ---
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    // Generic avatar placeholder using DiceBear
    img.src = 'https://api.dicebear.com/7.x/bottts/svg?seed=preview&backgroundColor=0ea5e9';
    img.onload = () => { avatarImgRef.current = img; drawPreview(); };
  }, []);

  const drawPreview = useCallback(() => {
    if (!canvasRef.current) return;
    renderPreview(canvasRef.current, bgImgRef.current, avatarImgRef.current, {
      barColor, borderColor, borderWidth, overlayOpacity, nameColor,
      username: 'Kyrik', level: 16, rank: 2, xp: 1414, needed: 3700,
    });
  }, [barColor, borderColor, borderWidth, overlayOpacity, nameColor]);

  // Redraw whenever any customization changes
  useEffect(() => { drawPreview(); }, [drawPreview]);

  // Cropper update → refresh background
  const onCropperReady = () => {
    scheduleBgRefresh();
  };
  const onCropMove = () => {
    scheduleBgRefresh();
  };

  const scheduleBgRefresh = () => {
    if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
    previewTimerRef.current = setTimeout(() => {
      updateBgFromCropper();
    }, 80);
  };

  const updateBgFromCropper = () => {
    const cropper = cropperRef.current?.cropper;
    if (!cropper) return;
    const canvas = cropper.getCroppedCanvas({ width: CARD_W, height: CARD_H });
    if (!canvas) return;
    const img = new Image();
    img.onload = () => {
      bgImgRef.current = img;
      drawPreview();
    };
    img.src = canvas.toDataURL();
  };

  const onFileChange = (e) => {
    e.preventDefault();
    const files = e.dataTransfer ? e.dataTransfer.files : e.target?.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.type.startsWith('image/')) {
      setStatus({ type: 'error', message: 'Lütfen geçerli bir resim dosyası seçin.' });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setStatus({ type: 'error', message: 'Dosya boyutu 5 MB\'ı aşamaz.' });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => { setImage(reader.result); setStatus({ type: '', message: '' }); };
    reader.readAsDataURL(file);
  };

  const getCropData = async () => {
    const cropper = cropperRef.current?.cropper;
    if (!cropper) return;
    const canvas = cropper.getCroppedCanvas({ width: 900, height: 250, imageSmoothingEnabled: true, imageSmoothingQuality: 'high' });
    if (!canvas) { setStatus({ type: 'error', message: 'Kırpma başarısız oldu.' }); return; }

    setLoading(true);
    setStatus({ type: '', message: '' });

    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append('token', token);
      formData.append('file', blob, 'banner.png');
      formData.append('bar_color', barColor);
      formData.append('border_color', borderColor);
      formData.append('border_width', String(borderWidth));
      formData.append('overlay_opacity', String(overlayOpacity));
      formData.append('name_color', nameColor);

      try {
        const res = await fetch(`${API_URL}/upload-banner`, { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
          setStatus({ type: 'success', message: 'Rank kartı başarıyla güncellendi! Sekmeyi kapatabilirsiniz.' });
        } else {
          setStatus({ type: 'error', message: data.detail || 'Bir hata oluştu.' });
        }
      } catch {
        setStatus({ type: 'error', message: 'Sunucuya bağlanılamadı.' });
      } finally {
        setLoading(false);
      }
    }, 'image/png');
  };

  if (status.type === 'success') {
    return (
      <div className="min-h-screen bg-[#0f0f1a] flex items-center justify-center p-6">
        <div className="bg-[#1a1b2e] border border-green-500/30 rounded-2xl p-10 max-w-md w-full text-center shadow-2xl shadow-green-500/10">
          <div className="w-24 h-24 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
            <Check className="w-12 h-12 text-green-400" />
          </div>
          <h2 className="text-3xl font-extrabold text-white mb-2">Harika!</h2>
          <p className="text-gray-400 text-lg">{status.message}</p>
          <p className="text-gray-600 text-sm mt-4">Yeni rank kartını görmek için Discord'da <span className="text-indigo-400 font-mono">f.rank</span> komutunu kullan.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white" style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* Header */}
      <div className="border-b border-white/5 bg-[#0f0f1a]/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-extrabold tracking-tight">
              <span style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Rank Kartı
              </span>{' '}
              <span className="text-white/80">Stüdyo</span>
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">Arka planını yükle, kırp, özelleştir ve kaydet</p>
          </div>
          {image && (
            <button
              onClick={getCropData}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white transition-all disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', boxShadow: '0 0 20px rgba(99,102,241,0.4)' }}
            >
              {loading ? <><RefreshCw className="w-4 h-4 animate-spin" />Kaydediliyor...</> : <><Check className="w-4 h-4" />Kaydet</>}
            </button>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Error */}
        {status.message && status.type === 'error' && (
          <div className="mb-5 flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{status.message}</p>
          </div>
        )}

        {!image ? (
          /* Drop Zone */
          <div
            onDragOver={e => e.preventDefault()}
            onDrop={onFileChange}
            className="border-2 border-dashed border-white/10 hover:border-indigo-500/60 transition-all duration-300 bg-white/[0.02] rounded-2xl flex flex-col items-center justify-center p-16 text-center cursor-pointer group"
          >
            <div className="w-20 h-20 rounded-2xl bg-white/5 group-hover:bg-indigo-500/10 flex items-center justify-center mb-5 transition-colors">
              <Upload className="w-10 h-10 text-gray-500 group-hover:text-indigo-400 transition-colors" />
            </div>
            <p className="text-xl font-bold text-gray-300 mb-2">Görseli buraya sürükleyin</p>
            <p className="text-sm text-gray-600 mb-8">PNG, JPG veya WEBP • Maksimum 5 MB</p>
            <label className="px-8 py-3 rounded-xl font-semibold text-white cursor-pointer transition-all text-sm"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', boxShadow: '0 0 24px rgba(99,102,241,0.35)' }}>
              Dosya Seç
              <input type="file" className="hidden" accept="image/*" onChange={onFileChange} />
            </label>
          </div>
        ) : (
          /* Editor Layout */
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-6">

            {/* Left — Cropper + Preview */}
            <div className="flex flex-col gap-4">
              {/* Tab switcher */}
              <div className="flex gap-1 bg-white/5 rounded-xl p-1 w-fit">
                <button
                  onClick={() => setActiveTab('crop')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === 'crop' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                  <Sliders className="w-4 h-4" /> Kırp
                </button>
                <button
                  onClick={() => setActiveTab('preview')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === 'preview' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                  <Eye className="w-4 h-4" /> Önizleme
                </button>
              </div>

              {/* Cropper */}
              <div className={`rounded-2xl overflow-hidden border border-white/10 bg-black/40 ${activeTab !== 'crop' ? 'hidden' : ''}`}>
                <Cropper
                  ref={cropperRef}
                  src={image}
                  style={{ height: 420, width: '100%' }}
                  aspectRatio={900 / 250}
                  guides={true}
                  viewMode={1}
                  dragMode="move"
                  background={false}
                  cropBoxResizable={true}
                  cropBoxMovable={true}
                  toggleDragModeOnDblclick={false}
                  ready={onCropperReady}
                  cropmove={onCropMove}
                  zoom={onCropMove}
                />
              </div>

              {/* Live Preview Canvas */}
              <div className={`flex flex-col gap-3 ${activeTab !== 'preview' ? 'hidden' : ''}`}>
                <div className="rounded-2xl overflow-hidden border border-white/10 shadow-2xl" style={{ aspectRatio: '900/250' }}>
                  <canvas
                    ref={canvasRef}
                    style={{ width: '100%', height: '100%', display: 'block' }}
                  />
                </div>
                <p className="text-xs text-center text-gray-600">Önizleme — gerçek bot çıktısını simüle eder</p>
              </div>

              {/* Always-visible small preview strip */}
              {activeTab === 'crop' && (
                <div className="flex flex-col gap-2">
                  <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5" /> Canlı Önizleme
                  </p>
                  <div className="rounded-xl overflow-hidden border border-white/10 shadow-xl" style={{ aspectRatio: '900/250' }}>
                    <canvas
                      ref={canvasRef}
                      style={{ width: '100%', height: '100%', display: 'block' }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Right — Customization Panel */}
            <div className="flex flex-col gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="flex items-center gap-2 mb-5">
                  <Settings2 className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-base font-bold text-white">Kişiselleştir</h2>
                </div>

                <div className="flex flex-col gap-5">
                  <ColorPicker label="Bar & Tema Rengi" value={barColor} onChange={setBarColor} icon="🎨" />
                  <ColorPicker label="Avatar Çerçeve Rengi" value={borderColor} onChange={setBorderColor} icon="🔵" />
                  <SliderPicker label="Çerçeve Kalınlığı" value={borderWidth} onChange={setBorderWidth} min={2} max={16} unit="px" icon="📏" />
                  <div className="h-px bg-white/5" />
                  <ColorPicker label="İsim Rengi" value={nameColor} onChange={setNameColor} icon="✏️" />
                  <SliderPicker label="Arkaplan Karartma" value={overlayOpacity} onChange={setOverlayOpacity} min={0} max={85} unit="%" icon="🌑" />
                </div>
              </div>

              {/* Reset + Change Image */}
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => { setBarColor('#10B981'); setBorderColor('#00C8FF'); setBorderWidth(6); setOverlayOpacity(60); setNameColor('#FFFFFF'); }}
                  className="w-full py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
                >
                  Varsayılana Sıfırla
                </button>
                <button
                  onClick={() => { setImage(null); bgImgRef.current = null; }}
                  className="w-full py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
                >
                  Farklı Resim Seç
                </button>
              </div>

              {/* Hints */}
              <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
                <p className="text-xs font-semibold text-indigo-400 mb-2">💡 İpuçları</p>
                <ul className="text-xs text-gray-500 space-y-1.5">
                  <li>• Bar rengi XP çubuğunu ve seviye yazısını etkiler</li>
                  <li>• Kırpma alanını sürükleyerek konumlandır</li>
                  <li>• Önizleme <span className="font-mono text-gray-400">f.rank</span> çıktısını simüle eder</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BannerUpload;
