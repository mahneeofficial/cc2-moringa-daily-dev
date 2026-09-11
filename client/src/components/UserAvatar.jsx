import { useState, useEffect } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const formatAvatarUrl = (raw) => {
  if (!raw) return null;
  let path = typeof raw === "string" ? raw : (raw.profile_image || raw.profileImage || raw.url || "");
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("blob:")) return path;

  const cleanPath = path.replace(/^\/+/, "");
  return API_BASE_URL ? `${API_BASE_URL}/${cleanPath}` : `/${cleanPath}`;
};

export default function UserAvatar({ 
  username, 
  profileImage, 
  size = "w-8 h-8", 
  showName = true, 
  className = "" 
}) {
  const imageUrl = formatAvatarUrl(profileImage);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setHasError(false);
  }, [profileImage]);

  const getInitial = (name) => {
    if (!name) return "U";
    return name.trim().charAt(0).toUpperCase();
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`${size} rounded-full overflow-hidden bg-orange-100 border border-orange-200 flex items-center justify-center shrink-0`}>
        {imageUrl && !hasError ? (
          <img 
            src={imageUrl} 
            alt={username || "User avatar"} 
            className="w-full h-full object-cover" 
            onError={() => setHasError(true)}
          />
        ) : (
          <span className="text-xs font-bold text-orange-600 uppercase">
            {getInitial(username)}
          </span>
        )}
      </div>
      {showName && username && (
        <span className="text-xs font-medium text-gray-700 truncate">{username}</span>
      )}
    </div>
  );
}