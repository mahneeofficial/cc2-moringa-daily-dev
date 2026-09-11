import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Check, Plus, Loader2 } from "lucide-react";
import {
  fetchCategories,
  fetchSubscriptions,
  toggleCategorySubscription,
} from "../features/categories/categoriesSlice";
import { selectCurrentUser } from "../features/auth/authSlice";
import { categoryColor } from "../utils/categoryColors";

export default function Categories() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const user = useSelector(selectCurrentUser);
  const categories = useSelector((state) => state.categories.items || []);
  const subscribedIds = useSelector((state) => state.categories.subscribedIds || []);
  const status = useSelector((state) => state.categories.status);
  const error = useSelector((state) => state.categories.error);

  // Check if token exists in storage as a fallback if Redux user state is rehydrating
  const isAuthenticated = Boolean(
    user || localStorage.getItem("token") || localStorage.getItem("access_token")
  );

  useEffect(() => {
    dispatch(fetchCategories());
    if (isAuthenticated) {
      dispatch(fetchSubscriptions());
    }
  }, [dispatch, isAuthenticated]);

  const handleSubscribeClick = (catId, isSubscribed) => {
    if (!isAuthenticated) {
      navigate("/login?next=/categories");
      return;
    }

    dispatch(
      toggleCategorySubscription({
        categoryId: Number(catId),
        subscribed: isSubscribed,
      })
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-mono text-brand-500 mb-1">// categories</p>
        <h1 className="text-2xl font-bold text-navy">Subscribe to what you care about</h1>
        <p className="text-sm text-muted mt-1">
          Subscribed categories surface in your feed's recommended section and trigger notifications for new posts.
        </p>
      </div>

      {status === "loading" && categories.length === 0 ? (
        <div className="flex justify-center items-center py-20 text-muted">
          <Loader2 className="w-6 h-6 animate-spin mr-2 text-brand-500" />
          <span>Loading categories...</span>
        </div>
      ) : status === "failed" && categories.length === 0 ? (
        <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400">
          <p className="font-semibold">Error loading categories</p>
          <p className="text-xs mt-1">{error || "Could not fetch categories from server."}</p>
        </div>
      ) : categories.length === 0 ? (
        <div className="p-8 text-center text-muted border border-line rounded-xl">
          No categories found in the database.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {categories.map((cat) => {
            const rawCatId = cat.id ?? cat.category_id ?? cat.CategoryID;
            const catId = Number(rawCatId);
            const colors = categoryColor(cat.name);
            
            // Type-safe check against subscribedIds list or backend category property
            const subscribed =
              subscribedIds.map(Number).includes(catId) || Boolean(cat.is_subscribed);
            
            const postCount = cat.contentCount ?? cat.contents_count ?? 0;

            return (
              <div
                key={catId}
                className="p-4 rounded-xl border border-line bg-white flex flex-col gap-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className={`text-sm font-display font-semibold ${colors.text}`}>
                      {cat.name}
                    </span>
                    <p className="text-xs text-muted mt-1">{cat.description}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleSubscribeClick(catId, subscribed)}
                    className={`shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition ${
                      subscribed
                        ? "bg-brand-500/10 border-brand-500/40 text-brand-600"
                        : "border-line text-muted hover:border-slate-600"
                    }`}
                  >
                    {subscribed ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                    {subscribed ? "Subscribed" : "Subscribe"}
                  </button>
                </div>
                <Link
                  to={`/?category=${catId}`}
                  className="text-[11px] font-mono text-muted hover:text-navy"
                >
                  {postCount} post{postCount === 1 ? "" : "s"} →
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}