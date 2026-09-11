import { createSlice } from "@reduxjs/toolkit";

const getStoredUser = () => {
  try {
    const item = localStorage.getItem("user");
    return item ? JSON.parse(item) : null;
  } catch {
    localStorage.removeItem("user");
    return null;
  }
};

const initialState = {
  user: getStoredUser(),
  token: localStorage.getItem("token") || null,
  previewRole: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setUser(state, action) {
      state.user = action.payload;
      if (action.payload) {
        localStorage.setItem("user", JSON.stringify(action.payload));
      } else {
        localStorage.removeItem("user");
      }
    },
    updateUser(state, action) {
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
      } else {
        state.user = action.payload;
      }
      if (state.user) {
        localStorage.setItem("user", JSON.stringify(state.user));
      }
    },
    setToken(state, action) {
      state.token = action.payload;
      if (action.payload) {
        localStorage.setItem("token", action.payload);
      } else {
        localStorage.removeItem("token");
      }
    },
    setCredentials(state, action) {
      const { user, token } = action.payload || {};
      state.user = user || null;
      state.token = token || null;

      if (user) localStorage.setItem("user", JSON.stringify(user));
      if (token) localStorage.setItem("token", token);
    },
    setPreviewRole(state, action) {
      state.previewRole = action.payload;
    },
    logout(state) {
      state.user = null;
      state.token = null;
      state.previewRole = null;
      localStorage.removeItem("token");
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
    },
    hydrateFromStorage(state) {
      state.user = getStoredUser();
      state.token = localStorage.getItem("token") || null;
    },
  },
});

export const {
  setUser,
  updateUser,
  setToken,
  setCredentials,
  setPreviewRole,
  logout,
  hydrateFromStorage,
} = authSlice.actions;

export default authSlice.reducer;

export function selectCurrentUser(state) {
  return state.auth?.user;
}

export function selectCurrentToken(state) {
  return state.auth?.token || localStorage.getItem("token");
}

export function selectIsPreview(state) {
  return Boolean(state.auth?.previewRole);
}

export function selectPreviewRole(state) {
  return state.auth?.previewRole;
}