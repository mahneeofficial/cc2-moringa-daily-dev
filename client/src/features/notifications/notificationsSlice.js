import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import {
  listNotifications,
  markRead,
  markAllRead,
  deleteNotificationApi,
  clearAllNotificationsApi,
} from "../../services/notificationsApi";

export const fetchNotifications = createAsyncThunk(
  "notifications/fetchAll",
  async () => {
    return await listNotifications();
  }
);

export const markNotificationRead = createAsyncThunk(
  "notifications/markRead",
  async (id) => {
    await markRead(id);
    return id;
  }
);

export const markAllNotificationsRead = createAsyncThunk(
  "notifications/markAllRead",
  async () => {
    await markAllRead();
  }
);

export const deleteNotification = createAsyncThunk(
  "notifications/deleteOne",
  async (id) => {
    await deleteNotificationApi(id);
    return id;
  }
);

export const clearAllNotifications = createAsyncThunk(
  "notifications/clearAll",
  async () => {
    await clearAllNotificationsApi();
  }
);

const notificationsSlice = createSlice({
  name: "notifications",

  initialState: {
    items: [],
    status: "idle",
    error: null,
  },

  reducers: {},

  extraReducers: (builder) => {
    builder
      .addCase(fetchNotifications.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })

      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.status = "succeeded";
        // Handles both direct arrays and object responses like { notifications: [...] }
        const data = action.payload;
        if (Array.isArray(data)) {
          state.items = data;
        } else if (data && Array.isArray(data.notifications)) {
          state.items = data.notifications;
        } else if (data && Array.isArray(data.data)) {
          state.items = data.data;
        } else {
          state.items = [];
        }
      })

      .addCase(fetchNotifications.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message || "Failed to fetch notifications";
      })

      .addCase(markNotificationRead.fulfilled, (state, action) => {
        const notification = state.items.find(
          (n) => String(n.id || n.NotificationID) === String(action.payload)
        );

        if (notification) {
          notification.isRead = true;
          notification.is_read = true;
          notification.IsRead = true;
        }
      })

      .addCase(markAllNotificationsRead.fulfilled, (state) => {
        state.items.forEach((notification) => {
          notification.isRead = true;
          notification.is_read = true;
          notification.IsRead = true;
        });
      })

      .addCase(deleteNotification.fulfilled, (state, action) => {
        state.items = state.items.filter(
          (n) => String(n.id || n.NotificationID) !== String(action.payload)
        );
      })

      .addCase(clearAllNotifications.fulfilled, (state) => {
        state.items = [];
      });
  },
});

export default notificationsSlice.reducer;

// Selectors
export const selectAllNotifications = (state) => state.notifications.items || [];
export const selectNotificationsStatus = (state) => state.notifications.status;
export const selectUnreadCount = (state) =>
  (state.notifications.items || []).filter(
    (n) => !n.isRead && !n.is_read && !n.IsRead
  ).length;