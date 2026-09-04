import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { listCategories } from "../../services/categoriesApi";
import {
  listSubscriptions,
  subscribe,
  unsubscribe,
} from "../../services/subscriptionsApi";

export const fetchCategories = createAsyncThunk(
  "categories/fetchAll",
  async () => {
    return await listCategories();
  }
);

export const fetchSubscriptions = createAsyncThunk(
  "categories/fetchSubscriptions",
  async () => {
    return await listSubscriptions();
  }
);

export const toggleCategorySubscription = createAsyncThunk(
  "categories/toggleSubscription",
  async ({ categoryId, subscribed }) => {
    if (subscribed) {
      await unsubscribe(categoryId);
    } else {
      await subscribe(categoryId);
    }

    return {
      categoryId,
      subscribed: !subscribed,
    };
  }
);

const categoriesSlice = createSlice({
  name: "categories",

  initialState: {
    items: [],
    subscribedIds: [],
    status: "idle",
  },

  reducers: {},

  extraReducers: (builder) => {
    builder
      .addCase(fetchCategories.pending, (state) => {
        state.status = "loading";
      })

      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.status = "succeeded";
        const payload = action.payload;
        state.items = Array.isArray(payload)
          ? payload
          : payload?.categories || payload?.items || [];
      })

      .addCase(fetchCategories.rejected, (state) => {
        state.status = "failed";
      })

      .addCase(fetchSubscriptions.fulfilled, (state, action) => {
        const payload = action.payload || [];
        const items = Array.isArray(payload) ? payload : payload.subscriptions || [];
        state.subscribedIds = items.map(
          (subscription) =>
            subscription.category_id ?? subscription.categoryId ?? subscription.CategoryID
        );
      })

      .addCase(toggleCategorySubscription.fulfilled, (state, action) => {
        const { categoryId, subscribed } = action.payload;

        if (subscribed) {
          if (!state.subscribedIds.includes(categoryId)) {
            state.subscribedIds.push(categoryId);
          }
        } else {
          state.subscribedIds = state.subscribedIds.filter(
            (id) => id !== categoryId
          );
        }
      });
  },
});

export default categoriesSlice.reducer;