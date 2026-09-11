import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Video, Headphones, FileText, Heart } from "lucide-react";
import { timeAgo } from "../../utils/format";
import { react } from "../../services/contentApi";

const TYPE_ICON = { video: Video, audio: Headphones, article: FileText };
const TYPE_LABEL = { video: "Video", audio: "Audio", article: "Article" };
const TYPE_TAG_COLOR = {
  video: "bg-blue-500/15 text-blue-400",
  audio: "bg-violet-500/15 text-violet-400",
  article: "bg-surface text-navy/70",
};

export default function ContentCard(props) {
  // Extract item safely whether passed as `item`, `post`, or `content`
  const currentItem = props?.item || props?.post || props?.content;

  // React hooks must run unconditionally
  const [likes, setLikes] = useState(() => Number(currentItem?.likes_count ?? currentItem?.likes ?? 0));
  const [liked, setLiked] = useState(() => Boolean(currentItem?.is_liked || currentItem?.isLiked));

  useEffect(() => {
    if (currentItem) {
      setLikes(Number(currentItem?.likes_count ?? currentItem?.likes ?? 0));
      setLiked(Boolean(currentItem?.is_liked || currentItem?.isLiked));
    }
  }, [currentItem]);

  // Guard check: return null if no item object was provided
  if (!currentItem || typeof currentItem !== "object") {
    return null;
  }

  // Safe property extraction
  const rawType = currentItem?.type || currentItem?.content_type || currentItem?.Type || "article";
  const normalizedType = String(rawType).toLowerCase();
  
  const TypeIcon = TYPE_ICON[normalizedType] || FileText;
  const typeLabel = TYPE_LABEL[normalizedType] || "Article";
  const tagColor = TYPE_TAG_COLOR[normalizedType] || TYPE_TAG_COLOR.article;
  
  const durationLabel = currentItem?.duration || currentItem?.readTime;
  const itemId = currentItem?.id || currentItem?.content_id || currentItem?.ContentID;

  async function handleLike(e) {
    e.preventDefault();
    e.stopPropagation();
    if (!itemId) return;

    const nextLiked = !liked;
    setLiked(nextLiked);
    setLikes((n) => Math.max(0, n + (nextLiked ? 1 : -1)));

    try {
      const summary = await react(itemId, "like");
      if (summary) {
        setLiked(summary.userReaction === "like");
        setLikes(summary.likes ?? summary.likes_count ?? likes);
      }
    } catch {
      // Revert on failure
      setLiked(!nextLiked);
      setLikes((n) => Math.max(0, n + (nextLiked ? -1 : 1)));
    }
  }

  return (
    <Link
      to={itemId ? `/content/${itemId}` : "#"}
      className="group block rounded-xl overflow-hidden border border-line bg-white hover:border-brand-500/50 hover:shadow-lg transition"
    >
      <div className="relative aspect-video bg-surface overflow-hidden">
        <img
          src={currentItem.thumbnail || currentItem.content_image || currentItem.media_url || ""}
          alt={currentItem.title || "Content thumbnail"}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-[1.02] transition duration-300"
        />
        {durationLabel && (
          <span className="absolute bottom-2.5 right-2.5 flex items-center gap-1 bg-black/80 text-white text-[11px] font-mono px-2 py-1 rounded-md">
            {durationLabel}
          </span>
        )}
        {currentItem.status && currentItem.status !== "Published" && currentItem.status !== "approved" && (
          <span className="absolute top-2.5 left-2.5 text-[10px] font-mono uppercase text-amber-300 bg-black/80 rounded px-1.5 py-0.5">
            {currentItem.status}
          </span>
        )}

        {/* Instagram-style like button */}
        <button
          onClick={handleLike}
          aria-label={liked ? "Unlike" : "Like"}
          className={`absolute bottom-2.5 left-2.5 flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[11px] font-semibold backdrop-blur transition ${
            liked
              ? "bg-red-500/90 text-white"
              : "bg-black/60 text-white hover:bg-black/80"
          }`}
        >
          <Heart
            className={`w-3.5 h-3.5 transition ${liked ? "fill-current scale-110" : ""}`}
          />
          {likes}
        </button>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2 mb-2.5">
          <span className={`flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded ${tagColor}`}>
            <TypeIcon className="w-3 h-3" strokeWidth={2} />
            {typeLabel}
          </span>
          {currentItem.category?.name && (
            <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-surface text-muted">
              {currentItem.category.name}
            </span>
          )}
        </div>

        <h3 className="font-display font-bold text-navy group-hover:text-brand-400 leading-snug text-lg transition">
          {currentItem.title}
        </h3>

        <div className="flex items-center gap-2 mt-3 text-xs text-muted">
          <span>{currentItem.author?.username || currentItem.author_name || "Author"}</span>
          {currentItem.createdAt && (
            <>
              <span>·</span>
              <span>{timeAgo(currentItem.createdAt)}</span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}