import { NavLink, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { X, Home, LayoutGrid, Bookmark, Bell, PlusCircle, ShieldCheck, User, LogOut, FlaskConical, Rss } from "lucide-react";
import { selectCurrentUser, selectIsPreview, setPreviewRole, logout } from "../features/auth/authSlice";

const NAV_ITEMS = [
  { to: "/", label: "Feed", icon: Home, end: true },
  { to: "/categories", label: "Categories", icon: LayoutGrid },
  { to: "/wishlist", label: "Wishlist", icon: Bookmark },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/create", label: "Post content", icon: PlusCircle },
];

export default function NavDrawer({ open, onClose }) {
  const user = useSelector(selectCurrentUser);
  const isPreview = useSelector(selectIsPreview);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  // Backend stores "Admin" (capital A) — compare case-insensitively so the
  // admin section actually shows for real admins.
  const isAdmin = String(user?.role || "").toLowerCase() === "admin";

  function handleLogout() {
    dispatch(logout());
    onClose();
    navigate("/login");
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/60 z-30 transition-opacity ${
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <aside
        className={`fixed top-0 left-0 h-screen w-72 bg-navy border-r border-navy-border z-40 flex flex-col py-5 px-4 transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between mb-6 px-1">
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center">
              <Rss className="w-3.5 h-3.5 text-slate-950" strokeWidth={2.25} />
            </span>
            <span className="font-display italic font-bold text-cream">MoringaHub</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-cream" aria-label="Close menu">
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition ${
                  isActive
                    ? "bg-brand-500/10 text-brand-600 font-medium"
                    : "text-slate-400 hover:text-cream hover:bg-navy-raised"
                }`
              }
            >
              <Icon className="w-4 h-4" strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}

          <NavLink
            to="/profile"
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition ${
                isActive
                  ? "bg-brand-500/10 text-brand-600 font-medium"
                  : "text-slate-400 hover:text-cream hover:bg-navy-raised"
              }`
            }
          >
            <User className="w-4 h-4" strokeWidth={1.75} />
            Profile
          </NavLink>

          {isAdmin && (
            <>
              <div className="pt-3 pb-1 px-3 text-[10px] font-mono uppercase tracking-wider text-slate-400">Admin</div>
              <NavLink
                to="/admin"
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition ${
                    isActive
                      ? "bg-sky-500/10 text-sky-400 font-medium"
                      : "text-slate-400 hover:text-cream hover:bg-navy-raised"
                  }`
                }
              >
                <ShieldCheck className="w-4 h-4" strokeWidth={1.75} />
                Admin dashboard
              </NavLink>
            </>
          )}
        </nav>

        {/* Dev-only: browse role-gated UI before real backend auth exists.
            Never shown in a production build. */}
        {isPreview && (
          <div className="border border-dashed border-navy-border rounded-lg p-3 mb-2">
            <p className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-2">
              <FlaskConical className="w-3.5 h-3.5 text-brand-500" /> Developer preview
            </p>
            <select
              value={user?.role}
              onChange={(e) => dispatch(setPreviewRole(e.target.value))}
              className="w-full bg-navy-raised border border-navy-border rounded-md text-slate-300 font-mono text-xs px-2 py-1.5 focus:outline-none"
            >
              <option value="admin">Preview as Admin</option>
              <option value="tech_writer">Preview as Tech Writer</option>
              <option value="user">Preview as User</option>
            </select>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:bg-navy-raised transition"
        >
          <LogOut className="w-4 h-4" strokeWidth={1.75} />
          Log out
        </button>
      </aside>
    </>
  );
}
