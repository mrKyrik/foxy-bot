import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Cropper from 'react-cropper';
import 'cropperjs/dist/cropper.css';
import { Upload, Check, AlertCircle, RefreshCw, Settings2, Sliders, Sparkles } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'https://kyrik.duckdns.org/api';

const CARD_W = 900;
const CARD_H = 250;

// ── Canvas Helpers ─────────────────────────────────────────────────────────────
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
  } catch { return fallback; }
}

function renderCard(canvas, bgImage, opts) {
  const { barColor, borderColor, borderWidth, overlayOpacity, nameColor, blurAmount,
          username, level, rank, xp, needed } = opts;

  const ctx = canvas.getContext('2d');
  canvas.width = CARD_W;
  canvas.height = CARD_H;

  // Background (with optional blur via canvas filter)
  if (bgImage) {
    const blur = Math.max(0, Math.min(20, blurAmount ?? 0));
    if (blur > 0) {
      const pad = blur * 3;
      ctx.save();
      ctx.filter = `blur(${blur}px)`;
      ctx.drawImage(bgImage, -pad, -pad, CARD_W + pad * 2, CARD_H + pad * 2);
      ctx.filter = 'none';
      ctx.restore();
    } else {
      ctx.drawImage(bgImage, 0, 0, CARD_W, CARD_H);
    }
  } else {
    const grad = ctx.createLinearGradient(0, 0, CARD_W, CARD_H);
    grad.addColorStop(0, '#0f0523');
    grad.addColorStop(1, '#130a2e');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, CARD_W, CARD_H);
  }

  // Overlay
  const op = Math.max(0, Math.min(85, overlayOpacity ?? 60)) / 100;
  ctx.fillStyle = `rgba(0,0,0,${op})`;
  ctx.fillRect(0, 0, CARD_W, CARD_H);

  // Avatar
  const avSize = 180;
  const ax = 35, ay = (CARD_H - avSize) / 2;
  const avCx = ax + avSize / 2, avCy = ay + avSize / 2, avR = avSize / 2;
  const bw = Math.max(2, Math.min(16, borderWidth ?? 6));

  ctx.save();
  ctx.beginPath();
  ctx.arc(avCx, avCy, avR, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = '#1e1040';
  ctx.fillRect(ax, ay, avSize, avSize);
  ctx.fillStyle = '#3b1f6b';
  ctx.beginPath();
  ctx.arc(avCx, avCy - 22, 33, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(avCx, avCy + 68, 52, 38, 0, 0, Math.PI);
  ctx.fill();
  ctx.restore();

  ctx.strokeStyle = `rgb(${hexToRgbStr(borderColor, '139,92,246')})`;
  ctx.lineWidth = bw;
  ctx.beginPath();
  ctx.arc(avCx, avCy, avR + bw / 2 + 1, 0, Math.PI * 2);
  ctx.stroke();

  // Name
  ctx.fillStyle = `rgb(${hexToRgbStr(nameColor, '255,255,255')})`;
  ctx.font = 'bold 57px "Segoe UI", Arial, sans-serif';
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';
  ctx.fillText(username ?? 'Kullanıcı', 255, 38);

  // Level | Rank
  ctx.fillStyle = `rgb(${hexToRgbStr(barColor, '139,92,246')})`;
  ctx.font = 'bold 45px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(`Lvl ${level ?? 1}  |  #${rank ?? 1}`, CARD_W - 55, 42);
  ctx.textAlign = 'left';

  // XP bar background
  const bx = 255, by = 152, bWidth = 590, bHeight = 30;
  ctx.fillStyle = 'rgba(15,5,35,0.85)';
  drawRoundRect(ctx, bx, by, bWidth, bHeight, 15);
  ctx.fill();

  // XP bar fill
  const ratio = Math.min(Math.max((xp ?? 0) / (needed || 1), 0), 1);
  const fillW = ratio * bWidth;
  if (fillW > 2) {
    ctx.fillStyle = `rgb(${hexToRgbStr(barColor, '139,92,246')})`;
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

// ── Shared UI Primitives ───────────────────────────────────────────────────────
const glass = {
  background: 'rgba(255,255,255,0.03)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(139,92,246,0.18)',
  borderRadius: '16px',
};

const accentGrad = 'linear-gradient(135deg, #6366f1, #8b5cf6)';

function ColorPicker({ label, value, onChange, icon }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label style={{ fontSize: '11px', fontWeight: 700, color: 'rgba(167,139,250,0.8)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
        {icon} {label}
      </label>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ position: 'relative', width: '40px', height: '40px', borderRadius: '10px', overflow: 'hidden', border: '1px solid rgba(139,92,246,0.3)', flexShrink: 0, boxShadow: `0 0 12px rgba(139,92,246,0.2)` }}>
          <input type="color" value={value} onChange={e => onChange(e.target.value)}
            style={{ position: 'absolute', inset: 0, width: '150%', height: '150%', top: '-4px', left: '-4px', cursor: 'pointer', border: 0, padding: 0 }} />
        </div>
        <input type="text" value={value}
          onChange={e => /^#[0-9a-fA-F]{0,6}$/.test(e.target.value) && onChange(e.target.value)}
          style={{ flex: 1, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '10px', padding: '9px 12px', fontSize: '13px', fontFamily: 'monospace', color: '#e2d9f3', outline: 'none', transition: 'border-color 0.2s' }}
          maxLength={7}
          onFocus={e => e.target.style.borderColor = 'rgba(139,92,246,0.6)'}
          onBlur={e => e.target.style.borderColor = 'rgba(139,92,246,0.2)'}
        />
      </div>
    </div>
  );
}

function SliderPicker({ label, value, onChange, min, max, unit, icon, accentColor = '#8b5cf6' }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <label style={{ fontSize: '11px', fontWeight: 700, color: 'rgba(167,139,250,0.8)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          {icon} {label}
        </label>
        <span style={{ fontSize: '12px', fontWeight: 800, color: accentColor }}>{value}{unit}</span>
      </div>
      <div style={{ position: 'relative', height: '8px' }}>
        <div style={{ position: 'absolute', inset: 0, borderRadius: '99px', background: `linear-gradient(to right, ${accentColor} ${pct}%, rgba(255,255,255,0.08) ${pct}%)` }} />
        <input type="range" min={min} max={max} value={value}
          onChange={e => onChange(Number(e.target.value))}
          style={{ position: 'absolute', inset: 0, width: '100%', opacity: 0, cursor: 'pointer', margin: 0 }} />
      </div>
    </div>
  );
}

function Divider() {
  return <div style={{ height: '1px', background: 'rgba(139,92,246,0.15)', margin: '4px 0' }} />;
}

// ── Main Component ─────────────────────────────────────────────────────────────
const BannerUpload = () => {
  const { token } = useParams();
  const [image, setImage]     = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus]   = useState({ type: '', message: '' });

  // Customization state
  const [barColor,       setBarColor]       = useState('#8b5cf6');
  const [borderColor,    setBorderColor]    = useState('#6366f1');
  const [borderWidth,    setBorderWidth]    = useState(6);
  const [overlayOpacity, setOverlayOpacity] = useState(55);
  const [nameColor,      setNameColor]      = useState('#FFFFFF');
  const [blurAmount,     setBlurAmount]     = useState(0);

  const cropperRef = useRef(null);
  const canvasRef  = useRef(null);
  const bgImgRef   = useRef(null);
  const timerRef   = useRef(null);
  const optsRef    = useRef({});

  optsRef.current = {
    barColor, borderColor, borderWidth, overlayOpacity, nameColor, blurAmount,
    username: 'Kyrik', level: 16, rank: 2, xp: 1414, needed: 3700,
  };

  const redraw = useCallback(() => {
    if (!canvasRef.current) return;
    renderCard(canvasRef.current, bgImgRef.current, optsRef.current);
  }, []);

  useEffect(() => { redraw(); }, [barColor, borderColor, borderWidth, overlayOpacity, nameColor, blurAmount, redraw]);

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

  const onFileChange = (e) => {
    e.preventDefault();
    const files = e.dataTransfer ? e.dataTransfer.files : e.target?.files;
    if (!files?.length) return;
    const file = files[0];
    if (!file.type.startsWith('image/')) { setStatus({ type: 'error', message: 'Geçerli bir resim seçin.' }); return; }
    if (file.size > 5 * 1024 * 1024) { setStatus({ type: 'error', message: 'Maksimum 5 MB.' }); return; }
    const reader = new FileReader();
    reader.onload = () => { setImage(reader.result); setStatus({ type: '', message: '' }); };
    reader.readAsDataURL(file);
  };

  const handleSave = async () => {
    if (typeof cropperRef.current?.cropper === 'undefined') {
      setStatus({ type: 'error', message: 'Lütfen önce resim yükleyin.' });
      return;
    }
    const cropper = cropperRef.current.cropper;
    const canvas  = cropper.getCroppedCanvas({ width: 900, height: 250, imageSmoothingEnabled: true, imageSmoothingQuality: 'high' });
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
      fd.append('blur_amount',     String(blurAmount));
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

  // ── Success ─────────────────────────────────────────────────────────────────
  if (status.type === 'success') {
    return (
      <div style={{ minHeight: '100vh', background: '#070511', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px',
        backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(99,102,241,0.18) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(139,92,246,0.14) 0%, transparent 50%)' }}>
        <div style={{ ...glass, padding: '48px 40px', maxWidth: '420px', width: '100%', textAlign: 'center', boxShadow: '0 0 60px rgba(99,102,241,0.2), 0 24px 60px rgba(0,0,0,0.6)' }}>
          <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(99,102,241,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', boxShadow: '0 0 30px rgba(99,102,241,0.4)' }}>
            <Check size={36} style={{ color: '#818cf8' }} />
          </div>
          <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>Harika!</h2>
          <p style={{ color: 'rgba(167,139,250,0.8)', fontSize: '15px', marginBottom: '16px' }}>{status.message}</p>
          <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: '13px' }}>
            Discord'da <code style={{ color: '#818cf8', background: 'rgba(99,102,241,0.15)', padding: '2px 8px', borderRadius: '6px' }}>f.rank</code> yaz.
          </p>
        </div>
      </div>
    );
  }

  // ── Main ────────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', background: '#070511', color: '#fff', fontFamily: "'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif",
      backgroundImage: 'radial-gradient(circle at 15% 15%, rgba(99,102,241,0.15) 0%, transparent 45%), radial-gradient(circle at 85% 85%, rgba(139,92,246,0.12) 0%, transparent 45%), radial-gradient(circle at 50% 50%, rgba(168,85,247,0.04) 0%, transparent 70%)' }}>

      {/* ── Sticky Header ──────────────────────────────────────────────────── */}
      <header style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: '1px solid rgba(139,92,246,0.15)', background: 'rgba(7,5,17,0.75)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 24px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={18} style={{ color: '#a78bfa' }} />
              <h1 style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.3px', lineHeight: 1 }}>
                <span style={{ background: accentGrad, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Foxy Rank</span>
                {' '}<span style={{ color: 'rgba(255,255,255,0.85)' }}>Stüdyosu</span>
              </h1>
            </div>
            <p style={{ fontSize: '11px', color: 'rgba(167,139,250,0.6)', marginTop: '2px', letterSpacing: '0.02em' }}>Arka planını yükle · kırp · özelleştir · kaydet</p>
          </div>
          {image && (
            <button onClick={handleSave} disabled={loading}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 22px', borderRadius: '12px', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: '14px', color: '#fff', background: accentGrad, boxShadow: '0 0 24px rgba(99,102,241,0.45), 0 4px 12px rgba(0,0,0,0.4)', opacity: loading ? 0.7 : 1, transition: 'all 0.2s', fontFamily: 'inherit' }}>
              {loading ? <><RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />Kaydediliyor…</> : <><Check size={15} />Kaydet</>}
            </button>
          )}
        </div>
      </header>

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '28px 24px' }}>

        {/* Error */}
        {status.message && status.type === 'error' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '12px', padding: '12px 16px', marginBottom: '20px' }}>
            <AlertCircle size={18} style={{ color: '#f87171', flexShrink: 0 }} />
            <p style={{ fontSize: '14px', color: '#fca5a5', fontWeight: 500 }}>{status.message}</p>
          </div>
        )}

        {!image ? (
          /* ── Drop Zone ───────────────────────────────────────────────────── */
          <label style={{ display: 'block', cursor: 'pointer' }}
            onDragOver={e => e.preventDefault()}
            onDrop={onFileChange}>
            <div style={{ ...glass, padding: '72px 40px', textAlign: 'center', transition: 'all 0.3s', cursor: 'pointer', position: 'relative', overflow: 'hidden' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(139,92,246,0.45)'; e.currentTarget.style.boxShadow = '0 0 40px rgba(99,102,241,0.15)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(139,92,246,0.18)'; e.currentTarget.style.boxShadow = 'none'; }}>
              {/* Decorative glow blobs */}
              <div style={{ position: 'absolute', top: '-60px', right: '-60px', width: '200px', height: '200px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(139,92,246,0.12), transparent 70%)', pointerEvents: 'none' }} />
              <div style={{ position: 'absolute', bottom: '-60px', left: '-60px', width: '200px', height: '200px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(99,102,241,0.10), transparent 70%)', pointerEvents: 'none' }} />

              <div style={{ width: '72px', height: '72px', borderRadius: '18px', background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(139,92,246,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', boxShadow: '0 0 24px rgba(99,102,241,0.2)' }}>
                <Upload size={32} style={{ color: '#a78bfa' }} />
              </div>
              <p style={{ fontSize: '20px', fontWeight: 800, color: '#f5f3ff', marginBottom: '8px' }}>Görseli buraya sürükleyin</p>
              <p style={{ fontSize: '13px', color: 'rgba(167,139,250,0.6)', marginBottom: '28px' }}>PNG, JPG veya WEBP · Maksimum 5 MB</p>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 28px', borderRadius: '12px', background: accentGrad, fontWeight: 700, fontSize: '14px', color: '#fff', boxShadow: '0 0 28px rgba(99,102,241,0.45)', cursor: 'pointer' }}>
                <Upload size={16} /> Dosya Seç
              </div>
              <input type="file" style={{ display: 'none' }} accept="image/*" onChange={onFileChange} />
            </div>
          </label>
        ) : (
          /* ── Editor ──────────────────────────────────────────────────────── */
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 370px', gap: '20px', alignItems: 'start' }}>

            {/* Left column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

              {/* Cropper */}
              <div style={{ ...glass, overflow: 'hidden' }}>
                <div style={{ padding: '10px 16px', borderBottom: '1px solid rgba(139,92,246,0.12)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sliders size={14} style={{ color: '#a78bfa' }} />
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'rgba(167,139,250,0.7)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Kırpma Alanı</span>
                </div>
                <Cropper
                  ref={cropperRef}
                  src={image}
                  style={{ height: 340, width: '100%' }}
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

              {/* Live Preview */}
              <div style={{ ...glass, overflow: 'hidden' }}>
                <div style={{ padding: '10px 16px', borderBottom: '1px solid rgba(139,92,246,0.12)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '14px' }}>👁</span>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'rgba(167,139,250,0.7)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Canlı Önizleme</span>
                  <span style={{ marginLeft: 'auto', fontSize: '11px', color: 'rgba(139,92,246,0.5)', fontStyle: 'italic' }}>f.rank çıktısını simüle eder</span>
                </div>
                <div style={{ padding: '12px', background: 'rgba(0,0,0,0.25)' }}>
                  <div style={{ borderRadius: '10px', overflow: 'hidden', aspectRatio: `${CARD_W}/${CARD_H}`, boxShadow: '0 4px 24px rgba(0,0,0,0.5)' }}>
                    <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Right column — Customization */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', position: 'sticky', top: '80px' }}>

              <div style={{ ...glass, padding: '20px', boxShadow: '0 0 40px rgba(99,102,241,0.08)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '10px', background: 'rgba(99,102,241,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(139,92,246,0.25)' }}>
                    <Settings2 size={16} style={{ color: '#a78bfa' }} />
                  </div>
                  <h2 style={{ fontSize: '15px', fontWeight: 800, color: '#f5f3ff' }}>Kişiselleştir</h2>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                  <ColorPicker label="Bar & Tema Rengi"     value={barColor}    onChange={setBarColor}    icon="🎨" />
                  <ColorPicker label="Çerçeve Rengi"        value={borderColor} onChange={setBorderColor} icon="🔵" />
                  <SliderPicker label="Çerçeve Kalınlığı"   value={borderWidth} onChange={setBorderWidth} min={2} max={16} unit="px" icon="📏" />
                  <Divider />
                  <ColorPicker label="İsim Rengi"           value={nameColor}   onChange={setNameColor}   icon="✏️" />
                  <SliderPicker label="Arkaplan Karartma"   value={overlayOpacity} onChange={setOverlayOpacity} min={0} max={85} unit="%" icon="🌑" />
                  <SliderPicker label="Bulanıklık (Blur)"   value={blurAmount}  onChange={setBlurAmount}  min={0} max={20} unit="px" icon="🌀" accentColor="#c084fc" />
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <button onClick={() => { setBarColor('#8b5cf6'); setBorderColor('#6366f1'); setBorderWidth(6); setOverlayOpacity(55); setNameColor('#FFFFFF'); setBlurAmount(0); }}
                  style={{ width: '100%', padding: '10px', borderRadius: '11px', border: '1px solid rgba(139,92,246,0.2)', background: 'rgba(255,255,255,0.03)', color: 'rgba(167,139,250,0.8)', fontWeight: 600, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(139,92,246,0.08)'; e.currentTarget.style.color = '#c4b5fd'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.color = 'rgba(167,139,250,0.8)'; }}>
                  Varsayılana Sıfırla
                </button>
                <button onClick={() => { setImage(null); bgImgRef.current = null; }}
                  style={{ width: '100%', padding: '10px', borderRadius: '11px', border: '1px solid rgba(139,92,246,0.2)', background: 'rgba(255,255,255,0.03)', color: 'rgba(167,139,250,0.8)', fontWeight: 600, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(139,92,246,0.08)'; e.currentTarget.style.color = '#c4b5fd'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.color = 'rgba(167,139,250,0.8)'; }}>
                  Farklı Resim Seç
                </button>
              </div>

              {/* Tips */}
              <div style={{ ...glass, padding: '14px 16px', borderColor: 'rgba(99,102,241,0.2)', background: 'rgba(99,102,241,0.04)' }}>
                <p style={{ fontSize: '11px', fontWeight: 800, color: '#818cf8', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>💡 İpuçları</p>
                <ul style={{ fontSize: '12px', color: 'rgba(167,139,250,0.6)', lineHeight: 1.8, listStyle: 'none', padding: 0 }}>
                  <li>• Bar rengi XP çubuğunu + seviye yazısını etkiler</li>
                  <li>• Kırpma kutusunu sürükleyerek konumlandır</li>
                  <li>• Bulanıklık özelliği resme blur efekti verir</li>
                  <li>• Kaydet ile tüm ayarlar birlikte uygulanır</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Spin keyframe for loading */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default BannerUpload;
