import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { Bell, BellOff } from "lucide-react";
import { fetchNotifications, markNotificationRead, markAllNotificationsRead } from "../features/notifications/notificationsSlice";
import { selectCurrentUser } from "../features/auth/authSlice";
import { timeAgo } from "../utils/format";
import EmptyState from "../components/ui/EmptyState";
import Button from "../components/ui/Button";

export default function Notifications() {
  const user = useSelector(selectCurrentUser);
  const items = useSelector((state) => state.notifications.items);
  const dispatch = useDispatch();

  useEffect(() => {
    if (user?.id) dispatch(fetchNotifications(user.id));
  }, [dispatch, user?.id]);

  const unreadCount = items.filter((n) => !n.isRead).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono text-brand-500 mb-1">// notifications</p>
          <h1 className="text-2xl font-bold text-navy">Notifications</h1>
        </div>
        {unreadCount > 0 && (
          <Button variant="ghost" size="sm" onClick={() => user?.id && dispatch(markAllNotificationsRead(user.id))}>
            Mark all as read
          </Button>
        )}
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={BellOff}
          title="You're all caught up"
          description="Subscribe to categories to hear about new posts as they're published."
        />
      ) : (
        <div className="divide-y divide-line border border-line rounded-xl overflow-hidden">
          {items.map((n) => (
            <Link
              key={n.id}
              to={n.contentId ? `/content/${n.contentId}` : "#"}
              onClick={() => !n.isRead && dispatch(markNotificationRead(n.id))}
              className={`flex items-start gap-3 p-4 hover:bg-surface transition ${
                !n.isRead ? "bg-brand-500/5" : ""
              }`}
            >
              <Bell className={`w-4 h-4 mt-0.5 shrink-0 ${!n.isRead ? "text-brand-500" : "text-muted"}`} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${!n.isRead ? "text-navy" : "text-muted"}`}>{n.message}</p>
                <p className="text-[11px] text-muted font-mono mt-0.5">{timeAgo(n.createdAt)}</p>
              </div>
              {!n.isRead && <span className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

