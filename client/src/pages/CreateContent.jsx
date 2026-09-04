import { useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { Sparkles, Wand2 } from "lucide-react";
import { createContent } from "../services/contentApi";
import { selectCurrentUser } from "../features/auth/authSlice";
import Button from "../components/ui/Button";
import { API_BASE_URL } from "../services/api";

const TYPES = [
  { value: "article", label: "Article" },
  { value: "video", label: "Video" },
  { value: "audio", label: "Audio" },
];

export default function CreateContent() {
  const user = useSelector(selectCurrentUser);
  const categories = useSelector((state) => state.categories.items);
  const navigate = useNavigate();

  const [form, setForm] = useState({ title: "", body: "", type: "article", mediaUrl: "", categoryId: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [aiLoading, setAiLoading] = useState(null); // 'category' | 'enhance' | null

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  // Helper to safely format API errors into user-friendly strings
  function parseAiError(data, status) {
    let raw = data?.error || data?.message || "AI service error";
    if (typeof raw === "object") raw = JSON.stringify(raw);

    if (status === 503 || raw.includes("RESOURCE_EXHAUSTED") || raw.includes("Quota exceeded")) {
      return "Gemini API rate limit reached. Please wait ~1 minute and try again.";
    }
    return raw;
  }

  // AI Helper: Detect best category matching title & body
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
    const categoryList = categories.map((c) => c.name).join(", ");
    const prompt = `Based on title "${form.title}" and text "${form.body}", select the single best category from: [${categoryList}]. Return ONLY the category name.`;

    try {
      const res = await fetch(`${API_BASE_URL}/api/ai/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          prompt, 
          history: [], 
          route: window.location.pathname 
        }),
      });
      const data = await res.json();
      
      if (!res.ok) {
        setError(parseAiError(data, res.status));
        return;
      }

      if (data.result) {
        const suggestedName = data.result.trim().toLowerCase();
        const matched = categories.find(
          (c) => c.name.toLowerCase() === suggestedName || suggestedName.includes(c.name.toLowerCase())
        );
        if (matched) {
          update("categoryId", matched.id);
        } else {
          setError(`AI suggested "${data.result.trim()}", which did not match an exact category.`);
        }
      }
    } catch (err) {
      console.error("AI Category suggestion error:", err);
      setError("Failed to connect to the AI service server.");
    } finally {
      setAiLoading(null);
    }
  }

  // AI Helper: Refine draft text strictly without options or headers
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
      const res = await fetch(`${API_BASE_URL}/api/ai/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          prompt, 
          history: [], 
          route: window.location.pathname 
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(parseAiError(data, res.status));
        return;
      }

      if (data.result) {
        const cleanedText = data.result.replace(/^###?\s*Option\s*\d+:?/gi, "").trim();
        update("body", cleanedText);
      }
    } catch (err) {
      console.error("AI Enhance error:", err);
      setError("Failed to connect to the AI service server.");
    } finally {
      setAiLoading(null);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    // Guard: without a logged-in user there is no authorId — this used to
    // crash with "Cannot read properties of null (reading 'id')".
    if (!user?.id) {
      navigate("/login?next=/create", { replace: true });
      return;
    }
    if (!form.title.trim() || !form.body.trim() || !form.categoryId) {
      setError("Title, content, and a category are all required.");
      return;
    }
    if (form.type !== "article" && !form.mediaUrl.trim()) {
      setError(`Add a ${form.type} URL before publishing.`);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const created = await createContent({ ...form, authorId: user.id });
      // Backend returns { content_id, status, ... } — fall back across shapes
      const newId = created?.content_id ?? created?.id;
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

  return (
    <div className="max-w-2xl">
      <p className="text-xs font-mono text-brand-500 mb-1">// new post</p>
      <h1 className="text-2xl font-bold text-navy mb-1">Share something with the community</h1>
      <p className="text-sm text-muted mb-6">
        Posts go to a review queue before appearing in the public feed — an admin or tech writer approves it first.
      </p>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs font-bold text-red-400 hover:text-red-300 ml-2">✕</button>
        </div>
      )}

      {/* AI Assistant Quick Toolbar */}
      <div className="mb-4 p-3 bg-brand-500/5 border border-brand-500/20 rounded-xl flex items-center justify-between flex-wrap gap-2">
        <span className="text-xs font-medium text-brand-600 flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-brand-500" /> AI Writing Tools
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSuggestCategory}
            disabled={!!aiLoading}
            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white border border-brand-500/30 text-brand-600 hover:bg-brand-500/10 transition disabled:opacity-50"
          >
            {aiLoading === "category" ? "Detecting..." : "✨ Auto-Detect Category"}
          </button>
          <button
            type="button"
            onClick={handleEnhanceDraft}
            disabled={!!aiLoading}
            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-brand-500 text-white hover:bg-brand-600 transition disabled:opacity-50 flex items-center gap-1"
          >
            <Wand2 className="w-3 h-3" />
            {aiLoading === "enhance" ? "Polishing..." : "Enhance Draft"}
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 bg-white border border-line rounded-xl p-6">
        <div className="flex gap-2">
          {TYPES.map((t) => (
            <button
              type="button"
              key={t.value}
              onClick={() => update("type", t.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                form.type === t.value
                  ? "bg-brand-500 text-navy border-brand-500"
                  : "border-line text-muted hover:border-navy/30"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div>
          <label className="block text-xs font-medium text-navy/70 mb-1">Title</label>
          <input
            value={form.title}
            onChange={(e) => update("title", e.target.value)}
            placeholder="A clear, specific title"
            className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-navy/70 mb-1">Category</label>
          <select
            value={form.categoryId}
            onChange={(e) => update("categoryId", e.target.value)}
            disabled={categories.length === 0}
            className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500 disabled:bg-surface disabled:text-muted"
          >
            <option value="">
              {categories.length === 0 ? "No categories available yet" : "Select a category…"}
            </option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          {categories.length === 0 && (
            <p className="text-xs text-muted mt-1">
              No categories exist yet — ask an admin to create one before you can publish.
            </p>
          )}
        </div>

        {form.type !== "article" && (
          <div>
            <label className="block text-xs font-medium text-navy/70 mb-1">
              {form.type === "video" ? "Video URL" : "Audio URL"}
            </label>
            <input
              value={form.mediaUrl}
              onChange={(e) => update("mediaUrl", e.target.value)}
              placeholder="https://…"
              className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
            />
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-navy/70 mb-1">
            {form.type === "article" ? "Body" : "Description"}
          </label>
          <textarea
            value={form.body}
            onChange={(e) => update("body", e.target.value)}
            rows={form.type === "article" ? 10 : 4}
            placeholder={form.type === "article" ? "Write your article…" : "What's this piece about?"}
            className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
          />
        </div>

        <Button type="submit" size="lg" disabled={submitting}>
          {submitting ? "Submitting…" : "Submit for review"}
        </Button>
      </form>
    </div>
  );
}