import apiRequest from "./api";

export async function listSubscriptions() {
  return apiRequest("/api/subscriptions");
}

export async function subscribe(categoryId) {
  return apiRequest("/api/subscriptions", {
    method: "POST",
    body: JSON.stringify({
      category_id: categoryId,
    }),
  });
}

export async function unsubscribe(categoryId) {
  return apiRequest(`/api/subscriptions/${categoryId}`, {
    method: "DELETE",
  });
}
