import apiRequest from "./api";

export async function listCategories() {
  return apiRequest("/api/categories");
}

export async function createCategory({ name, description }) {
  return apiRequest("/api/categories", {
    method: "POST",
    body: { name, description },
  });
}

export async function updateCategory(id, { name, description }) {
  return apiRequest(`/api/categories/${id}`, {
    method: "PATCH",
    body: { name, description },
  });
}

export async function deleteCategory(id) {
  return apiRequest(`/api/categories/${id}`, {
    method: "DELETE",
  });
}

export async function subscribeCategory(id) {
  return apiRequest(`/api/categories/${id}/subscribe`, {
    method: "POST",
  });
}

export async function unsubscribeCategory(id) {
  return apiRequest(`/api/categories/${id}/unsubscribe`, {
    method: "DELETE",
  });
}