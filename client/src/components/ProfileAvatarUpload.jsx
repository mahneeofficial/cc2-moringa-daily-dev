import { useState } from 'react';
import { Camera } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

export default function ProfileAvatarUpload({ user, onAvatarUpdated }) {
  const [preview, setPreview] = useState(
    user?.profile_image ? `${API_BASE_URL}${user.profile_image}` : null
  );
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setPreview(URL.createObjectURL(file));

    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!token) {
      alert('Your session expired. Please log in again.');
      return;
    }

    const formData = new FormData();
    formData.append('profile_picture', file);

    setUploading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/avatar`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        if (onAvatarUpdated) onAvatarUpdated(data.profile_image);
      } else {
        alert(data.error || 'Failed to update profile picture');
      }
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <div className="relative w-20 h-20 rounded-full overflow-hidden bg-slate-800 border-2 border-slate-700 flex items-center justify-center group">
        {preview ? (
          <img src={preview} alt="Profile Avatar" className="w-full h-full object-cover" />
        ) : (
          <span className="text-2xl font-bold text-slate-300">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </span>
        )}

        <label className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center cursor-pointer transition">
          <Camera className="w-6 h-6 text-emerald-400" />
          <input 
            type="file" 
            accept="image/png, image/jpeg, image/webp" 
            onChange={handleFileSelect} 
            className="hidden" 
          />
        </label>
      </div>

      <div>
        <label className="cursor-pointer bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-4 py-2.5 rounded-xl transition inline-block">
          {uploading ? 'Uploading...' : 'Change Avatar'}
          <input 
            type="file" 
            accept="image/png, image/jpeg, image/webp" 
            onChange={handleFileSelect} 
            className="hidden" 
          />
        </label>
        <p className="text-[11px] text-slate-500 mt-1">PNG, JPG or WEBP up to 5MB</p>
      </div>
    </div>
  );
}