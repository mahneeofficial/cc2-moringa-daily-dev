import apiRequest from "./api";

export async function register({ username, email, password, role = "user" }) {
  const sanitizedRole = role.toLowerCase() === "admin" ? "user" : role;

  const body = { username, email, password, role: sanitizedRole };

  return apiRequest("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function signUpUser(data) {
  return register(data);
}

export async function login({ username, password }) {
  const data = await apiRequest("/api/auth/login", {
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

export async function loginUser(data) {
  return login(data);
}

export async function logout() {
  try {
    await apiRequest("/api/auth/logout", {
      method: "POST",
    });
  } finally {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  }
}

// GET /api/me — retrieve user profile matching ERD (bio, interests, profile_image)
export async function getCurrentUser() {
  return apiRequest("/api/me");
}

// PUT /api/me — update ERD profile fields (bio, interests, profile_image)
export async function updateProfile(profileData) {
  return apiRequest("/api/me", {
    method: "PUT",
    body: JSON.stringify(profileData),
  });
}

// PUT /api/auth/change-password
export async function changePassword({ old_password, new_password }) {
  return apiRequest("/api/auth/change-password", {
    method: "PUT",
    body: JSON.stringify({ old_password, new_password }),
  });
}

export async function requestPasswordReset(email) {
  return apiRequest("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token, password) {
  return apiRequest("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      token,
      password,
    }),
  });
}