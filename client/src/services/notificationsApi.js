import apiRequest from "./api";

export async function listNotifications() {
  return apiRequest("/api/users/me/notifications");
}

export async function markRead(notificationId) {
  return apiRequest(`/api/users/me/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
}

export async function markAllRead() {
  return apiRequest("/api/users/me/notifications/read-all", {
    method: "PATCH",
  });
}

