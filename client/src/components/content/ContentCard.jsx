import { useState } from "react";
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

export default function ContentCard({ item }) {
  const TypeIcon = TYPE_ICON[item.type] || FileText;
  const durationLabel = item.duration || item.readTime;

  const [likes, setLikes] = useState(item.likes_count ?? 0);
  const [liked, setLiked] = useState(Boolean(item.is_liked));

  // Instagram-style optimistic toggle: the heart flips instantly, the API
  // call follows, and we reconcile with the server's answer.
  async function handleLike(e) {
    e.preventDefault();
    e.stopPropagation();
    const nextLiked = !liked;
    setLiked(nextLiked);
    setLikes((n) => Math.max(0, n + (nextLiked ? 1 : -1)));
    try {
      const summary = await react(item.id, "like");
      if (summary) {
        setLiked(summary.userReaction === "like");
        setLikes(summary.likes ?? summary.likes_count ?? likes);
      }
    } catch {
      // revert on failure
      setLiked(!nextLiked);
      setLikes((n) => Math.max(0, n + (nextLiked ? -1 : 1)));
    }
  }

  return (
    <Link
      to={`/content/${item.id}`}
      className="group block rounded-xl overflow-hidden border border-line bg-white hover:border-brand-500/50 hover:shadow-lg transition"
    >
      <div className="relative aspect-video bg-surface overflow-hidden">
        <img
          src={item.thumbnail || item.content_image}
          alt=""
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-[1.02] transition duration-300"
        />
        {durationLabel && (
          <span className="absolute bottom-2.5 right-2.5 flex items-center gap-1 bg-black/80 text-white text-[11px] font-mono px-2 py-1 rounded-md">
            {durationLabel}
          </span>
        )}
        {item.status && item.status !== "Published" && item.status !== "approved" && (
          <span className="absolute top-2.5 left-2.5 text-[10px] font-mono uppercase text-amber-300 bg-black/80 rounded px-1.5 py-0.5">
            {item.status}
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
          <span className={`flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded ${TYPE_TAG_COLOR[item.type]}`}>
            <TypeIcon className="w-3 h-3" strokeWidth={2} />
            {TYPE_LABEL[item.type]}
          </span>
          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-surface text-muted">
            {item.category?.name}
          </span>
        </div>

        <h3 className="font-display font-bold text-navy group-hover:text-brand-400 leading-snug text-lg transition">
          {item.title}
        </h3>

        <div className="flex items-center gap-2 mt-3 text-xs text-muted">
          <span>{item.author?.username}</span>
          <span>·</span>
          <span>{timeAgo(item.createdAt)}</span>
        </div>
      </div>
    </Link>
  );
}
