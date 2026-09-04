import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useSelector } from "react-redux";
import { ThumbsUp, ThumbsDown, Bookmark, Share2, Flag, Video, Headphones, FileText, Check, Sparkles } from "lucide-react";
import {
  getContent,
  react,
  reactionSummary
} from "../services/contentApi";

import {
  toggleWishlist,
  isWishlisted
} from "../services/wishlistApi";
import { listComments, addComment, updateComment, deleteComment } from "../services/commentsApi";
import { reportContent } from "../services/adminApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import { categoryColor } from "../utils/categoryColors";
import { timeAgo } from "../utils/format";
import Avatar from "../components/ui/Avatar";
import RoleBadge from "../components/ui/RoleBadge";
import CommentThread from "../components/content/CommentThread";
import MediaPlayer from "../components/content/MediaPlayer";
import { ContentCardSkeleton } from "../components/ui/Skeleton";
import { API_BASE_URL } from "../services/api";

const TYPE_ICON = { video: Video, audio: Headphones, article: FileText };

export default function ContentDetail() {
  const { id } = useParams();
  const user = useSelector(selectCurrentUser);
  const [item, setItem] = useState(null);
  const [comments, setComments] = useState([]);
  const [reactionState, setReactionState] = useState({ likes: 0, dislikes: 0, userReaction: null });
  const [saved, setSaved] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  // AI Summary State
  const [summary, setSummary] = useState("");
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [contentItem, commentTree] = await Promise.all([
          getContent(id),
          listComments(id).catch(() => [])
        ]);
        if (cancelled) return;

        setItem(contentItem);
        setComments(commentTree || []);

        try {
          const summaryData = await reactionSummary(id);
          if (summaryData && !cancelled) setReactionState(summaryData);
        } catch (e) {
          console.warn("Could not load reactions summary:", e);
        }

        if (user?.id) {
          try {
            const wishlistStatus = await isWishlisted(id);
            if (!cancelled) setSaved(!!wishlistStatus);
          } catch (e) {
            console.warn("Could not load wishlist status:", e);
          }
        }
      } catch (err) {
        console.error("Failed to load content details:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id, user?.id]);

  async function handleReact(type) {
    if (!user) return alert("Please log in to react.");
    // FIX: this used to call react(id, user.id, type) — the extra user.id
    // argument shifted "type" out of place and the API received the numeric
    // user id as the reaction type, so every click failed with a 400.
    try {
      const summaryData = await react(id, type);
      if (summaryData) setReactionState(summaryData);
    } catch (e) {
      console.error("Reaction failed:", e);
    }
  }

  async function handleWishlist() {
    if (!user) return alert("Please log in to save items.");
    try {
      const nowSaved = await toggleWishlist(id, saved);
      setSaved(nowSaved);
    } catch (e) {
      console.error("Wishlist update failed:", e);
    }
  }

  async function handleShare() {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // Fallback
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleReport() {
    if (!user) return alert("Please log in to report content.");
    const reason = window.prompt("What's wrong with this content?");
    if (reason) {
      await reportContent(id, user.id, reason);
      window.alert("Thanks — this has been flagged for review.");
    }
  }

  // AI Summarize handler
  async function handleSummarize() {
    if (!item) return;
    setSummarizing(true);
    const bodyText = item.description || item.body || "";
    const prompt = `Summarize the following article into 3 concise bullet points:\n\nTitle: ${item.title}\nContent: ${bodyText}`;

    try {
      const res = await fetch(`${API_BASE_URL}/api/ai/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setSummary(data.result || "Could not generate summary.");
    } catch (err) {
      console.error("AI Summarize error:", err);
      setSummary("Error connecting to AI service.");
    } finally {
      setSummarizing(false);
    }
  }

  async function handleTopLevelComment(e) {
    e.preventDefault();
    if (!newComment.trim() || !user) return;
    await addComment(id,newComment.trim());
    setNewComment("");
    const tree = await listComments(id);
    setComments(tree);
  }

  async function handleReply(parentId, body) {
    if (!user) return;
    await addComment(id, body, parentId);
    const tree = await listComments(id);
    setComments(tree);
  }

  async function handleEditComment(commentId, newBody) {
    await updateComment(commentId, newBody);
    const tree = await listComments(id);
    setComments(tree);
  }

  async function handleDeleteComment(commentId) {
    await deleteComment(commentId);
    const tree = await listComments(id);
    setComments(tree);
  }

  if (loading) return <ContentCardSkeleton />;
  if (!item) return <p className="text-muted p-4">This post couldn't be found.</p>;

  const categoryName = item.categories?.[0]?.name || item.category?.name || "General";
  const colors = categoryColor(categoryName);
  const TypeIcon = TYPE_ICON[item.type] || FileText;
  const bodyText = item.description || item.body || "";
  const mediaUrl = item.url || item.mediaUrl;
  const createdAt = item.created_at || item.createdAt;
  const authorName = item.author?.username || `User #${item.author_id || item.authorId || ""}`;

  return (
    <article className="space-y-8">
      <div>
        <Link to="/" className="text-xs text-muted hover:text-navy">← Back to feed</Link>

        <div className="flex items-center gap-2 mt-4 mb-2">
          <span className={`text-[11px] font-mono uppercase tracking-wide ${colors.text}`}>{categoryName}</span>
          <span className="text-navy/70">·</span>
          <TypeIcon className="w-3.5 h-3.5 text-muted" />
          <span className="text-[11px] text-muted capitalize">{item.type}</span>
        </div>

        <h1 className="text-3xl font-display font-bold text-navy leading-tight">{item.title}</h1>

        <div className="flex items-center justify-between gap-2 mt-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Avatar username={authorName} role={item.author?.role} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-navy">{authorName}</span>
                <RoleBadge role={item.author?.role} />
              </div>
              <span className="text-[11px] text-muted font-mono">{timeAgo(createdAt)}</span>
            </div>
          </div>

          {/* AI Summarize Action Button */}
          <button
            onClick={handleSummarize}
            disabled={summarizing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-500/10 border border-brand-500/30 text-brand-600 rounded-lg text-xs font-semibold hover:bg-brand-500/20 transition disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5 text-brand-500" />
            {summarizing ? "Summarizing..." : "Summarize with AI"}
          </button>
        </div>
      </div>

      {/* AI Key Takeaways Summary Box */}
      {summary && (
        <div className="p-4 bg-brand-500/5 border-l-4 border-brand-500 rounded-r-xl space-y-1">
          <p className="text-xs font-bold uppercase tracking-wider text-brand-600 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" /> AI Key Takeaways
          </p>
          <div className="text-xs text-navy/80 leading-relaxed whitespace-pre-wrap">{summary}</div>
        </div>
      )}

      {/* Media: video/audio get the player; any other post with a media
          URL (image posts, articles with a cover file) renders the image.
          `url` is now ABSOLUTE from the API, so this works across origins. */}
      {(item.type === "video" || item.type === "audio") && mediaUrl && (
        <MediaPlayer type={item.type} url={mediaUrl} />
      )}
      {item.type !== "video" && item.type !== "audio" && mediaUrl && (
        <img
          src={mediaUrl}
          alt={item.title || "Post media"}
          className="w-full max-h-[540px] object-cover rounded-xl border border-line bg-slate-50"
          onError={(e) => { e.currentTarget.style.display = "none"; }}
        />
      )}

      <div className="prose-content text-navy/70 leading-relaxed whitespace-pre-line text-[15px]">
        {bodyText}
      </div>

      <div className="flex items-center gap-2 py-4 border-y border-line">
        <button
          onClick={() => handleReact("like")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            reactionState.userReaction === "like"
              ? "bg-brand-500/10 border-brand-500/40 text-brand-600"
              : "border-line text-muted hover:border-navy/30"
          }`}
        >
          <ThumbsUp className="w-3.5 h-3.5" /> {reactionState.likes || 0}
        </button>
        <button
          onClick={() => handleReact("dislike")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            reactionState.userReaction === "dislike"
              ? "bg-red-500/10 border-red-500/40 text-red-400"
              : "border-line text-muted hover:border-navy/30"
          }`}
        >
          <ThumbsDown className="w-3.5 h-3.5" /> {reactionState.dislikes || 0}
        </button>
        <button
          onClick={handleWishlist}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            saved ? "bg-brand-500/10 border-brand-500/40 text-brand-600" : "border-line text-muted hover:border-navy/30"
          }`}
        >
          <Bookmark className="w-3.5 h-3.5" /> {saved ? "Saved" : "Save"}
        </button>
        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-line text-muted hover:border-navy/30 transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
          {copied ? "Link copied" : "Share"}
        </button>
        <button
          onClick={handleReport}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted hover:text-red-400 ml-auto"
        >
          <Flag className="w-3.5 h-3.5" /> Report
        </button>
      </div>

      <section className="space-y-5">
        <h2 className="text-sm font-semibold text-navy/70">
          Discussion <span className="text-muted font-mono">({comments.length})</span>
        </h2>

        {user ? (
          <form onSubmit={handleTopLevelComment} className="flex gap-2">
            <Avatar username={user?.username} role={user?.role} size="sm" />
            <input
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Add to the discussion…"
              className="flex-1 px-3.5 py-2 rounded-lg bg-surface border border-line text-sm text-navy placeholder:text-navy/40 focus:outline-none focus:border-brand-500"
            />
            <button type="submit" className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-lg">
              Post
            </button>
          </form>
        ) : (
          <p className="text-xs text-muted">Log in to leave a comment.</p>
        )}

        <div className="space-y-5">
          {comments.length === 0 ? (
            <p className="text-sm text-muted">No comments yet — start the discussion.</p>
          ) : (
            comments.map((comment) => (
              <CommentThread
                key={comment.id}
                comment={comment}
                onReply={handleReply}
                onEdit={handleEditComment}
                onDelete={handleDeleteComment}
              />
            ))
          )}
        </div>
      </section>
    </article>
  );
}