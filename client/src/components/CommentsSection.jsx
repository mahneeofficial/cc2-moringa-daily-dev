import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { MessageSquare, Send, Reply, Trash2, Edit2, X, Check } from "lucide-react";
import {
  listComments,
  addComment,
  deleteComment,
  updateComment,
} from "../services/commentsApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import { timeAgo } from "../utils/format";

export default function CommentsSection({ contentId }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState("");
  const [loading, setLoading] = useState(false);

  const currentUser = useSelector(selectCurrentUser);
  const token = localStorage.getItem("token");

  useEffect(() => {
    if (!contentId) return;
    refreshComments();
  }, [contentId]);

  async function refreshComments() {
    try {
      const data = await listComments(contentId);
      setComments(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to fetch comments:", err);
    }
  }

  const handlePostComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    setLoading(true);
    try {
      await addComment(contentId, newComment.trim());
      setNewComment("");
      await refreshComments();
    } catch (err) {
      console.error("Error posting comment:", err);
    } finally {
      setLoading(false);
    }
  };

  const handlePostReply = async (parentId) => {
    if (!replyText.trim()) return;

    setLoading(true);
    try {
      await addComment(contentId, replyText.trim(), parentId);
      setReplyText("");
      setReplyingTo(null);
      await refreshComments();
    } catch (err) {
      console.error("Error posting reply:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (commentId) => {
    if (!editText.trim()) return;
    try {
      await updateComment(commentId, editText.trim());
      setEditingId(null);
      setEditText("");
      await refreshComments();
    } catch (err) {
      console.error("Error updating comment:", err);
    }
  };

  const handleDelete = async (commentId) => {
    if (!window.confirm("Are you sure you want to delete this comment?")) return;
    try {
      await deleteComment(commentId);
      await refreshComments();
    } catch (err) {
      console.error("Error deleting comment:", err);
    }
  };

  // Build root comments and nest sub-replies
  const rootComments = comments.filter((c) => {
    const parentId = c.parent_comment_id || c.parentCommentId || c.parentId;
    return !parentId;
  });

  const getReplies = (parentId) => {
    return comments.filter((c) => {
      const pid = c.parent_comment_id || c.parentCommentId || c.parentId;
      return String(pid) === String(parentId);
    });
  };

  const renderCommentCard = (comment, isReply = false) => {
    const commentId = comment.comment_id || comment.id || comment.CommentID;
    const authorName = comment.user?.username || comment.author?.username || "Anonymous";
    const authorId = comment.user_id || comment.userId || comment.user?.id || comment.author?.id;
    const body = comment.text || comment.body || "";
    const date = comment.created_at || comment.createdAt;

    const isOwnerOrAdmin =
      currentUser && (currentUser.id === authorId || currentUser.role?.toLowerCase() === "admin");

    return (
      <div
        key={commentId}
        className={`p-4 bg-[#0b0e14] border border-slate-800/80 rounded-xl space-y-2 ${
          isReply ? "ml-6 border-l-2 border-l-emerald-500/40" : ""
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {authorId ? (
              <Link
                to={`/profile/${authorId}`}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 hover:underline transition"
              >
                {authorName}
              </Link>
            ) : (
              <span className="text-xs font-semibold text-emerald-400">{authorName}</span>
            )}
            {date && <span className="text-[10px] text-slate-500 font-mono">{timeAgo ? timeAgo(date) : date}</span>}
          </div>

          <div className="flex items-center gap-2">
            {token && !isReply && (
              <button
                onClick={() => {
                  setReplyingTo(replyingTo === commentId ? null : commentId);
                  setReplyText("");
                }}
                className="text-[11px] text-slate-400 hover:text-emerald-400 flex items-center gap-1 cursor-pointer"
              >
                <Reply className="w-3 h-3" /> Reply
              </button>
            )}

            {isOwnerOrAdmin && (
              <>
                <button
                  onClick={() => {
                    setEditingId(commentId);
                    setEditText(body);
                  }}
                  className="text-[11px] text-slate-400 hover:text-white cursor-pointer"
                >
                  <Edit2 className="w-3 h-3" />
                </button>
                <button
                  onClick={() => handleDelete(commentId)}
                  className="text-[11px] text-slate-400 hover:text-red-400 cursor-pointer"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </>
            )}
          </div>
        </div>

        {editingId === commentId ? (
          <div className="space-y-2 mt-2">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full bg-[#121620] border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setEditingId(null)}
                className="p-1 text-slate-400 hover:text-white text-xs flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" /> Cancel
              </button>
              <button
                onClick={() => handleUpdate(commentId)}
                className="p-1 text-emerald-400 hover:text-emerald-300 text-xs flex items-center gap-1"
              >
                <Check className="w-3.5 h-3.5" /> Save
              </button>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">{body}</p>
        )}

        {replyingTo === commentId && (
          <div className="mt-3 pt-3 border-t border-slate-800 space-y-2">
            <textarea
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder={`Replying to @${authorName}...`}
              rows="2"
              className="w-full bg-[#121620] border border-slate-800 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setReplyingTo(null)}
                className="px-3 py-1 rounded-lg text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handlePostReply(commentId)}
                className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-3 py-1 rounded-lg transition"
              >
                {loading ? "Sending..." : "Reply"}
              </button>
            </div>
          </div>
        )}

        {!isReply && (
          <div className="space-y-2 mt-2">
            {getReplies(commentId).map((reply) => renderCommentCard(reply, true))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="mt-8 bg-[#121620] border border-slate-800 rounded-2xl p-6 shadow-xl text-slate-100">
      <div className="flex items-center gap-2 mb-6">
        <MessageSquare className="w-5 h-5 text-emerald-400" />
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
          Discussion ({comments.length})
        </h3>
      </div>

      {token ? (
        <form onSubmit={handlePostComment} className="mb-8">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="What are your thoughts?"
            rows="3"
            className="w-full bg-[#0b0e14] border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 transition resize-none mb-3"
          />
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs px-4 py-2 rounded-xl transition flex items-center gap-2 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              {loading ? "Posting..." : "Post Comment"}
            </button>
          </div>
        </form>
      ) : (
        <p className="text-xs text-slate-400 mb-6 bg-[#0b0e14] p-4 rounded-xl border border-slate-800">
          Please sign in to join the conversation.
        </p>
      )}

      <div className="space-y-4">
        {rootComments.length > 0 ? (
          rootComments.map((comment) => renderCommentCard(comment))
        ) : (
          <p className="text-xs text-slate-500 italic">
            No comments yet. Be the first to share your thoughts!
          </p>
        )}
      </div>
    </div>
  );
}