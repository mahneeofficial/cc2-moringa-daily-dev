import { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { Bookmark, Sparkles, FolderHeart } from "lucide-react";
import { Link } from "react-router-dom";
import { listWishlist } from "../services/wishlistApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import ContentCard from "../components/content/ContentCard";

export default function Wishlist() {
  const user = useSelector(selectCurrentUser);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    if (!user?.id) {
      setLoading(false);
      return;
    }

    setLoading(true);
    listWishlist()
      .then((data) => {
        if (cancelled) return;
        
        const rawList = Array.isArray(data) 
          ? data 
          : (data?.data || data?.items || data?.wishlist || []);

        const parsedItems = rawList
          .map((row) => {
            if (!row || typeof row !== "object") return null;
            
            let contentObj = null;
            
            if (row.content && typeof row.content === "object") {
              contentObj = row.content;
            } else if (row.Content && typeof row.Content === "object") {
              contentObj = row.Content;
            } else if (row.post && typeof row.post === "object") {
              contentObj = row.post;
            } else if (row.item && typeof row.item === "object") {
              contentObj = row.item;
            } else if (!("content" in row) && !("Content" in row)) {
              contentObj = row;
            }

            if (!contentObj || typeof contentObj !== "object") return null;
            
            const postId = contentObj.id || contentObj.content_id || contentObj.ContentID;
            const postTitle = contentObj.title || contentObj.Title;
            if (!postId && !postTitle) return null;

            return {
              ...contentObj,
              type: contentObj.type || contentObj.Type || contentObj.content_type || "article",
              is_bookmarked: true,
              isBookmarked: true,
              wishlistRowId: row.id || row.wishlist_id || row.WishlistID || row.bookmark_id,
            };
          })
          .filter(Boolean);

        setItems(parsedItems);
      })
      .catch((err) => {
        console.error("Failed to load wishlist:", err);
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  const handleItemUpdate = (updatedPost) => {
    if (!updatedPost) return;
    const updatedPostId = updatedPost.id || updatedPost.content_id || updatedPost.ContentID;
    
    if (updatedPost.is_bookmarked === false || updatedPost.isBookmarked === false) {
      setItems((prev) => prev.filter((item) => {
        const itemId = item?.id || item?.content_id || item?.ContentID;
        return String(itemId) !== String(updatedPostId);
      }));
    } else {
      setItems((prev) => prev.map((item) => {
        const itemId = item?.id || item?.content_id || item?.ContentID;
        return String(itemId) === String(updatedPostId) ? { ...item, ...updatedPost } : item;
      }));
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto p-4 sm:p-6 text-slate-100">
      <div className="bg-gradient-to-r from-emerald-950/80 via-slate-900 to-cyan-950/80 p-6 rounded-2xl border border-emerald-500/40 shadow-lg shadow-emerald-950/50 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-emerald-500/20 rounded-full blur-2xl pointer-events-none"></div>
        <div className="flex items-center gap-3 mb-2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 shadow-sm shadow-emerald-500/20">
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-emerald-400" /> saved_collection
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-200 to-cyan-400">
          Saved For Later
        </h1>
        <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-xl font-medium">
          Your personal library of bookmarked articles, tutorials, and tech posts.
        </p>
      </div>

      {loading ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-36 bg-slate-900/90 border border-emerald-500/20 rounded-2xl w-full"></div>
          <div className="h-36 bg-slate-900/90 border border-emerald-500/20 rounded-2xl w-full"></div>
        </div>
      ) : items.length === 0 ? (
        <div className="p-10 text-center bg-gradient-to-b from-slate-900 to-slate-950 border border-emerald-500/30 rounded-2xl shadow-xl space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-400/40 text-emerald-400 flex items-center justify-center mx-auto shadow-md shadow-emerald-500/20">
            <Bookmark className="w-7 h-7 text-emerald-400" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-100">Your wishlist is empty</h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-sm mx-auto">
              Bookmark interesting posts while exploring to keep them handy here whenever you need them.
            </p>
          </div>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 hover:from-emerald-300 hover:to-cyan-300 text-slate-950 font-bold text-xs sm:text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/25 active:scale-95"
          >
            <FolderHeart className="w-4 h-4 text-slate-950" />
            Browse the Feed
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item, index) => {
            if (!item) return null;
            const cardId = item.id || item.content_id || item.ContentID || item.wishlistRowId || index;
            return (
              <ContentCard 
                key={cardId} 
                post={item} 
                onUpdate={handleItemUpdate} 
              />
            );
          })}
        </div>
      )}
    </div>
  );
}