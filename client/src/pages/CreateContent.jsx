import { useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { Sparkles, Wand2, Upload, Link as LinkIcon, ChevronDown } from "lucide-react";
import { createContent, createPost } from "../services/contentApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import Button from "../components/ui/Button";
import apiRequest from "../services/api";

const TYPES = [
  { value: "article", label: "Article" },
  { value: "image", label: "Image" },
  { value: "video", label: "Video" },
  { value: "audio", label: "Audio" },
];

const MAX_FILE_SIZE_MB = 50;

export default function CreateContent() {
  const user = useSelector(selectCurrentUser);
  const categoriesRaw = useSelector((state) => state.categories?.items || state.categories);
  const categories = Array.isArray(categoriesRaw) ? categoriesRaw : [];

  const navigate = useNavigate();

  const [form, setForm] = useState({
    title: "",
    body: "",
    type: "article",
    mediaUrl: "",
    categoryId: "",
  });

  const [file, setFile] = useState(null);
  const [uploadMode, setUploadMode] = useState("url"); // 'url' | 'file'
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [aiLoading, setAiLoading] = useState(null);
  const [categoryOpen, setCategoryOpen] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value ?? "" }));
  }

  function handleFileChange(e) {
    const selectedFile = e.target.files?.[0];
    setError(null);

    if (!selectedFile) {
      setFile(null);
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      const sizeInMB = (selectedFile.size / (1024 * 1024)).toFixed(1);
      setError(`File is too large (${sizeInMB}MB). Maximum allowed upload size is ${MAX_FILE_SIZE_MB}MB.`);
      e.target.value = "";
      setFile(null);
      return;
    }

    setFile(selectedFile);
  }

  function parseAiError(err) {
    const status = err?.status;
    let raw = err?.message || err?.error || "AI service error";
    if (typeof raw === "object") raw = JSON.stringify(raw);

    if (status === 503 || raw.includes("RESOURCE_EXHAUSTED") || raw.includes("Quota exceeded")) {
      return "Gemini API rate limit reached. Please wait ~1 minute and try again.";
    }
    return raw;
  }

  async function handleSuggestCategory() {
    if (!form.title.trim() && !form.body.trim()) {
      setError("Please write a title or draft text first so the AI can analyze it.");
      return;
    }
    if (categories.length === 0) {
      setError("No categories exist in the system to match against.");
      return;
    }

    setAiLoading("category");
    setError(null);

    const categoryNames = categories.map((c) => c.name || c.Name || "").filter(Boolean);
    const categoryList = categoryNames.join(", ");
    const prompt = `Based on title "${form.title}" and text "${form.body}", select the single best category from: [${categoryList}]. Return ONLY the category name.`;

    try {
      const data = await apiRequest("/api/ai/generate", {
        method: "POST",
        body: {
          prompt,
          history: [],
          route: window.location.pathname,
        },
      });

      if (data?.result) {
        const suggestedName = data.result.trim().toLowerCase();
        const matched = categories.find((c) => {
          const name = (c.name || c.Name || "").toLowerCase();
          return name === suggestedName || suggestedName.includes(name);
        });

        if (matched) {
          update("categoryId", matched.id || matched.CategoryID);
        } else {
          setError(`AI suggested "${data.result.trim()}", which did not match an exact category.`);
        }
      }
    } catch (err) {
      console.error("AI Category suggestion error:", err);
      setError(parseAiError(err));
    } finally {
      setAiLoading(null);
    }
  }

  async function handleEnhanceDraft() {
    if (!form.body.trim()) {
      setError("Please write a rough draft in the body box first.");
      return;
    }

    setAiLoading("enhance");
    setError(null);
    const prompt = `Rewrite and polish the following article content for clarity, tone, and grammar.
CRITICAL INSTRUCTION: Return ONLY the final polished text directly. Do NOT include options (like "Option 1"), headings, intro/outro commentary, or bullet lists.

Content:
${form.body}`;

    try {
      const data = await apiRequest("/api/ai/generate", {
        method: "POST",
        body: {
          prompt,
          history: [],
          route: window.location.pathname,
        },
      });

      if (data?.result) {
        const cleanedText = data.result.replace(/^###?\s*Option\s*\d+:?/gi, "").trim();
        update("body", cleanedText);
      }
    } catch (err) {
      console.error("AI Enhance error:", err);
      setError(parseAiError(err));
    } finally {
      setAiLoading(null);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();

    const activeUserId = user?.id || user?.UserID;

    if (!activeUserId) {
      navigate("/login?next=/create", { replace: true });
      return;
    }
    if (!form.title.trim() || !form.body.trim() || !form.categoryId) {
      setError("Title, content, and a category are all required.");
      return;
    }

    if (form.type !== "article") {
      if (uploadMode === "url" && !form.mediaUrl.trim()) {
        setError(`Add a ${form.type} URL before publishing.`);
        return;
      }
      if (uploadMode === "file" && !file) {
        setError(`Select a ${form.type} file to upload.`);
        return;
      }
    }

    setError(null);
    setSubmitting(true);

    const formattedContentType = form.type.charAt(0).toUpperCase() + form.type.slice(1);

    try {
      let created;
      if (uploadMode === "file" && file) {
        created = await createPost({
          title: form.title,
          description: form.body,
          type: formattedContentType,
          categoryId: form.categoryId,
          authorId: activeUserId,
          file,
        });
      } else {
        created = await createContent({
          title: form.title,
          body: form.body,
          type: formattedContentType,
          mediaUrl: form.mediaUrl,
          categoryId: form.categoryId,
          authorId: activeUserId,
        });
      }

      const newId = created?.content_id ?? created?.id ?? created?.data?.id ?? created?.ContentID;
      if (newId) {
        navigate(`/content/${newId}`);
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err.message || "Something went wrong while submitting. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const getAcceptType = () => {
    switch (form.type) {
      case "image":
        return "image/*";
      case "video":
        return "video/*";
      case "audio":
        return "audio/*";
      default:
        return "*/*";
    }
  };

  const selectedCategoryName = categories.find(
    (c) => String(c.id || c.CategoryID) === String(form.categoryId)
  )?.name || categories.find(
    (c) => String(c.id || c.CategoryID) === String(form.categoryId)
  )?.Name;

  return (
    <div className="max-w-2xl mx-auto p-4 text-slate-100">
      <p className="text-xs font-mono text-emerald-400 mb-1">// new post</p>
      <h1 className="text-2xl font-bold text-slate-100 mb-1">Share something with the community</h1>
      <p className="text-sm text-slate-400 mb-6">
        Posts go to a review queue before appearing in the public feed — an admin or tech writer approves it first.
      </p>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs font-bold text-red-400 hover:text-red-300 ml-2">
            ✕
          </button>
        </div>
      )}

      <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-between flex-wrap gap-2">
        <span className="text-xs font-medium text-emerald-400 flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-emerald-400" /> AI Writing Tools
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSuggestCategory}
            disabled={!!aiLoading}
            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 border border-emerald-500/30 text-emerald-400 hover:bg-slate-700 transition disabled:opacity-50 cursor-pointer"
          >
            {aiLoading === "category" ? "Detecting..." : "✨ Auto-Detect Category"}
          </button>
          <button
            type="button"
            onClick={handleEnhanceDraft}
            disabled={!!aiLoading}
            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500 text-slate-950 hover:bg-emerald-400 font-semibold transition disabled:opacity-50 flex items-center gap-1 cursor-pointer"
          >
            <Wand2 className="w-3 h-3" />
            {aiLoading === "enhance" ? "Polishing..." : "Enhance Draft"}
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-6">
        <div className="flex flex-wrap gap-2">
          {TYPES.map((t) => (
            <button
              type="button"
              key={t.value}
              onClick={() => {
                update("type", t.value);
                setFile(null);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer ${
                form.type === t.value
                  ? "bg-emerald-500 text-slate-950 border-emerald-500 font-semibold"
                  : "border-slate-800 text-slate-400 hover:border-slate-600"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Title</label>
          <input
            value={form.title || ""}
            onChange={(e) => update("title", e.target.value)}
            placeholder="A clear, specific title"
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Category</label>
          <div className="relative">
            <button
              type="button"
              onClick={() => setCategoryOpen((prev) => !prev)}
              disabled={categories.length === 0}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs sm:text-sm text-slate-100 focus:outline-none focus:border-emerald-500 disabled:bg-slate-900 disabled:text-slate-600 cursor-pointer"
            >
              <span className="truncate">
                {selectedCategoryName ||
                  (categories.length === 0 ? "No categories available yet" : "Select a category…")}
              </span>
              <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 ml-2 transition-transform duration-200 ${categoryOpen ? "rotate-180" : ""}`} />
            </button>

            {categoryOpen && categories.length > 0 && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setCategoryOpen(false)} />
                <div className="absolute left-0 right-0 top-full mt-1 z-20 max-h-56 overflow-y-auto rounded-lg bg-slate-950 border border-slate-800 shadow-2xl py-1">
                  {categories.map((c) => {
                    const id = c.id || c.CategoryID;
                    const name = c.name || c.Name;
                    const isSelected = String(form.categoryId) === String(id);
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => {
                          update("categoryId", id);
                          setCategoryOpen(false);
                        }}
                        className={`w-full text-left px-3.5 py-2.5 text-xs sm:text-sm truncate transition cursor-pointer hover:bg-slate-800 ${
                          isSelected ? "bg-emerald-500/20 text-emerald-400 font-semibold" : "text-slate-200"
                        }`}
                      >
                        {name}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>
          {categories.length === 0 && (
            <p className="text-xs text-slate-500 mt-1">
              No categories exist yet — ask an admin to create one before you can publish.
            </p>
          )}
        </div>

        {form.type !== "article" && (
          <div className="space-y-2">
            <div className="flex items-center gap-4 text-xs">
              <button
                type="button"
                onClick={() => setUploadMode("url")}
                className={`flex items-center gap-1 cursor-pointer ${uploadMode === "url" ? "text-emerald-400 font-semibold" : "text-slate-400"}`}
              >
                <LinkIcon className="w-3.5 h-3.5" /> Media URL
              </button>
              <button
                type="button"
                onClick={() => setUploadMode("file")}
                className={`flex items-center gap-1 cursor-pointer ${uploadMode === "file" ? "text-emerald-400 font-semibold" : "text-slate-400"}`}
              >
                <Upload className="w-3.5 h-3.5" /> Upload File
              </button>
            </div>

            {uploadMode === "url" ? (
              <input
                value={form.mediaUrl || ""}
                onChange={(e) => update("mediaUrl", e.target.value)}
                placeholder="https://…"
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            ) : (
              <input
                type="file"
                accept={getAcceptType()}
                onChange={handleFileChange}
                className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-emerald-500/20 file:text-emerald-400 hover:file:bg-emerald-500/30 cursor-pointer"
              />
            )}
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            {form.type === "article" ? "Body" : "Description"}
          </label>
          <textarea
            value={form.body || ""}
            onChange={(e) => update("body", e.target.value)}
            rows={form.type === "article" ? 10 : 4}
            placeholder={form.type === "article" ? "Write your article…" : "What's this piece about?"}
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <Button type="submit" size="lg" disabled={submitting} className="w-full">
          {submitting ? "Submitting…" : "Submit for review"}
        </Button>
      </form>
    </div>
  );
}