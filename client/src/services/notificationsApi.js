import apiRequest from "./api";

export async function listNotifications() {
  return apiRequest("/api/notifications");
}

export async function getUnreadCount() {
  return apiRequest("/api/notifications/unread-count");
}

export async function markRead(notificationId) {
  return apiRequest(`/api/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
}

export async function markAllRead() {
  return apiRequest("/api/notifications/read-all", {
    method: "PATCH",
  });
}

export async function deleteNotificationApi(notificationId) {
  return apiRequest(`/api/notifications/${notificationId}`, {
    method: "DELETE",
  });
}

export async function clearAllNotificationsApi() {
  return apiRequest("/api/notifications/clear-all", {
    method: "DELETE",
  });
}