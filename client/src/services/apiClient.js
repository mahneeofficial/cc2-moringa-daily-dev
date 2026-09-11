import apiRequest from "./api";

function formatUrl(url) {
  if (!url) return "/api";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("/api")) {
    return url;
  }
  return `/api${url.startsWith("/") ? "" : "/"}${url}`;
}

const apiClient = {
  get: (url, config = {}) =>
    apiRequest(formatUrl(url), { method: "GET", ...config }),

  post: (url, data, config = {}) =>
    apiRequest(formatUrl(url), { method: "POST", body: data, ...config }),

  put: (url, data, config = {}) =>
    apiRequest(formatUrl(url), { method: "PUT", body: data, ...config }),

  patch: (url, data, config = {}) =>
    apiRequest(formatUrl(url), { method: "PATCH", body: data, ...config }),

  delete: (url, config = {}) =>
    apiRequest(formatUrl(url), { method: "DELETE", ...config }),
};

export default apiClient;