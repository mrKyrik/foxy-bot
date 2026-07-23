import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Cropper from 'react-cropper';
import 'cropperjs/dist/cropper.css';
import { Upload, Check, AlertCircle, RefreshCw, Settings2, Sliders } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'https://kyrik.duckdns.org/api';

const CARD_W = 900;
const CARD_H = 250;

// ── Canvas Helpers ────────────────────────────────────────────────────────────
function drawRoundRect(ctx, x, y, w, h, r) {
  const rad = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rad, y);
  ctx.lineTo(x + w - rad, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + rad);
  ctx.lineTo(x + w, y + h - rad);
  ctx.quadraticCurveTo(x + w, y + h, x + w - rad, y + h);
  ctx.lineTo(x + rad, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - rad);
  ctx.lineTo(x, y + rad);
  ctx.quadraticCurveTo(x, y, x + rad, y);
  ctx.closePath();
}

function hexToRgbStr(hex, fallback = '16,185,129') {
  try {
    const clean = hex.replace('#', '');
    const full = clean.length === 3
      ? clean.split('').map(c => c + c).join('')
      : clean;
    const n = parseInt(full, 16);
    return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
  } catch {
    return fallback;
  }
}

function renderCard(canvas, bgImage, opts) {
  const {
    barColor, borderColor, borderWidth, overlayOpacity, nameColor,
    username, level, rank, xp, needed,
  } = opts;

  const ctx = canvas.getContext('2d');
  canvas.width = CARD_W;
  canvas.height = CARD_H;

  // Background
  if (bgImage) {
    ctx.drawImage(bgImage, 0, 0, CARD_W, CARD_H);
  } else {
    ctx.fillStyle = '#0F172A';
    ctx.fillRect(0, 0, CARD_W, CARD_H);
  }

  // Overlay
  const op = Math.max(0, Math.min(85, overlayOpacity ?? 60)) / 100;
  ctx.fillStyle = `rgba(0,0,0,${op})`;
  ctx.fillRect(0, 0, CARD_W, CARD_H);

  // ── Avatar ─────────────────────────────────────────────────────────────────
  const avSize = 180;
  const ax = 35, ay = (CARD_H - avSize) / 2;
  const avCx = ax + avSize / 2, avCy = ay + avSize / 2, avR = avSize / 2;
  const bw = Math.max(2, Math.min(16, borderWidth ?? 6));

  // Avatar placeholder (dark circle + silhouette)
  ctx.save();
  ctx.beginPath();
  ctx.arc(avCx, avCy, avR, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(ax, ay, avSize, avSize);
  ctx.fillStyle = '#334155';
  ctx.beginPath();
  ctx.arc(avCx, avCy - 22, 33, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(avCx, avCy + 68, 52, 38, 0, 0, Math.PI);
  ctx.fill();
  ctx.restore();

  // Avatar border
  ctx.strokeStyle = `rgb(${hexToRgbStr(borderColor, '0,200,255')})`;
  ctx.lineWidth = bw;
  ctx.beginPath();
  ctx.arc(avCx, avCy, avR + bw / 2 + 1, 0, Math.PI * 2);
  ctx.stroke();

  // ── Name ───────────────────────────────────────────────────────────────────
  ctx.fillStyle = `rgb(${hexToRgbStr(nameColor, '255,255,255')})`;
  ctx.font = 'bold 57px "Segoe UI", Arial, sans-serif';
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';
  ctx.fillText(username ?? 'Kullanıcı', 255, 38);

  // ── Level | Rank (right) ───────────────────────────────────────────────────
  ctx.fillStyle = `rgb(${hexToRgbStr(barColor, '16,185,129')})`;
  ctx.font = 'bold 45px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'top';
  ctx.fillText(`Lvl ${level ?? 1}  |  #${rank ?? 1}`, CARD_W - 55, 42);
  ctx.textAlign = 'left';

  // ── XP Bar ────────────────────────────────────────────────────────────────
  const bx = 255, by = 152, bWidth = 590, bHeight = 30;
  ctx.fillStyle = 'rgba(30,41,59,0.88)';
  drawRoundRect(ctx, bx, by, bWidth, bHeight, 15);
  ctx.fill();

  const ratio = Math.min(Math.max((xp ?? 0) / (needed || 1), 0), 1);
  const fillW = ratio * bWidth;
  if (fillW > 2) {
    ctx.fillStyle = `rgb(${hexToRgbStr(barColor, '16,185,129')})`;
    drawRoundRect(ctx, bx, by, fillW, bHeight, 15);
    ctx.fill();
  }

  // XP text
  ctx.fillStyle = 'rgba(200,200,200,0.9)';
  ctx.font = '500 23px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'bottom';
  ctx.fillText(`${xp ?? 0} / ${needed ?? 0} XP`, bx + bWidth, by - 5);
}

// ── Shared UI ─────────────────────────────────────────────────────────────────
function ColorPicker({ label, value, onChange, icon }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        {icon} {label}
      </label>
      <div className="flex items-center gap-2">
        <div className="relative w-10 h-10 rounded-lg overflow-hidden border-2 border-white/10 flex-shrink-0">
          <input
            type="color"
            value={value}
            onChange={e => onChange(e.target.value)}
            className="absolute inset-0 w-[150%] h-[150%] -top-2 -left-2 cursor-pointer border-0 p-0"
          />
        </div>
        <input
          type="text"
          value={value}
          onChange={e => /^#[0-9a-fA-F]{0,6}$/.test(e.target.value) && onChange(e.target.value)}
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-indigo-500/60 transition-colors"
          maxLength={7}
        />
      </div>
    </div>
  );
}

function SliderPicker({ label, value, onChange, min, max, unit, icon }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
        <span>{icon} {label}</span>
        <span className="text-indigo-400 font-bold">{value}{unit}</span>
      </label>
      <input
        type="range" min={min} max={max} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-full appearance-none cursor-pointer"
        style={{ background: `linear-gradient(to right, #6366f1 ${pct}%, rgba(255,255,255,0.1) ${pct}%)` }}
      />
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
const BannerUpload = () => {
  const { token } = useParams();
  const [image, setImage]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus]   = useState({ type: '', message: '' });

  // Customization
  const [barColor,       setBarColor]       = useState('#10B981');
  const [borderColor,    setBorderColor]    = useState('#00C8FF');
  const [borderWidth,    setBorderWidth]    = useState(6);
  const [overlayOpacity, setOverlayOpacity] = useState(60);
  const [nameColor,      setNameColor]      = useState('#FFFFFF');

  const cropperRef = useRef(null);
  const canvasRef  = useRef(null);   // single canvas, always mounted when image set
  const bgImgRef   = useRef(null);
  const timerRef   = useRef(null);

  // Preview options packed into a stable ref so refreshBg never goes stale
  const optsRef = useRef({});
  optsRef.current = {
    barColor, borderColor, borderWidth, overlayOpacity, nameColor,
    username: 'Kyrik', level: 16, rank: 2, xp: 1414, needed: 3700,
  };

  // ── Draw current frame ────────────────────────────────────────────────────
  const redraw = useCallback(() => {
    if (!canvasRef.current) return;
    renderCard(canvasRef.current, bgImgRef.current, optsRef.current);
  }, []); // optsRef is always current, no deps needed

  // Redraw when any customization knob changes
  useEffect(() => { redraw(); }, [barColor, borderColor, borderWidth, overlayOpacity, nameColor, redraw]);

  // ── Pull background from cropper → redraw ─────────────────────────────────
  const refreshBg = useCallback(() => {
    const cropper = cropperRef.current?.cropper;
    if (!cropper) return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const c = cropper.getCroppedCanvas({ width: CARD_W, height: CARD_H });
      if (!c) return;
      const img = new Image();
      img.onload = () => { bgImgRef.current = img; redraw(); };
      img.src = c.toDataURL();
    }, 80);
  }, [redraw]);

  // ── File handling ─────────────────────────────────────────────────────────
  const onFileChange = (e) => {
    e.preventDefault();
    const files = e.dataTransfer ? e.dataTransfer.files : e.target?.files;
    if (!files?.length) return;
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

  // ── Save ──────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (typeof cropperRef.current?.cropper === 'undefined') {
      setStatus({ type: 'error', message: 'Lütfen önce resim yükleyin.' });
      return;
    }
    const cropper = cropperRef.current.cropper;
    const canvas  = cropper.getCroppedCanvas({
      width: 900, height: 250,
      imageSmoothingEnabled: true, imageSmoothingQuality: 'high',
    });
    if (!canvas) { setStatus({ type: 'error', message: 'Kırpma başarısız.' }); return; }

    setLoading(true);
    setStatus({ type: '', message: '' });

    canvas.toBlob(async (blob) => {
      const fd = new FormData();
      fd.append('token',           token);
      fd.append('file',            blob, 'banner.png');
      fd.append('bar_color',       barColor);
      fd.append('border_color',    borderColor);
      fd.append('border_width',    String(borderWidth));
      fd.append('overlay_opacity', String(overlayOpacity));
      fd.append('name_color',      nameColor);
      try {
        const res  = await fetch(`${API_URL}/upload-banner`, { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) setStatus({ type: 'success', message: data.message ?? 'Rank kartı güncellendi!' });
        else        setStatus({ type: 'error',   message: data.detail  ?? 'Bir hata oluştu.' });
      } catch {
        setStatus({ type: 'error', message: 'Sunucuya bağlanılamadı.' });
      } finally {
        setLoading(false);
      }
    }, 'image/png');
  };

  // ── Success screen ────────────────────────────────────────────────────────
  if (status.type === 'success') {
    return (
      <div className="min-h-screen bg-[#0f0f1a] flex items-center justify-center p-6">
        <div className="bg-[#1a1b2e] border border-green-500/30 rounded-2xl p-10 max-w-md w-full text-center shadow-2xl shadow-green-500/10">
          <div className="w-24 h-24 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check className="w-12 h-12 text-green-400" />
          </div>
          <h2 className="text-3xl font-extrabold text-white mb-2">Harika!</h2>
          <p className="text-gray-400 text-lg">{status.message}</p>
          <p className="text-gray-600 text-sm mt-4">
            Discord'da{' '}
            <span className="text-indigo-400 font-mono">f.rank</span>{' '}
            yazarak yeni kartını görüntüleyebilirsin.
          </p>
        </div>
      </div>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen bg-[#0f0f1a] text-white"
      style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}
    >
      {/* Sticky header */}
      <div className="border-b border-white/5 bg-[#0f0f1a]/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-extrabold tracking-tight">
              <span style={{
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>
                Rank Kartı
              </span>{' '}
              <span className="text-white/80">Stüdyo</span>
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">Arka planını yükle, kırp, özelleştir ve kaydet</p>
          </div>
          {image && (
            <button
              onClick={handleSave}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white transition-all disabled:opacity-50 active:scale-95"
              style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', boxShadow: '0 0 20px rgba(99,102,241,.4)' }}
            >
              {loading
                ? <><RefreshCw className="w-4 h-4 animate-spin" />Kaydediliyor…</>
                : <><Check className="w-4 h-4" />Kaydet</>}
            </button>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Error banner */}
        {status.message && status.type === 'error' && (
          <div className="mb-5 flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{status.message}</p>
          </div>
        )}

        {!image ? (
          /* ── Drop zone ──────────────────────────────────────────────────── */
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
            <label
              className="px-8 py-3 rounded-xl font-semibold text-white cursor-pointer text-sm"
              style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', boxShadow: '0 0 24px rgba(99,102,241,.35)' }}
            >
              Dosya Seç
              <input type="file" className="hidden" accept="image/*" onChange={onFileChange} />
            </label>
          </div>
        ) : (
          /* ── Editor ─────────────────────────────────────────────────────── */
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">

            {/* ── Left: Cropper + Preview ─────────────────────────────────── */}
            <div className="flex flex-col gap-5">

              {/* Cropper */}
              <div>
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider flex items-center gap-1.5 mb-2">
                  <Sliders className="w-3.5 h-3.5" /> Kırpma Alanı
                </p>
                <div className="rounded-2xl overflow-hidden border border-white/10 bg-black/40">
                  <Cropper
                    ref={cropperRef}
                    src={image}
                    style={{ height: 360, width: '100%' }}
                    aspectRatio={CARD_W / CARD_H}
                    guides={true}
                    viewMode={1}
                    dragMode="move"
                    background={false}
                    cropBoxResizable={true}
                    cropBoxMovable={true}
                    toggleDragModeOnDblclick={false}
                    ready={refreshBg}
                    cropmove={refreshBg}
                    zoom={refreshBg}
                  />
                </div>
              </div>

              {/* Live preview — SINGLE canvas, always mounted */}
              <div>
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider flex items-center gap-1.5 mb-2">
                  👁 Canlı Önizleme
                </p>
                <div
                  className="rounded-xl overflow-hidden border border-white/10 shadow-xl w-full"
                  style={{ aspectRatio: `${CARD_W}/${CARD_H}` }}
                >
                  <canvas
                    ref={canvasRef}
                    style={{ width: '100%', height: '100%', display: 'block' }}
                  />
                </div>
                <p className="text-xs text-center text-gray-600 mt-1.5">
                  Gerçek <span className="font-mono">f.rank</span> çıktısını simüle eder
                </p>
              </div>
            </div>

            {/* ── Right: Customization panel ──────────────────────────────── */}
            <div className="flex flex-col gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="flex items-center gap-2 mb-5">
                  <Settings2 className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-base font-bold text-white">Kişiselleştir</h2>
                </div>

                <div className="flex flex-col gap-5">
                  <ColorPicker label="Bar & Tema Rengi"      value={barColor}    onChange={setBarColor}    icon="🎨" />
                  <ColorPicker label="Avatar Çerçeve Rengi"  value={borderColor} onChange={setBorderColor} icon="🔵" />
                  <SliderPicker
                    label="Çerçeve Kalınlığı" value={borderWidth} onChange={setBorderWidth}
                    min={2} max={16} unit="px" icon="📏"
                  />
                  <div className="h-px bg-white/5" />
                  <ColorPicker label="İsim Rengi" value={nameColor} onChange={setNameColor} icon="✏️" />
                  <SliderPicker
                    label="Arkaplan Karartma" value={overlayOpacity} onChange={setOverlayOpacity}
                    min={0} max={85} unit="%" icon="🌑"
                  />
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => {
                    setBarColor('#10B981'); setBorderColor('#00C8FF');
                    setBorderWidth(6); setOverlayOpacity(60); setNameColor('#FFFFFF');
                  }}
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

              {/* Tips */}
              <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
                <p className="text-xs font-semibold text-indigo-400 mb-2">💡 İpuçları</p>
                <ul className="text-xs text-gray-500 space-y-1.5">
                  <li>• Bar rengi XP çubuğunu ve seviye yazısını etkiler</li>
                  <li>• Kırpma kutusunu sürükleyerek konumlandır</li>
                  <li>• Önizleme gerçek bot çıktısını simüle eder</li>
                  <li>• Kaydet tuşuyla tüm ayarlar birlikte kaydedilir</li>
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
