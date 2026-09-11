const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5001"
).replace(/\/$/, "");

export { API_BASE_URL };

let handling401 = false;

function handleSessionExpired() {
  if (handling401) return;
  handling401 = true;

  localStorage.removeItem("token");
  localStorage.removeItem("access_token");
  localStorage.removeItem("jwt");
  localStorage.removeItem("accessToken");
  localStorage.removeItem("user");

  if (typeof window !== "undefined") {
    const current = window.location?.pathname || "/";
    const currentSearch = window.location?.search || "";
    const fullPath = current + currentSearch;
    const safeCurrent = current.startsWith("/login") ? "/" : fullPath;

    window.location.assign(
      `/login?session=expired&next=${encodeURIComponent(safeCurrent)}`
    );
  }
}

export async function apiRequest(endpoint, options = {}, { retried = false } = {}) {
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("jwt") ||
    localStorage.getItem("accessToken");

  // Build target URL (handles relative endpoints, absolute URLs, and empty base URLs safely)
  let url;
  if (endpoint.startsWith("http://") || endpoint.startsWith("https://")) {
    url = new URL(endpoint);
  } else {
    const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const base = API_BASE_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:5001");
    url = new URL(path, base);
  }

  // Append query parameters if passed in options.params
  if (options.params && typeof options.params === "object") {
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const customHeaders = { ...(options.headers || {}) };
  if (isFormData) {
    delete customHeaders["Content-Type"];
    delete customHeaders["content-type"];
  }

  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...customHeaders,
  };

  if (token && !headers.Authorization && !headers.authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  // Automatically stringify object bodies if not FormData, Blob, or URLSearchParams
  let body = options.body;
  if (
    body &&
    typeof body === "object" &&
    !isFormData &&
    !(body instanceof URLSearchParams) &&
    !(body instanceof Blob)
  ) {
    body = JSON.stringify(body);
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
    body,
  });

  if (response.status === 204) {
    return null;
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  const isAuthRoute =
    endpoint.includes("/login") ||
    endpoint.includes("/register") ||
    endpoint.includes("/auth/");

  // Redirect to login on 401 for any protected route
  if (response.status === 401 && !isAuthRoute && !retried) {
    handleSessionExpired();
    throw new Error("Your session has expired. Redirecting to login…");
  }

  // Schema auto-repair retry logic
  if (
    response.status === 503 &&
    data?.schema_repaired &&
    data?.retry &&
    !retried
  ) {
    return apiRequest(endpoint, options, { retried: true });
  }

  if (!response.ok) {
    let base = data?.error || data?.message || `Request failed with status ${response.status}`;
    if (typeof base === "object") {
      base = JSON.stringify(base);
    }
    const detail = data?.details
      ? ` (${typeof data.details === "object" ? JSON.stringify(data.details) : data.details})`
      : "";
    throw new Error(base + detail);
  }

  return data;
}

export default apiRequest;