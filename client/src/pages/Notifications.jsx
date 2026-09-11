import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { 
  Bell, 
  BellOff, 
  Flag, 
  ShieldCheck, 
  ShieldAlert, 
  Loader2,
  Trash2
} from "lucide-react";
import { 
  fetchNotifications, 
  markNotificationRead, 
  markAllNotificationsRead,
  deleteNotification,
  clearAllNotifications,
  selectAllNotifications,
  selectNotificationsStatus,
  selectUnreadCount
} from "../features/notifications/notificationsSlice";
import { timeAgo } from "../utils/format";
import EmptyState from "../components/ui/EmptyState";
import Button from "../components/ui/Button";

function getNotificationMeta(type) {
  switch (type) {
    case "report_received":
      return {
        icon: <Flag className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />,
        badge: "Under Review",
        badgeStyle: "bg-amber-500/10 text-amber-500 border-amber-500/20"
      };
    case "report_feedback":
    case "report_resolved":
      return {
        icon: <ShieldCheck className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />,
        badge: "Admin Feedback",
        badgeStyle: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
      };
    case "content_removed":
      return {
        icon: <ShieldAlert className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />,
        badge: "Action Taken",
        badgeStyle: "bg-rose-500/10 text-rose-500 border-rose-500/20"
      };
    default:
      return {
        icon: <Bell className="w-4 h-4 text-brand-500 mt-0.5 shrink-0" />,
        badge: "Notification",
        badgeStyle: "bg-brand-500/10 text-brand-500 border-brand-500/20"
      };
  }
}

export default function Notifications() {
  const items = useSelector(selectAllNotifications);
  const status = useSelector(selectNotificationsStatus);
  const unreadCount = useSelector(selectUnreadCount);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // Fetch on mount without relying on user.id
  useEffect(() => {
    dispatch(fetchNotifications());
  }, [dispatch]);

  const handleItemClick = (notification) => {
    const isRead = notification.isRead || notification.is_read || notification.IsRead;
    const notifId = notification.id || notification.NotificationID;
    const targetContentId = notification.contentId || notification.content_id || notification.ContentID;

    if (!isRead) {
      dispatch(markNotificationRead(notifId));
    }
    if (targetContentId) {
      navigate(`/content/${targetContentId}`);
    }
  };

  const handleMarkAllRead = () => {
    if (unreadCount > 0) {
      dispatch(markAllNotificationsRead());
    }
  };

  const handleDeleteOne = (e, id) => {
    e.stopPropagation();
    dispatch(deleteNotification(id));
  };

  const handleClearAll = () => {
    if (items.length > 0) {
      dispatch(clearAllNotifications());
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono text-brand-500 mb-1">// notifications</p>
          <h1 className="text-2xl font-bold text-navy">Notifications</h1>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={handleMarkAllRead}>
              Mark all as read
            </Button>
          )}
          {items.length > 0 && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleClearAll}
              className="text-rose-500 hover:text-rose-600 hover:bg-rose-50"
            >
              Clear all
            </Button>
          )}
        </div>
      </div>

      {status === "loading" && items.length === 0 ? (
        <div className="flex items-center justify-center py-12 text-muted">
          <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading notifications...
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={BellOff}
          title="You're all caught up"
          description="Subscribe to categories to hear about new posts or monitor your submit history."
        />
      ) : (
        <div className="divide-y divide-line border border-line rounded-xl overflow-hidden bg-white">
          {items.map((n) => {
            const notifId = n.id || n.NotificationID;
            const isRead = n.isRead || n.is_read || n.IsRead;
            const message = n.message || n.Message;
            const createdAt = n.createdAt || n.created_at || n.CreatedAt;
            const type = n.type || n.Type;

            const { icon, badge, badgeStyle } = getNotificationMeta(type);

            return (
              <div
                key={notifId}
                onClick={() => handleItemClick(n)}
                className={`flex items-center justify-between gap-3.5 p-4 transition cursor-pointer hover:bg-surface ${
                  !isRead ? "bg-brand-500/5" : ""
                }`}
              >
                <div className="flex items-start gap-3.5 min-w-0 flex-1">
                  {icon}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${badgeStyle}`}>
                        {badge}
                      </span>
                      <span className="text-[11px] text-muted font-mono">{timeAgo(createdAt)}</span>
                    </div>
                    <p className={`text-sm leading-snug ${!isRead ? "text-navy font-medium" : "text-muted"}`}>
                      {message}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {!isRead && <span className="w-2 h-2 rounded-full bg-brand-500" />}
                  <button
                    onClick={(e) => handleDeleteOne(e, notifId)}
                    className="p-1.5 text-gray-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition cursor-pointer"
                    title="Delete notification"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}