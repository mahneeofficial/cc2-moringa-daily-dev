import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Search, Bell, ShieldCheck, LogOut, User, Bookmark, Plus, Menu } from "lucide-react";
import { getCurrentUser } from "../services/authApi";
import apiRequest from "../services/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const formatAvatarUrl = (raw) => {
  if (!raw) return null;
  let path = typeof raw === "string" ? raw : (raw.profile_image || raw.profileImage || raw.url || "");
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("blob:")) return path;

  const cleanPath = path.replace(/^\/+/, "");
  return API_BASE_URL ? `${API_BASE_URL}/${cleanPath}` : `/${cleanPath}`;
};

// Reads cached user immediately to prevent initials showing during page refresh
const getInitialUserData = () => {
  try {
    const cached = localStorage.getItem("user");
    if (!cached) return { name: "", email: "", role: "", profileImage: null };
    const data = JSON.parse(cached);
    const profile = data.profile || {};
    const rawImg = profile.profile_image || data.profile_image || data.profileImage || data.avatar_url;
    return {
      name: data.username || data.name || "User",
      email: data.email || "",
      role: data.role || "User",
      profileImage: formatAvatarUrl(rawImg),
    };
  } catch {
    return { name: "", email: "", role: "", profileImage: null };
  }
};

export default function Navbar({ searchQuery, setSearchQuery }) {
  const navigate = useNavigate();
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");

  const [isAdmin, setIsAdmin] = useState(false);
  const [currentUser, setCurrentUser] = useState(getInitialUserData);

  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const notificationRef = useRef(null);
  const profileMenuRef = useRef(null);

  const unreadCount = notifications.length;

  const fetchNotifications = async (isPolling = false) => {
    if (!token) return;
    try {
      const data = await apiRequest("/api/notifications");
      setNotifications(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching notifications:", error);
    }
  };

  const loadUserData = () => {
    if (!token) return;

    getCurrentUser(token)
      .then((res) => {
        if (res) {
          const data = res.user || res.data || res;
          const profile = data.profile || {};
          const isUserAdmin = data.is_admin || (data.role && data.role.toLowerCase() === 'admin');
          const rawImg = profile.profile_image || data.profile_image || data.profileImage || data.avatar_url;

          setIsAdmin(isUserAdmin);
          setCurrentUser((prev) => ({
            name: data.username || data.name || prev.name || "User",
            email: data.email || prev.email || "",
            role: data.role || (isUserAdmin ? "Admin" : "User"),
            profileImage: formatAvatarUrl(rawImg) || prev.profileImage,
          }));
        }
      })
      .catch((err) => console.error("Error fetching user info:", err));
  };

  useEffect(() => {
    loadUserData();

    const handleAvatarUpdate = (e) => {
      if (e.detail) {
        const formatted = formatAvatarUrl(e.detail);
        setCurrentUser((prev) => ({
          ...prev,
          profileImage: formatted,
        }));
      } else {
        loadUserData();
      }
    };

    window.addEventListener("user-avatar-updated", handleAvatarUpdate);
    fetchNotifications(false);
    const interval = setInterval(() => fetchNotifications(true), 15000);

    return () => {
      window.removeEventListener("user-avatar-updated", handleAvatarUpdate);
      clearInterval(interval);
    };
  }, [token]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleOpenLogoutModal = () => {
    setShowProfileMenu(false);
    setShowLogoutModal(true);
  };

  const confirmLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setIsAdmin(false);
    setCurrentUser({ name: "", email: "", role: "", profileImage: null });
    setShowLogoutModal(false);
    navigate("/login");
  };

  const getInitials = (name) => {
    if (!name) return "U";
    const parts = name.trim().split(" ");
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-gray-100 px-6 grid grid-cols-3 items-center sticky top-0 z-30 select-none shadow-sm">
        <div className="flex items-center gap-3">
          <button className="text-gray-400 hover:text-gray-600 transition cursor-pointer">
            <Menu className="w-5 h-5" />
          </button>

          <Link to="/" className="flex items-center gap-2 font-bold text-gray-900 text-lg tracking-tight">
            <img src="/logo.png" alt="MoringaHub Logo" className="w-8 h-8 object-contain rounded-lg" />
            MoringaHub
          </Link>
          
          {token && isAdmin && (
            <Link
              to="/admin"
              className="flex items-center gap-1.5 bg-orange-50 text-orange-600 border border-orange-200 px-2.5 py-1 rounded-lg text-xs font-semibold hover:bg-orange-100 transition"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Admin
            </Link>
          )}
        </div>

        <div className="w-full max-w-md justify-self-center">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search articles, videos, topics..."
              value={searchQuery || ""}
              onChange={(e) => setSearchQuery && setSearchQuery(e.target.value)}
              className="w-full bg-gray-50/80 border border-gray-100 rounded-full pl-10 pr-4 py-2 text-xs text-gray-800 placeholder-gray-400 focus:outline-none focus:bg-white focus:border-orange-400 transition"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          {token && (
            <>
              <Link
                to="/create"
                className="flex items-center gap-1.5 bg-orange-500 hover:bg-orange-600 text-white font-semibold px-4 py-1.5 rounded-full text-xs transition cursor-pointer shadow-sm"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                Create
              </Link>

              <div className="relative" ref={notificationRef}>
                <button
                  onClick={() => {
                    setShowNotifications(!showNotifications);
                    setShowProfileMenu(false);
                  }}
                  className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition cursor-pointer"
                  title="Notifications"
                >
                  <Bell className="w-4 h-4" />
                  {unreadCount > 0 && (
                    <span className="absolute top-1 right-1 bg-orange-500 text-white font-bold text-[9px] w-4 h-4 rounded-full flex items-center justify-center">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-100 rounded-2xl shadow-xl py-2 z-50">
                    <div className="px-4 py-2 border-b border-gray-100 flex justify-between items-center">
                      <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">Notifications</span>
                      <span className="text-[10px] bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full font-medium">
                        {notifications.length} total
                      </span>
                    </div>
                    <div className="max-h-64 overflow-y-auto divide-y divide-gray-50">
                      {notifications.length === 0 ? (
                        <div className="p-6 text-center text-xs text-gray-400">
                          No notifications yet.
                        </div>
                      ) : (
                        notifications.map(n => (
                          <div key={n.id || n.NotificationID} className="p-3 text-xs hover:bg-gray-50 transition cursor-pointer">
                            <p className="text-gray-700 leading-relaxed mb-1">{n.message || n.Message}</p>
                            <span className="text-[10px] text-gray-400 font-mono">{n.created_at || n.CreatedAt}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="relative" ref={profileMenuRef}>
                <button
                  onClick={() => {
                    setShowProfileMenu(!showProfileMenu);
                    setShowNotifications(false);
                  }}
                  className="flex items-center focus:outline-none group cursor-pointer"
                >
                  <div className="w-9 h-9 rounded-full overflow-hidden border border-gray-200 group-hover:border-orange-500 transition flex items-center justify-center bg-orange-100">
                    {currentUser.profileImage ? (
                      <img 
                        src={currentUser.profileImage} 
                        alt={currentUser.name} 
                        className="w-full h-full object-cover"
                        onError={() => setCurrentUser(prev => ({ ...prev, profileImage: null }))}
                      />
                    ) : (
                      <span className="text-orange-600 font-bold text-xs">
                        {getInitials(currentUser.name)}
                      </span>
                    )}
                  </div>
                </button>

                {showProfileMenu && (
                  <div className="absolute right-0 mt-2 w-60 bg-white border border-gray-100 rounded-2xl shadow-xl overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-sm font-bold text-gray-800 truncate">{currentUser.name || "User"}</p>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{currentUser.email}</p>
                      {currentUser.role && (
                        <span className="inline-block text-[10px] font-mono text-orange-600 mt-1 uppercase tracking-wide">
                          {currentUser.role}
                        </span>
                      )}
                    </div>

                    <div className="py-1 border-b border-gray-100">
                      <Link 
                        to="/profile" 
                        onClick={() => setShowProfileMenu(false)}
                        className="flex items-center px-4 py-2 text-xs text-gray-600 hover:bg-gray-50 transition"
                      >
                        <User className="w-4 h-4 mr-2.5 text-gray-400" />
                        My Profile
                      </Link>
                      <Link 
                        to="/saved" 
                        onClick={() => setShowProfileMenu(false)}
                        className="flex items-center px-4 py-2 text-xs text-gray-600 hover:bg-gray-50 transition"
                      >
                        <Bookmark className="w-4 h-4 mr-2.5 text-gray-400" />
                        Saved Content
                      </Link>
                    </div>

                    <div className="py-1">
                      <button 
                        onClick={handleOpenLogoutModal}
                        className="w-full flex items-center px-4 py-2 text-xs text-red-600 hover:bg-red-50 transition font-semibold cursor-pointer"
                      >
                        <LogOut className="w-4 h-4 mr-2.5 text-red-600" />
                        Logout
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {!token && (
            <button
              onClick={() => navigate("/login")}
              className="bg-orange-500 hover:bg-orange-600 text-white font-semibold text-xs px-4 py-1.5 rounded-full transition shadow-sm cursor-pointer"
            >
              Sign in
            </button>
          )}
        </div>
      </header>

      {showLogoutModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 text-center animate-in fade-in zoom-in duration-150">
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
              <LogOut className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-gray-900 mb-1">Confirm Sign Out</h3>
            <p className="text-xs text-gray-500 mb-6">Are you sure you want to log out of your account?</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={confirmLogout}
                className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl transition shadow-sm cursor-pointer"
              >
                Log Out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}