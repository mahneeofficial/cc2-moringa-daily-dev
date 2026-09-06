import apiRequest from "./api";

/**
 * Fetch a profile.
 * If userId is provided, fetches the public profile for that user (/api/profiles/:userId).
 * If no userId is provided, fetches the logged-in user's profile (/api/profiles/me).
 */
export async function getProfile(userId) {
  if (userId) {
    return apiRequest(`/api/profiles/${userId}`);
  }
  return apiRequest("/api/profiles/me");
}

export async function fetchProfile(userId) {
  return getProfile(userId);
}

export async function updateProfile({
  bio,
  interests,
  skills,
  github_url,
  profileImage,
}) {
  return apiRequest("/api/profiles/me", {
    method: "PUT",
    body: JSON.stringify({
      bio,
      interests,
      skills,
      github_url,
      profile_image: profileImage,
    }),
  });
}