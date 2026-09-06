import apiRequest from "./api";

function getAuthHeaders() {
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("jwt") ||
    localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function formatContentType(type) {
  if (!type) return "Article";
  return type.charAt(0).toUpperCase() + type.slice(1).toLowerCase();
}

export async function listContent({
  categoryId,
  search,
  status,
  includeAll = false,
} = {}) {
  const params = new URLSearchParams();

  if (categoryId) params.set("category_id", categoryId);
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (includeAll) params.set("status", "all");

  const query = params.toString();
  const data = await apiRequest(`/api/content${query ? `?${query}` : ""}`, {
    headers: { ...getAuthHeaders() },
  });

  if (Array.isArray(data)) return data;
  return data?.items ?? [];
}

export async function getContent(id) {
  return apiRequest(`/api/content/${id}`, {
    headers: { ...getAuthHeaders() },
  });
}

export async function createContent({
  title,
  body,
  description,
  type,
  mediaUrl,
  url,
  categoryId,
  authorId,
}) {
  const parsedCategoryId = categoryId ? parseInt(categoryId, 10) : null;
  const parsedAuthorId = authorId ? parseInt(authorId, 10) : null;
  const contentBody = body || description || "";
  const contentUrl = mediaUrl || url || "";
  const contentType = formatContentType(type);

  const payload = {
    title,
    description: contentBody,
    body: contentBody,
    content_type: contentType,
    contentType,
    content_url: contentUrl,
    mediaUrl: contentUrl,
    category_id: parsedCategoryId,
    categoryId: parsedCategoryId,
    author_id: parsedAuthorId,
    authorId: parsedAuthorId,
    Title: title,
    Description: contentBody,
    ContentType: contentType,
    ContentURL: contentUrl,
    CategoryID: parsedCategoryId,
    AuthorID: parsedAuthorId,
  };

  return apiRequest("/api/content", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
}

export async function createPost({
  title,
  description,
  type = "Article",
  categoryId,
  file = null,
}) {
  const contentType = formatContentType(type);
  const formData = new FormData();

  formData.append("title", title);
  formData.append("Title", title);
  formData.append("description", description || "");
  formData.append("body", description || "");
  formData.append("Description", description || "");
  formData.append("content_type", contentType);
  formData.append("contentType", contentType);
  formData.append("ContentType", contentType);

  if (categoryId) {
    formData.append("category_id", categoryId);
    formData.append("categoryId", categoryId);
    formData.append("CategoryID", categoryId);
  }

  if (file) {
    formData.append("file", file);
    formData.append("media_file", file);
  }

  return apiRequest("/api/content", {
    method: "POST",
    headers: { ...getAuthHeaders() },
    body: formData,
  });
}

export async function approveContent(id) {
  return apiRequest(`/api/admin/content/${id}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ status: "Published" }),
  });
}

export async function rejectContent(id, reason = "") {
  return apiRequest(`/api/admin/content/${id}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ status: "Rejected", reason }),
  });
}

export async function flagContent(id) {
  return apiRequest(`/api/content/${id}/flag`, {
    method: "PATCH",
    headers: { ...getAuthHeaders() },
  });
}

export async function react(contentId, type) {
  return apiRequest(`/api/content/${contentId}/reactions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      type,
      reaction: type,
      reaction_type: type,
      Reaction: type,
    }),
  });
}

export async function reactionSummary(contentId) {
  return apiRequest(`/api/content/${contentId}/reactions`, {
    headers: { ...getAuthHeaders() },
  });
}

export async function deleteContent(contentId) {
  return apiRequest(`/api/content/${contentId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
}