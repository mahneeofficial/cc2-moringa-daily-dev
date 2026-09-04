import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Image as ImageIcon,
  Video,
  Music,
  X,
  Upload,
  Send,
  CheckCircle2,
  Clock,
  FileText,
} from "lucide-react";
import { listCategories } from "../services/categoriesApi";
import { createPost } from "../services/contentApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import { useSelector } from "react-redux";

const ACCEPTED = {
  image: ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"],
  video: ["video/mp4", "video/webm", "video/quicktime"],
  audio: ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg"],
};

function detectKind(file) {
  if (!file) return null;
  for (const [kind, mimes] of Object.entries(ACCEPTED)) {
    if (mimes.includes(file.type)) return kind;
  }
  return null;
}

export default function CreatePost() {
  const navigate = useNavigate();
  const user = useSelector(selectCurrentUser);
  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [caption, setCaption] = useState("");
  const [title, setTitle] = useState("");
  const [categories, setCategories] = useState([]);
  const [categoryId, setCategoryId] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // { id, status } after success

  useEffect(() => {
    listCategories()
      .then((data) => {
        const list = Array.isArray(data) ? data : data?.items ?? [];
        setCategories(list);
        if (list.length > 0) {
          setCategoryId(
            String(list[0].id ?? list[0].CategoryID ?? list[0].category_id)
          );
        }
      })
      .catch(() => setCategories([]));
  }, []);

  // Revoke object URLs so previews don't leak memory
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const fileKind = detectKind(file);

  function handleFile(f) {
    const kind = detectKind(f);
    if (!f) return;
    if (!kind) {
      setError("Unsupported file type. Use an image, video or audio file.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("File is too large — keep it under 50 MB.");
      return;
    }
    setError("");
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  }

  function clearFile() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!file && !caption.trim()) {
      setError("Add a photo/video or write something first.");
      return;
    }
    if (!categoryId) {
      setError("Pick a category for your post.");
      return;
    }

    // Instagram-style: no separate title form — derive it from the caption.
    const derivedTitle =
      title.trim() ||
      caption.trim().split("\n")[0].slice(0, 80) ||
      `${user?.username || "Someone"}'s new ${fileKind || "post"}`;

    const type = fileKind
      ? fileKind.charAt(0).toUpperCase() + fileKind.slice(1) // Image | Video | Audio
      : "Article";

    setSubmitting(true);
    try {
      const data = await createPost({
        title: derivedTitle,
        description: caption,
        type,
        categoryId,
        file,
      });
      setResult({
        id: data?.content_id ?? data?.id ?? null,
        status: data?.status ?? "Pending",
        reason: data?.publish_reason || null,
      });
    } catch (err) {
      setError(err.message || "Failed to create post.");
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Success screen (like Instagram's "Post shared") ----------
  if (result) {
    const published = result.status === "Published";
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-6">
        <div
          className={`w-16 h-16 rounded-2xl mx-auto flex items-center justify-center border ${
            published
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-500"
              : "bg-amber-500/10 border-amber-500/30 text-amber-500"
          }`}
        >
          {published ? (
            <CheckCircle2 className="w-8 h-8" />
          ) : (
            <Clock className="w-8 h-8" />
          )}
        </div>

        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-navy">
            {published ? "Your post is live!" : "Sent for review"}
          </h1>
          <p className="text-sm text-muted">
            {published
              ? "Everyone in the community can see it right now."
              : "An admin will review it shortly — it goes live once approved."}
          </p>
          {result.reason && (
            <p className="text-[11px] text-muted font-mono pt-1">
              {result.reason}
            </p>
          )}
        </div>

        <div className="flex gap-2 justify-center">
          {result.id && (
            <button
              onClick={() => navigate(`/content/${result.id}`)}
              className="px-5 py-2.5 rounded-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold transition"
            >
              View post
            </button>
          )}
          <Link
            to="/"
            className="px-5 py-2.5 rounded-full border border-line bg-white text-navy/70 hover:text-navy text-sm font-semibold transition"
          >
            Back to feed
          </Link>
        </div>
      </div>
    );
  }

  // ---------- Composer ----------
  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-brand-500 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to feed
        </Link>
        <Link
          to="/create-article"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-brand-500 transition"
        >
          <FileText className="w-4 h-4" /> Long-form article editor
        </Link>
      </div>

      <div className="bg-white border border-line rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-line">
          <h1 className="font-display font-bold text-navy">Create new post</h1>
          <span className="text-[11px] font-mono text-muted">
            {user?.username}
          </span>
        </div>

        {error && (
          <div className="mx-5 mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid md:grid-cols-2">
          {/* Left: media dropzone / preview */}
          <div className="p-5">
            {previewUrl ? (
              <div className="relative rounded-xl overflow-hidden border border-line bg-surface aspect-square flex items-center justify-center">
                {fileKind === "video" ? (
                  <video
                    src={previewUrl}
                    controls
                    className="w-full h-full object-contain"
                  />
                ) : fileKind === "audio" ? (
                  <div className="flex flex-col items-center gap-3 text-muted">
                    <Music className="w-10 h-10" />
                    <audio src={previewUrl} controls />
                  </div>
                ) : (
                  <img
                    src={previewUrl}
                    alt="Selected"
                    className="w-full h-full object-cover"
                  />
                )}
                <button
                  type="button"
                  onClick={clearFile}
                  className="absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-black/70 text-white flex items-center justify-center hover:bg-black/90 transition"
                  aria-label="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  handleFile(e.dataTransfer.files?.[0]);
                }}
                className={`w-full aspect-square rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-3 transition ${
                  dragOver
                    ? "border-brand-500 bg-brand-500/5"
                    : "border-line bg-surface hover:border-brand-500/50"
                }`}
              >
                <div className="w-14 h-14 rounded-2xl bg-brand-500/10 text-brand-500 flex items-center justify-center">
                  <Upload className="w-6 h-6" />
                </div>
                <div className="text-center px-6">
                  <p className="text-sm font-semibold text-navy">
                    Drag & drop, or click to upload
                  </p>
                  <p className="text-[11px] text-muted mt-1">
                    Images · Videos · Audio (max 50 MB)
                  </p>
                </div>
                <div className="flex gap-3 text-muted">
                  <ImageIcon className="w-4 h-4" />
                  <Video className="w-4 h-4" />
                  <Music className="w-4 h-4" />
                </div>
              </button>
            )}

            <input
              ref={inputRef}
              type="file"
              accept="image/*,video/*,audio/*"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />

            <p className="text-[11px] text-muted mt-3 text-center">
              {file
                ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`
                : "No media selected — your post will be a text post."}
            </p>
          </div>

          {/* Right: caption + category */}
          <div className="p-5 md:border-l md:border-line flex flex-col gap-4">
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-muted mb-1.5">
                Caption
              </label>
              <textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="Write a caption… #hashtags welcome"
                rows={6}
                className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-line text-sm text-navy placeholder:text-navy/40 focus:outline-none focus:border-brand-500 resize-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-muted mb-1.5">
                Title <span className="normal-case font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Auto-generated from your caption if empty"
                className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-line text-sm text-navy placeholder:text-navy/40 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-muted mb-1.5">
                Category
              </label>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((cat) => {
                  const id = String(cat.id ?? cat.CategoryID ?? cat.category_id);
                  const name = cat.name ?? cat.Name;
                  const active = categoryId === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setCategoryId(id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                        active
                          ? "border-brand-500 text-brand-600 bg-brand-500/10"
                          : "border-line text-navy/60 bg-white hover:border-navy/30"
                      }`}
                    >
                      {name}
                    </button>
                  );
                })}
                {categories.length === 0 && (
                  <p className="text-xs text-muted">Loading categories…</p>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="mt-auto w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-bold transition disabled:opacity-50 inline-flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              {submitting ? "Sharing…" : "Share post"}
            </button>

            <p className="text-[11px] text-muted text-center">
              {user?.role?.toLowerCase() === "admin" ||
              user?.role?.toLowerCase() === "tech_writer"
                ? "Your posts are published immediately."
                : "Posts by learners are reviewed by an admin before going live."}
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
