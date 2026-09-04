import apiRequest from "./api";

/**
 * Dedicated admin sign-in — hits /api/auth/admin/login, which only accepts
 * Admin-role accounts (the public /api/auth/login rejects admins).
 */
export async function adminLogin({ username, password }) {
  const data = await apiRequest("/api/auth/admin/login", {
    method: "POST",
    body: JSON.stringify({
      username,
      password,
    }),
  });

  if (data?.token) {
    localStorage.setItem("token", data.token);
  }

  if (data?.user) {
    localStorage.setItem("user", JSON.stringify(data.user));
  }

  return data;
}
