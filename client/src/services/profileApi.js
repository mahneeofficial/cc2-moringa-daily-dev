import apiRequest from "./api";

export async function getProfile() {
  return apiRequest("/api/profiles/me");
}

export async function fetchProfile() {
  return getProfile();
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

