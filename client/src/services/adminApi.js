import apiRequest from "./api";

function getAuthHeaders() {
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("jwt") ||
    localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function listUsers() {
  return apiRequest("/api/admin/users", {
    headers: { ...getAuthHeaders() },
  });
}

export async function addUser({ username, email, password, role }) {
  return apiRequest("/api/admin/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ username, email, password, role }),
  });
}

export async function toggleUserActive(id) {
  return apiRequest(`/api/admin/users/${id}/status`, {
    method: "PATCH",
    headers: { ...getAuthHeaders() },
  });
}

export async function listPendingContent() {
  return apiRequest("/api/admin/pending-content", {
    headers: { ...getAuthHeaders() },
  });
}

export async function listReports() {
  const data = await apiRequest("/api/reports", {
    headers: { ...getAuthHeaders() },
  });
  return Array.isArray(data) ? data : data?.items ?? [];
}

export async function resolveReport(id, status = "Resolved") {
  return apiRequest(`/api/reports/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ status }),
  });
}

export async function reportContent(contentId, userId, reason) {
  return apiRequest(`/api/content/${contentId}/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ reason }),
  });
}