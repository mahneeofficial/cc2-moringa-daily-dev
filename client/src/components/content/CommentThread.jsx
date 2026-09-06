import { useState } from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { CornerDownRight, Pencil, Trash2 } from "lucide-react";
import { selectCurrentUser } from "../../features/auth/authSlice";
import { timeAgo } from "../../utils/format";
import Avatar from "../ui/Avatar";
import RoleBadge from "../ui/RoleBadge";

export default function CommentThread({ comment, onReply, onEdit, onDelete, depth = 0 }) {
  const currentUser = useSelector(selectCurrentUser);
  const [replying, setReplying] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(comment.body);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const isOwnComment = currentUser?.id === comment.author?.id;
  const canDelete = isOwnComment || currentUser?.role === "admin";

  async function submitReply(e) {
    e.preventDefault();
    if (!replyText.trim()) return;
    await onReply(comment.id, replyText.trim());
    setReplyText("");
    setReplying(false);
  }

  async function submitEdit(e) {
    e.preventDefault();
    if (!editText.trim() || editText === comment.body) {
      setEditing(false);
      return;
    }
    await onEdit(comment.id, editText.trim());
    setEditing(false);
  }

  async function confirmDelete() {
    await onDelete(comment.id);
    setConfirmingDelete(false);
  }

  const authorId = comment.author?.id;

  return (
    <div className={depth > 0 ? "ml-6 pl-4 border-l border-line" : ""}>
      <div className="flex gap-3">
        {/* Clickable Profile Avatar */}
        {authorId ? (
          <Link to={`/profile/${authorId}`}>
            <Avatar username={comment.author?.username} role={comment.author?.role} size="sm" />
          </Link>
        ) : (
          <Avatar username={comment.author?.username} role={comment.author?.role} size="sm" />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {/* Clickable Author Username */}
            {authorId ? (
              <Link
                to={`/profile/${authorId}`}
                className="text-sm font-medium text-navy hover:text-brand-500 hover:underline transition"
              >
                {comment.author?.username}
              </Link>
            ) : (
              <span className="text-sm font-medium text-navy">{comment.author?.username}</span>
            )}

            <RoleBadge role={comment.author?.role} />
            <span className="text-[11px] text-muted font-mono">{timeAgo(comment.createdAt)}</span>
            {comment.updatedAt && !comment.deleted && (
              <span className="text-[11px] text-muted italic">(edited)</span>
            )}
          </div>

          {editing ? (
            <form onSubmit={submitEdit} className="mt-1.5 flex gap-2">
              <input
                autoFocus
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-lg bg-white border border-line text-xs text-navy focus:outline-none focus:border-brand-500"
              />
              <button
                type="submit"
                className="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-lg"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setEditText(comment.body);
                }}
                className="px-3 py-1.5 bg-surface hover:bg-line/60 text-navy/70 text-xs rounded-lg"
              >
                Cancel
              </button>
            </form>
          ) : (
            <p className={`text-sm mt-0.5 ${comment.deleted ? "text-muted italic" : "text-navy/70"}`}>
              {comment.body}
            </p>
          )}

          {!comment.deleted && !editing && (
            <div className="flex items-center gap-3 mt-1.5">
              <button
                onClick={() => setReplying((v) => !v)}
                className="flex items-center gap-1 text-[11px] text-muted hover:text-brand-600"
              >
                <CornerDownRight className="w-3 h-3" /> Reply
              </button>
              {isOwnComment && (
                <button
                  onClick={() => setEditing(true)}
                  className="flex items-center gap-1 text-[11px] text-muted hover:text-brand-600"
                >
                  <Pencil className="w-3 h-3" /> Edit
                </button>
              )}
              {canDelete && !confirmingDelete && (
                <button
                  onClick={() => setConfirmingDelete(true)}
                  className="flex items-center gap-1 text-[11px] text-muted hover:text-red-400"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              )}
              {confirmingDelete && (
                <span className="flex items-center gap-2 text-[11px]">
                  <span className="text-muted">Delete this comment?</span>
                  <button onClick={confirmDelete} className="text-red-400 font-medium hover:underline">
                    Yes
                  </button>
                  <button onClick={() => setConfirmingDelete(false)} className="text-muted hover:underline">
                    Cancel
                  </button>
                </span>
              )}
            </div>
          )}

          {replying && (
            <form onSubmit={submitReply} className="mt-2 flex gap-2">
              <input
                autoFocus
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder={`Reply to ${comment.author?.username}…`}
                className="flex-1 px-3 py-1.5 rounded-lg bg-white border border-line text-xs text-navy focus:outline-none focus:border-brand-500"
              />
              <button
                type="submit"
                className="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-lg"
              >
                Reply
              </button>
            </form>
          )}

          {comment.replies?.length > 0 && (
            <div className="mt-3 space-y-3">
              {comment.replies.map((reply) => (
                <CommentThread
                  key={reply.id}
                  comment={reply}
                  onReply={onReply}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  depth={depth + 1}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}