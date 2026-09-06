import { useState, useEffect } from "react";
import { initials, roleColorClass } from "../../utils/format";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const formatAvatarUrl = (raw) => {
  if (!raw) return null;
  let path = typeof raw === "string" ? raw : (raw.profile_image || raw.profileImage || raw.url || "");
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("blob:")) return path;

  const cleanPath = path.replace(/^\/+/, "");
  return API_BASE_URL ? `${API_BASE_URL}/${cleanPath}` : `/${cleanPath}`;
};

export default function Avatar({ src, profileImage, username, role, size = "md", className = "" }) {
  const sizes = { 
    sm: "w-7 h-7 text-[10px]", 
    md: "w-9 h-9 text-xs", 
    lg: "w-14 h-14 text-base" 
  };

  const rawImage = src || profileImage;
  const imageUrl = formatAvatarUrl(rawImage);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setHasError(false);
  }, [rawImage]);

  return (
    <div
      className={`${sizes[size] || size} shrink-0 rounded-full overflow-hidden bg-surface border border-line flex items-center justify-center font-mono font-medium ${roleColorClass(role)} ${className}`}
    >
      {imageUrl && !hasError ? (
        <img
          src={imageUrl}
          alt={username || "User avatar"}
          className="w-full h-full object-cover"
          onError={() => setHasError(true)}
        />
      ) : (
        <span>{initials(username)}</span>
      )}
    </div>
  );
}