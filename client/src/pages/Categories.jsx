import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Check, Plus } from "lucide-react";
import { toggleCategorySubscription } from "../features/categories/categoriesSlice";
import { selectCurrentUser } from "../features/auth/authSlice";
import { categoryColor } from "../utils/categoryColors";

export default function Categories() {
  const user = useSelector(selectCurrentUser);
  const categories = useSelector((state) => state.categories.items);
  const subscribedIds = useSelector((state) => state.categories.subscribedIds);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-mono text-brand-500 mb-1">// categories</p>
        <h1 className="text-2xl font-bold text-navy">Subscribe to what you care about</h1>
        <p className="text-sm text-muted mt-1">
          Subscribed categories surface in your feed's recommended section and trigger notifications for new posts.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        {categories.map((cat) => {
          const colors = categoryColor(cat.name);
          const subscribed = subscribedIds.includes(cat.id);
          return (
            <div key={cat.id} className="p-4 rounded-xl border border-line bg-white flex flex-col gap-3">
              <div className="flex items-start justify-between">
                <div>
                  <span className={`text-sm font-display font-semibold ${colors.text}`}>{cat.name}</span>
                  <p className="text-xs text-muted mt-1">{cat.description}</p>
                </div>
                <button
                  onClick={() => {
                    if (!user?.id) {
                      navigate("/login?next=/categories");
                      return;
                    }
                    dispatch(toggleCategorySubscription({ categoryId: cat.id, userId: user.id }));
                  }}
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
                to={`/?category=${cat.id}`}
                className="text-[11px] font-mono text-muted hover:text-navy"
              >
                {cat.contentCount} post{cat.contentCount === 1 ? "" : "s"} →
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}

