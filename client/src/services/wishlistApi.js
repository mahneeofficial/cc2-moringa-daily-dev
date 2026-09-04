import apiRequest from "./api";

export async function listWishlist() {
  const data = await apiRequest("/api/users/me/wishlist");
  return Array.isArray(data) ? data : [];
}

export async function addToWishlist(contentId) {
  return apiRequest("/api/wishlist", {
    method: "POST",
    body: JSON.stringify({
      content_id: contentId,
    }),
  });
}

// The DELETE endpoint expects the wishlist ROW id, not the content id —
// so look the row up first (this was silently 404-ing before).
export async function removeFromWishlist(contentId) {
  const items = await listWishlist();
  const row = items.find(
    (item) =>
      String(item.contentId ?? item.content_id ?? item.ContentID) ===
      String(contentId)
  );

  const rowId = row ? row.id : contentId;

  return apiRequest(`/api/wishlist/${rowId}`, {
    method: "DELETE",
  });
}

export async function isWishlisted(contentId) {
  const items = await listWishlist();

  return items.some(
    (item) =>
      String(item.contentId ?? item.content_id ?? item.ContentID) ===
      String(contentId)
  );
}

export async function toggleWishlist(contentId, currentlyWishlisted) {
  if (currentlyWishlisted) {
    await removeFromWishlist(contentId);
    return false;
  }

  await addToWishlist(contentId);
  return true;
}
