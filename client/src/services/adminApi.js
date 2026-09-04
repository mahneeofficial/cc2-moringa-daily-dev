import apiRequest from "./api";

// NOTE: this used to call `api.get(...)` on the fetch-based api.js wrapper
// (which has no .get/.post helpers) and pointed at URLs that don't exist on
// the backend. Everything now goes through apiRequest + the real /api/admin
// routes.

// GET /api/admin/users
export async function listUsers() {
  return apiRequest("/api/admin/users");
}

// POST /api/admin/users
export async function addUser({ username, email, password, role }) {
  return apiRequest("/api/admin/users", {
    method: "POST",
    body: JSON.stringify({ username, email, password, role }),
  });
}

// PATCH /api/admin/users/:id/status (toggles active/deactivated)
export async function toggleUserActive(id) {
  return apiRequest(`/api/admin/users/${id}/status`, {
    method: "PATCH",
  });
}

// GET /api/admin/pending-content — returns a direct array
export async function listPendingContent() {
  return apiRequest("/api/admin/pending-content");
}

// GET /api/reports
export async function listReports() {
  const data = await apiRequest("/api/reports");
  return Array.isArray(data) ? data : data?.items ?? [];
}

// PATCH /api/reports/:id
export async function resolveReport(id, status = "Resolved") {
  return apiRequest(`/api/reports/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// POST /api/content/:id/report
export async function reportContent(contentId, userId, reason) {
  return apiRequest(`/api/content/${contentId}/report`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
