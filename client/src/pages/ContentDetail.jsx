import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import {
  ThumbsUp,
  ThumbsDown,
  Bookmark,
  Share2,
  Flag,
  Video,
  Headphones,
  FileText,
  Check,
  Sparkles,
  Trash2
} from "lucide-react";

import {
  getContent,
  react,
  reactionSummary,
  deleteContent
} from "../services/contentApi";
import { toggleWishlist, isWishlisted } from "../services/wishlistApi";
import { reportContent } from "../services/adminApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import { categoryColor } from "../utils/categoryColors";
import { timeAgo } from "../utils/format";
import CommentsSection from "../components/CommentsSection";
import ReportModal from "../components/content/ReportModal";
import apiRequest from "../services/api";

const TYPE_ICON = { video: Video, audio: Headphones, article: FileText };

export default function ContentDetail() {
  const { id } = useParams();
  const user = useSelector(selectCurrentUser);
  const navigate = useNavigate();

  const [item, setItem] = useState(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [reactionState, setReactionState] = useState({ likes: 0, dislikes: 0, userReaction: null });
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  const [summary, setSummary] = useState("");
  const [summarizing, setSummarizing] = useState(false);

  // Moderation / Report Modal States
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);
  const [reportFeedback, setReportFeedback] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const contentItem = await getContent(id);
        if (cancelled) return;
        setItem(contentItem);

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

  async function handleDeletePost() {
    try {
      await deleteContent(id);
      navigate("/");
    } catch (err) {
      alert(err.message || "Could not delete this post.");
      setConfirmingDelete(false);
    }
  }

  function handleOpenReportModal() {
    if (!user) return alert("Please log in to report content.");
    setIsReportModalOpen(true);
  }

  async function handleReportSubmit(reportData) {
    setIsSubmittingReport(true);
    try {
      if (typeof reportContent === "function") {
        await reportContent(id, user.id, reportData.full_reason);
      } else {
        await apiRequest(`/api/content/${id}/report`, {
          method: "POST",
          body: reportData
        });
      }

      setIsReportModalOpen(false);
      setReportFeedback("Report submitted. You will receive a notification when admins review it.");
      setTimeout(() => setReportFeedback(""), 6000);
    } catch (err) {
      console.error("Report error:", err);
      alert(err.message || "Failed to submit report. Please try again.");
    } finally {
      setIsSubmittingReport(false);
    }
  }

  async function handleSummarize() {
    if (!item) return;
    setSummarizing(true);
    const bodyText = item.description || item.body || "";
    const promptText = `Summarize the following article into 3 concise bullet points:\n\nTitle: ${item.title}\nContent: ${bodyText}`;

    try {
      const data = await apiRequest("/api/ai/generate", {
        method: "POST",
        body: { prompt: promptText }
      });
      setSummary(data.result || "Could not generate summary.");
    } catch (err) {
      console.error("AI Summarize error:", err);
      setSummary(err.message || "Error connecting to AI service.");
    } finally {
      setSummarizing(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 animate-pulse space-y-4">
        <div className="h-4 w-24 bg-slate-800 rounded"></div>
        <div className="h-8 w-3/4 bg-slate-800 rounded"></div>
        <div className="h-64 w-full bg-slate-800 rounded-xl"></div>
      </div>
    );
  }

  if (!item) return <p className="text-slate-400 p-4">This post couldn't be found.</p>;

  const categoryName = item.categories?.[0]?.name || item.category?.name || "General";
  const colors = typeof categoryColor === "function" ? categoryColor(categoryName) : { text: "text-emerald-400" };
  const contentType = (item.type || item.contentType || "article").toLowerCase();
  const TypeIcon = TYPE_ICON[contentType] || FileText;
  const bodyText = item.description || item.body || "";
  const mediaUrl = item.url || item.mediaUrl || item.content_url;
  const createdAt = item.created_at || item.createdAt;

  const authorId = item.UserID || item.user_id || item.author_id || item.authorId;
  const authorName = item.author?.username || item.user?.username || `User #${authorId || ""}`;
  const authorRole = item.author?.role || item.user?.role;
  const isOwnerOrAdmin = user && (user.id === authorId || user.role?.toLowerCase() === "admin");

  return (
    <article className="space-y-8 max-w-4xl mx-auto p-4 text-slate-100">
      <div>
        <Link to="/" className="text-xs text-slate-400 hover:text-white transition">
          ← Back to feed
        </Link>

        {reportFeedback && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{reportFeedback}</span>
          </div>
        )}

        <div className="flex items-center gap-2 mt-4 mb-2">
          <span className={`text-[11px] font-mono uppercase tracking-wide ${colors?.text || "text-emerald-400"}`}>
            {categoryName}
          </span>
          <span className="text-slate-600">·</span>
          <TypeIcon className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px] text-slate-400 capitalize">{contentType}</span>
        </div>

        <h1 className="text-3xl font-bold text-slate-100 leading-tight">
          {item.title}
        </h1>

        <div className="flex items-center justify-between gap-2 mt-4 flex-wrap">
          {/* Author Profile Link */}
          <Link
            to={authorId ? `/profile/${authorId}` : "#"}
            className="flex items-center gap-3 group transition hover:opacity-90"
          >
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-xs border border-emerald-500/30 group-hover:border-emerald-400 transition">
              {authorName.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-slate-200 group-hover:text-emerald-400 group-hover:underline transition">
                  {authorName}
                </span>
                {authorRole && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 capitalize">
                    {authorRole}
                  </span>
                )}
              </div>
              <span className="text-[11px] text-slate-500 font-mono">{timeAgo(createdAt)}</span>
            </div>
          </Link>

          <button
            onClick={handleSummarize}
            disabled={summarizing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-lg text-xs font-semibold hover:bg-emerald-500/20 transition disabled:opacity-50 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {summarizing ? "Summarizing..." : "Summarize with AI"}
          </button>
        </div>
      </div>

      {summary && (
        <div className="p-4 bg-emerald-500/10 border-l-4 border-emerald-500 rounded-r-xl space-y-1">
          <p className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" /> AI Key Takeaways
          </p>
          <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
            {summary}
          </div>
        </div>
      )}

      {contentType === "video" && mediaUrl && (
        <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-slate-900 border border-slate-800">
          <video src={mediaUrl} controls className="w-full h-full object-contain" />
        </div>
      )}

      {contentType === "audio" && mediaUrl && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <audio src={mediaUrl} controls className="w-full" />
        </div>
      )}

      {contentType !== "video" && contentType !== "audio" && mediaUrl && (
        <img
          src={mediaUrl}
          alt={item.title || "Post media"}
          className="w-full max-h-[540px] object-cover rounded-xl border border-slate-800 bg-slate-900"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      )}

      <div className="text-slate-300 leading-relaxed whitespace-pre-line text-[15px]">
        {bodyText}
      </div>

      <div className="flex items-center gap-2 py-4 border-y border-slate-800">
        <button
          onClick={() => handleReact("like")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            reactionState.userReaction === "like"
              ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-400"
              : "border-slate-800 text-slate-400 hover:border-slate-600"
          }`}
        >
          <ThumbsUp className="w-3.5 h-3.5" /> {reactionState.likes || 0}
        </button>

        <button
          onClick={() => handleReact("dislike")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            reactionState.userReaction === "dislike"
              ? "bg-red-500/10 border-red-500/40 text-red-400"
              : "border-slate-800 text-slate-400 hover:border-slate-600"
          }`}
        >
          <ThumbsDown className="w-3.5 h-3.5" /> {reactionState.dislikes || 0}
        </button>

        <button
          onClick={handleWishlist}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            saved
              ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-400"
              : "border-slate-800 text-slate-400 hover:border-slate-600"
          }`}
        >
          <Bookmark className="w-3.5 h-3.5" /> {saved ? "Saved" : "Save"}
        </button>

        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-800 text-slate-400 hover:border-slate-600 transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
          {copied ? "Link copied" : "Share"}
        </button>

        <div className="flex items-center gap-2 ml-auto">
          {isOwnerOrAdmin && (
            confirmingDelete ? (
              <span className="flex items-center gap-2 text-[11px]">
                <span className="text-slate-400">Delete this post?</span>
                <button
                  onClick={handleDeletePost}
                  className="text-red-500 font-medium hover:underline"
                >
                  Yes
                </button>
                <button
                  onClick={() => setConfirmingDelete(false)}
                  className="text-slate-400 hover:underline"
                >
                  Cancel
                </button>
              </span>
            ) : (
              <button
                onClick={() => setConfirmingDelete(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-red-500 transition"
              >
                <Trash2 className="w-3.5 h-3.5" /> Delete
              </button>
            )
          )}

          <button
            onClick={handleOpenReportModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-red-500 transition"
          >
            <Flag className="w-3.5 h-3.5" /> Report
          </button>
        </div>
      </div>

      <CommentsSection contentId={id} />

      <ReportModal 
        isOpen={isReportModalOpen} 
        onClose={() => setIsReportModalOpen(false)} 
        onSubmit={handleReportSubmit} 
        isSubmitting={isSubmittingReport} 
      />
    </article>
  );
}