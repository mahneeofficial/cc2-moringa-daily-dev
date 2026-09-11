import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import { Menu, Search, Plus, Bell } from "lucide-react";
import { selectCurrentUser } from "../features/auth/authSlice";
import { selectUnreadCount } from "../features/notifications/notificationsSlice";
import Avatar from "../components/ui/Avatar";
import NavDrawer from "./NavDrawer";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const formatAvatarUrl = (raw) => {
  if (!raw) return null;
  let path = typeof raw === "string" ? raw : (raw.profile_image || raw.profileImage || raw.url || "");
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("blob:")) return path;

  const cleanPath = path.replace(/^\/+/, "");
  return API_BASE_URL ? `${API_BASE_URL}/${cleanPath}` : `/${cleanPath}`;
};

export default function Topbar({ search, onSearchChange }) {
  const user = useSelector(selectCurrentUser);
  const unread = useSelector(selectUnreadCount);
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [profileImage, setProfileImage] = useState(null);

  useEffect(() => {
    const rawImg = user?.profile_image || user?.profileImage || user?.profile?.profile_image;
    setProfileImage(formatAvatarUrl(rawImg));

    const handleAvatarUpdate = (e) => {
      if (e.detail) {
        setProfileImage(formatAvatarUrl(e.detail));
      }
    };

    window.addEventListener("user-avatar-updated", handleAvatarUpdate);
    return () => window.removeEventListener("user-avatar-updated", handleAvatarUpdate);
  }, [user]);

  return (
    <>
      <header className="sticky top-0 z-20 bg-white border-b border-line">
        <div className="flex items-center gap-4 px-4 sm:px-6 py-3">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-navy/60 hover:text-navy shrink-0 cursor-pointer"
            aria-label="Open menu"
          >
            <Menu className="w-6 h-6" strokeWidth={1.75} />
          </button>

          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 shrink-0 cursor-pointer"
          >
            <img src="/logo.png" alt="MoringaHub Logo" className="w-8 h-8 object-contain rounded-lg" />
            <span className="font-display font-extrabold text-lg text-navy hidden sm:inline">
              MoringaHub
            </span>
          </button>

          <div className="relative flex-1 max-w-xl">
            <Search className="w-4 h-4 text-navy/40 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="search"
              value={search}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder="Search articles, videos, topics…"
              className="w-full pl-10 pr-4 py-2.5 rounded-full bg-surface border border-line text-sm text-navy placeholder:text-navy/40 focus:outline-none focus:border-brand-500"
            />
          </div>

          <button
            onClick={() => navigate("/create")}
            className="hidden sm:flex items-center gap-1.5 px-4 py-2 rounded-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold transition shrink-0 cursor-pointer"
            aria-label="Create a post"
            title="Create a post"
          >
            <Plus className="w-4 h-4" strokeWidth={2.5} /> Create
          </button>

          <button
            onClick={() => navigate("/notifications")}
            className="relative text-navy/60 hover:text-navy shrink-0 cursor-pointer"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5" strokeWidth={1.75} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-brand-500 ring-2 ring-white" />
            )}
          </button>

          <button onClick={() => navigate("/profile")} className="shrink-0 cursor-pointer">
            <Avatar 
              src={profileImage} 
              profileImage={profileImage} 
              username={user?.username} 
              role={user?.role} 
            />
          </button>
        </div>
      </header>

      <NavDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}