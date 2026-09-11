import apiRequest from "./api";

function getAuthHeaders() {
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("jwt") ||
    localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function listWishlist() {
  const data = await apiRequest("/api/users/me/wishlist", {
    headers: { ...getAuthHeaders() },
  });
  if (Array.isArray(data)) return data;
  return data?.items || data?.wishlist || [];
}

export async function addToWishlist(contentId) {
  const parsedId = parseInt(contentId, 10) || contentId;

  return apiRequest("/api/wishlist", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      content_id: parsedId,
      contentId: parsedId,
      ContentID: parsedId,
    }),
  });
}

export async function removeFromWishlist(contentId) {
  let rowId = contentId;

  try {
    const items = await listWishlist();
    const row = items.find((item) => {
      const itemId =
        item.contentId ??
        item.content_id ??
        item.ContentID ??
        item.content?.id ??
        item.content?.content_id ??
        item.content?.ContentID;
      return String(itemId) === String(contentId);
    });

    if (row) {
      rowId = row.id ?? row.bookmark_id ?? row.wishlist_id ?? row.WishlistID ?? contentId;
    }
  } catch (err) {
    console.warn("Could not fetch list before removing bookmark, trying direct ID deletion:", err);
  }

  return apiRequest(`/api/wishlist/${rowId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
}

export async function isWishlisted(contentId) {
  try {
    const items = await listWishlist();
    return items.some((item) => {
      const itemId =
        item.contentId ??
        item.content_id ??
        item.ContentID ??
        item.content?.id ??
        item.content?.content_id ??
        item.content?.ContentID;
      return String(itemId) === String(contentId);
    });
  } catch (err) {
    console.warn("Error checking wishlist status:", err);
    return false;
  }
}

export async function toggleWishlist(contentId, currentlyWishlisted) {
  if (currentlyWishlisted) {
    await removeFromWishlist(contentId);
    return false;
  }

  await addToWishlist(contentId);
  return true;
}