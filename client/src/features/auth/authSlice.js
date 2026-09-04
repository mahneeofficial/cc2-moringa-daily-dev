import { createSlice } from "@reduxjs/toolkit";

const storedUser = localStorage.getItem("user");
const storedToken = localStorage.getItem("token");

const initialState = {
  user: storedUser ? JSON.parse(storedUser) : null,
  token: storedToken || null,
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

      if (user) {
        localStorage.setItem("user", JSON.stringify(user));
      }
      if (token) {
        localStorage.setItem("token", token);
      }
    },

    setPreviewRole(state, action) {
      state.previewRole = action.payload;
    },

    logout(state) {
      state.user = null;
      state.token = null;
      state.previewRole = null;

      localStorage.removeItem("token");
      localStorage.removeItem("user");
    },

    hydrateFromStorage(state) {
      const storedUser = localStorage.getItem("user");
      const storedToken = localStorage.getItem("token");

      if (storedUser) {
        try {
          state.user = JSON.parse(storedUser);
        } catch {
          state.user = null;
          localStorage.removeItem("user");
        }
      }

      if (storedToken) {
        state.token = storedToken;
      }
    },
  },
});

export const {
  setUser,
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