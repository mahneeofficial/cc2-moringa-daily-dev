const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";

// Shared so every component (AI widgets etc.) talks to the same backend —
// deploy only needs VITE_API_BASE_URL set at build time.
export { API_BASE_URL };

// ---------------------------------------------------------------------------
// Global auth-session handling
// ---------------------------------------------------------------------------
// A stale/expired token used to surface as random 401s from reactions,
// subscriptions, etc. Now the FIRST 401 clears the dead session and sends
// the user to the login page once, instead of failing silently everywhere.
let handling401 = false;

function handleSessionExpired() {
  if (handling401) return;
  handling401 = true;
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  // Preserve where they were so login can bring them back.
  if (typeof window !== "undefined") {
    const current = window.location?.pathname || "/";
    const safeCurrent = current === "/login" ? "/" : current;
    window.location.assign(`/login?session=expired&next=${encodeURIComponent(safeCurrent)}`);
  }
}

export async function apiRequest(endpoint, options = {}, { retried = false } = {}) {
  const token = localStorage.getItem("token");

  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  // Never set Content-Type for FormData — the browser must add the boundary.
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  // Stale/expired token → clear session and redirect to login once.
  // (But never for the login endpoints themselves — a wrong password there
  // is a legit 401 the form needs to show.)
  if (
    response.status === 401 &&
    token &&
    !endpoint.includes("/auth/login") &&
    !retried
  ) {
    handleSessionExpired();
    throw new Error("Your session has expired. Redirecting to login…");
  }

  // The backend repairs DB schema drift automatically and answers 503 with
  // retry: true — replay the request once so the user never sees the error.
  // (Safe for POSTs too: the 503 means the request never completed.)
  if (
    response.status === 503 &&
    data?.schema_repaired &&
    data?.retry &&
    !retried
  ) {
    return apiRequest(endpoint, options, { retried: true });
  }

  if (!response.ok) {
    // Include the backend's `details` when present so schema/config errors
    // are visible in the UI instead of a generic message.
    const base =
      data?.error ||
      data?.message ||
      `Request failed with status ${response.status}`;
    const detail = data?.details ? ` (${data.details})` : "";
    throw new Error(base + detail);
  }

  return data;
}

export default apiRequest;
