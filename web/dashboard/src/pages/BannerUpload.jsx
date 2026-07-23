import React, { useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import Cropper from 'react-cropper';
import 'cropperjs/dist/cropper.css';
import { Upload, Check, AlertCircle, RefreshCw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

const BannerUpload = () => {
  const { token } = useParams();
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const cropperRef = useRef(null);

  const onFileChange = (e) => {
    e.preventDefault();
    let files;
    if (e.dataTransfer) {
      files = e.dataTransfer.files;
    } else if (e.target) {
      files = e.target.files;
    }
    
    if (files && files.length > 0) {
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
      reader.onload = () => {
        setImage(reader.result);
        setStatus({ type: '', message: '' });
      };
      reader.readAsDataURL(file);
    }
  };

  const getCropData = async () => {
    if (typeof cropperRef.current?.cropper !== 'undefined') {
      const cropper = cropperRef.current?.cropper;
      
      // Enforce 900x250 output size
      const canvas = cropper.getCroppedCanvas({
        width: 900,
        height: 250,
        imageSmoothingEnabled: true,
        imageSmoothingQuality: 'high',
      });
      
      if (!canvas) {
        setStatus({ type: 'error', message: 'Kırpma başarısız oldu.' });
        return;
      }

      setLoading(true);
      setStatus({ type: '', message: '' });

      canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('token', token);
        formData.append('file', blob, 'banner.png');

        try {
          const res = await fetch(`${API_URL}/upload-banner`, {
            method: 'POST',
            body: formData,
          });
          
          const data = await res.json();
          
          if (res.ok) {
            setStatus({ type: 'success', message: 'Arka plan başarıyla güncellendi! Sekmeyi kapatabilirsiniz.' });
          } else {
            setStatus({ type: 'error', message: data.detail || 'Bir hata oluştu.' });
          }
        } catch (err) {
          setStatus({ type: 'error', message: 'Sunucuya bağlanılamadı.' });
        } finally {
          setLoading(false);
        }
      }, 'image/png');
    }
  };

  if (status.type === 'success') {
    return (
      <div className="min-h-screen bg-[#1e1e2e] flex items-center justify-center p-6">
        <div className="bg-[#2a2b3d] border border-green-500/30 rounded-2xl p-8 max-w-md w-full text-center shadow-xl">
          <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check className="w-10 h-10 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Başarılı!</h2>
          <p className="text-gray-400">{status.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#1e1e2e] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="bg-[#2a2b3d] border border-[#3f3f5a] rounded-2xl p-6 sm:p-8 max-w-4xl w-full shadow-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-extrabold text-white tracking-tight mb-2">
            <span className="bg-gradient-to-r from-blue-400 to-indigo-500 text-transparent bg-clip-text">Rank Kartı</span> Arka Planı
          </h1>
          <p className="text-gray-400">Resmini yükle, istediğin gibi kırp ve kaydet!</p>
        </div>

        {status.message && status.type === 'error' && (
          <div className="mb-6 flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{status.message}</p>
          </div>
        )}

        {!image ? (
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={onFileChange}
            className="border-2 border-dashed border-[#3f3f5a] hover:border-indigo-500 transition-colors bg-[#232433] rounded-2xl flex flex-col items-center justify-center p-12 text-center cursor-pointer"
          >
            <Upload className="w-16 h-16 text-gray-500 mb-4" />
            <p className="text-lg font-medium text-gray-300 mb-1">
              Görseli sürükleyip bırakın veya seçin
            </p>
            <p className="text-sm text-gray-500 mb-6">PNG, JPG (Maks 5 MB)</p>
            <label className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-xl font-medium cursor-pointer transition-colors shadow-lg shadow-indigo-500/20">
              Dosya Seç
              <input type="file" className="hidden" accept="image/*" onChange={onFileChange} />
            </label>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="bg-black/40 rounded-xl overflow-hidden border border-[#3f3f5a]">
              <Cropper
                ref={cropperRef}
                src={image}
                style={{ height: 400, width: '100%' }}
                aspectRatio={900 / 250}
                guides={true}
                viewMode={1}
                dragMode="move"
                background={false}
                cropBoxResizable={true}
                cropBoxMovable={true}
                toggleDragModeOnDblclick={false}
              />
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-end">
              <button
                onClick={() => setImage(null)}
                disabled={loading}
                className="px-6 py-2.5 rounded-xl font-medium text-gray-300 hover:text-white bg-[#3f3f5a]/50 hover:bg-[#3f3f5a] transition-colors disabled:opacity-50"
              >
                İptal Et
              </button>
              <button
                onClick={getCropData}
                disabled={loading}
                className="px-8 py-2.5 rounded-xl font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/20 flex items-center justify-center disabled:opacity-50"
              >
                {loading ? (
                  <><RefreshCw className="w-5 h-5 mr-2 animate-spin" /> Kaydediliyor...</>
                ) : (
                  <><Upload className="w-5 h-5 mr-2" /> Kırp ve Kaydet</>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BannerUpload;
