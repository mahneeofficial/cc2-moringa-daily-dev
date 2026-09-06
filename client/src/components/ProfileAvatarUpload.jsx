import { useState, useEffect } from 'react';
import { Camera } from 'lucide-react';
import apiClient from '../services/apiClient';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export default function ProfileAvatarUpload({ user, onAvatarUpdated }) {
  const getFullAvatarUrl = (img) => {
    if (!img) return null;
    if (typeof img !== 'string') return null;
    if (img.startsWith('http://') || img.startsWith('https://') || img.startsWith('blob:')) {
      return img;
    }
    const cleanPath = img.replace(/^\/+/, '');
    return API_BASE_URL ? `${API_BASE_URL}/${cleanPath}` : `/${cleanPath}`;
  };

  const [preview, setPreview] = useState(getFullAvatarUrl(user?.profile_image));
  const [uploading, setUploading] = useState(false);

  // Synchronize preview if user prop updates externally
  useEffect(() => {
    if (user?.profile_image) {
      setPreview(getFullAvatarUrl(user.profile_image));
    }
  }, [user]);

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setPreview(URL.createObjectURL(file));

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);

    try {
      const data = await apiClient.put('/profiles/me', formData);

      const newAvatar = data?.profile_image || data?.profile?.profile_image || data?.avatar_url;
      const fullUrl = getFullAvatarUrl(newAvatar);
      setPreview(fullUrl);

      // Persist to localStorage so the avatar remains after browser refresh
      try {
        const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
        const updatedUser = {
          ...storedUser,
          profile_image: newAvatar,
          profileImage: newAvatar,
          avatar_url: newAvatar,
        };
        localStorage.setItem('user', JSON.stringify(updatedUser));
      } catch (err) {
        console.error('Error updating local storage user:', err);
      }

      // Broadcast change so Navbar and Topbar update dynamically
      window.dispatchEvent(new CustomEvent('user-avatar-updated', { detail: fullUrl }));

      if (onAvatarUpdated) onAvatarUpdated(newAvatar);
    } catch (err) {
      console.error('Upload failed:', err);
      const errorMessage = err?.message || 'Failed to update profile picture';
      alert(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <div className="relative w-20 h-20 rounded-full overflow-hidden bg-slate-100 border-2 border-slate-200 flex items-center justify-center group shadow-sm">
        {preview ? (
          <img src={preview} alt="Profile Avatar" className="w-full h-full object-cover" />
        ) : (
          <span className="text-2xl font-bold text-slate-600">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </span>
        )}

        <label className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center cursor-pointer transition">
          <Camera className="w-6 h-6 text-white" />
          <input 
            type="file" 
            accept="image/*" 
            onChange={handleFileSelect} 
            className="hidden" 
          />
        </label>
      </div>

      <div>
        <label className="cursor-pointer bg-orange-500 hover:bg-orange-600 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition inline-block shadow-sm">
          {uploading ? 'Uploading...' : 'Change Avatar'}
          <input 
            type="file" 
            accept="image/*" 
            onChange={handleFileSelect} 
            className="hidden" 
          />
        </label>
      </div>
    </div>
  );
}