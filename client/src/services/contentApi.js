import apiRequest from "./api";

export async function listContent({
  categoryId,
  search,
  status,
  includeAll = false,
} = {}) {
  const params = new URLSearchParams();

  if (categoryId) {
    params.set("category_id", categoryId);
  }

  if (search) {
    params.set("search", search);
  }

  if (status) {
    params.set("status", status);
  }

  if (includeAll) {
    params.set("status", "all");
  }

  const query = params.toString();

  const data = await apiRequest(`/api/content${query ? `?${query}` : ""}`);

  // The endpoint returns { items, pagination } — normalise to a plain array
  // so callers can always treat it like a list.
  if (Array.isArray(data)) return data;
  return data?.items ?? [];
}

export async function getContent(id) {
  return apiRequest(`/api/content/${id}`);
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
  const token = localStorage.getItem("token");

  const parsedCategoryId = categoryId ? parseInt(categoryId, 10) : null;
  const parsedAuthorId = authorId ? parseInt(authorId, 10) : null;

  const payload = {
    title: title,
    description: body || description || "",
    content_type: type || "article",
    type: type || "article",
    content_url: mediaUrl || url || "",
    mediaUrl: mediaUrl || url || "",
    category_id: parsedCategoryId,
    author_id: parsedAuthorId,
    // Schema field compatibility fallbacks
    Title: title,
    Description: body || description || "",
    Type: type || "article",
    CategoryID: parsedCategoryId,
    AuthorID: parsedAuthorId,
  };

  return apiRequest("/api/content", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Instagram-style post creation: multipart upload with media file,
 * thumbnail and caption. `file` is a File/Blob from a file input.
 */
export async function createPost({
  title,
  description,
  type = "Image",
  categoryId,
  file = null,
  thumbnail = null,
  summary = "",
  duration = "",
}) {
  const formData = new FormData();
  formData.append("title", title);
  formData.append("description", description || "");
  formData.append("content_type", type);
  if (categoryId) formData.append("category_id", categoryId);
  if (summary) formData.append("summary", summary);
  if (duration) formData.append("duration", duration);
  if (file) formData.append("media_file", file);
  if (thumbnail) formData.append("thumbnail", thumbnail);

  return apiRequest("/api/content", {
    method: "POST",
    body: formData,
  });
}

// Admin approve goes through the admin status endpoint — there is no
// /api/content/<id>/approve route on the backend.
export async function approveContent(id) {
  return apiRequest(`/api/admin/content/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: "Published" }),
  });
}

export async function rejectContent(id, reason = "") {
  return apiRequest(`/api/admin/content/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: "Rejected", reason }),
  });
}

export async function flagContent(id) {
  return apiRequest(`/api/content/${id}/flag`, {
    method: "PATCH",
  });
}

/**
 * React ("like" | "dislike") to a content item. Returns the new summary:
 * { likes, dislikes, userReaction }.
 */
export async function react(contentId, type) {
  return apiRequest(`/api/content/${contentId}/reactions`, {
    method: "POST",
    body: JSON.stringify({ type }),
  });
}

export async function reactionSummary(contentId) {
  return apiRequest(`/api/content/${contentId}/reactions`);
}

/**
 * Delete a post. The API allows the AUTHOR of the post or an admin —
 * everyone else gets a 403.
 */
export async function deleteContent(contentId) {
  return apiRequest(`/api/content/${contentId}`, {
    method: "DELETE",
  });
}
