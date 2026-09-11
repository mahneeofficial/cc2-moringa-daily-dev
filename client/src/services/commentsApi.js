import apiRequest from "./api";

function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function listComments(contentId) {
  const data = await apiRequest(`/api/content/${contentId}/comments`, {
    headers: { ...getAuthHeaders() },
  });
  if (Array.isArray(data)) return data;
  return data?.comments || data?.items || [];
}

export async function addComment(contentId, body, parentCommentId = null) {
  return apiRequest(`/api/content/${contentId}/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      text: body,
      body: body,
      content_id: contentId,
      contentId: contentId,
      parent_comment_id: parentCommentId,
      parentCommentId: parentCommentId,
    }),
  });
}

export async function updateComment(commentId, body) {
  return apiRequest(`/api/comments/${commentId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      text: body,
      body: body,
    }),
  });
}

export async function deleteComment(commentId) {
  return apiRequest(`/api/comments/${commentId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
}