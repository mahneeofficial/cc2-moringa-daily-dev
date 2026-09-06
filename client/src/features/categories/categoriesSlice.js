import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { listCategories } from "../../services/categoriesApi";
import {
  listSubscriptions,
  subscribe,
  unsubscribe,
} from "../../services/subscriptionsApi";

// 1. Fetch All Categories from backend
export const fetchCategories = createAsyncThunk(
  "categories/fetchAll",
  async (_, { rejectWithValue }) => {
    try {
      const data = await listCategories();
      return data;
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || err.message || "Failed to fetch categories"
      );
    }
  }
);

// 2. Fetch User Subscriptions from backend
export const fetchSubscriptions = createAsyncThunk(
  "categories/fetchSubscriptions",
  async (_, { rejectWithValue }) => {
    try {
      const data = await listSubscriptions();
      return data;
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || err.message || "Failed to fetch subscriptions"
      );
    }
  }
);

// 3. Toggle Category Subscription
export const toggleCategorySubscription = createAsyncThunk(
  "categories/toggleSubscription",
  async ({ categoryId, subscribed }, { getState, rejectWithValue }) => {
    try {
      const targetId = Number(categoryId);
      const currentSubscribedIds = getState().categories.subscribedIds.map(Number);

      const isCurrentlySubscribed =
        typeof subscribed === "boolean"
          ? subscribed
          : currentSubscribedIds.includes(targetId);

      if (isCurrentlySubscribed) {
        await unsubscribe(targetId);
      } else {
        await subscribe(targetId);
      }

      return {
        categoryId: targetId,
        subscribed: !isCurrentlySubscribed,
      };
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || err.message || "Failed to toggle subscription"
      );
    }
  }
);

const categoriesSlice = createSlice({
  name: "categories",

  initialState: {
    items: [],
    subscribedIds: [],
    status: "idle", // 'idle' | 'loading' | 'succeeded' | 'failed'
    error: null,
  },

  reducers: {},

  extraReducers: (builder) => {
    builder
      // --- Fetch Categories ---
      .addCase(fetchCategories.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.status = "succeeded";
        const payload = action.payload;
        const items = Array.isArray(payload)
          ? payload
          : payload?.categories || payload?.items || [];

        state.items = items;

        // Auto-extract and normalize subscriptions from category items
        const isSubscribedFromItems = items
          .filter((cat) => cat.is_subscribed)
          .map((cat) => Number(cat.id ?? cat.category_id ?? cat.CategoryID));

        if (isSubscribedFromItems.length > 0) {
          const combined = new Set([
            ...state.subscribedIds.map(Number),
            ...isSubscribedFromItems,
          ]);
          state.subscribedIds = Array.from(combined);
        }
      })
      .addCase(fetchCategories.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload || "Failed to load categories";
      })

      // --- Fetch Subscriptions ---
      .addCase(fetchSubscriptions.fulfilled, (state, action) => {
        const payload = action.payload || [];
        const items = Array.isArray(payload)
          ? payload
          : payload.subscriptions || payload.items || [];

        state.subscribedIds = items
          .map((sub) => sub.category_id ?? sub.categoryId ?? sub.CategoryID ?? sub.id)
          .filter((id) => id !== undefined && id !== null)
          .map(Number);
      })

      // --- Toggle Category Subscription ---
      .addCase(toggleCategorySubscription.fulfilled, (state, action) => {
        const { categoryId, subscribed } = action.payload;
        const numericId = Number(categoryId);

        // Update subscribedIds state array with normalized numbers
        if (subscribed) {
          if (!state.subscribedIds.map(Number).includes(numericId)) {
            state.subscribedIds.push(numericId);
          }
        } else {
          state.subscribedIds = state.subscribedIds
            .map(Number)
            .filter((id) => id !== numericId);
        }

        // Keep cat.is_subscribed flag in sync within state.items array
        state.items = state.items.map((cat) => {
          const catId = Number(cat.id ?? cat.category_id ?? cat.CategoryID);
          if (catId === numericId) {
            return { ...cat, is_subscribed: subscribed };
          }
          return cat;
        });
      });
  },
});

export default categoriesSlice.reducer;