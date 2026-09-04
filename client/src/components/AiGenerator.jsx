import { useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import AiAvatar from "./AiAvatar";
import { API_BASE_URL } from "../services/api";

export default function AiGenerator() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [copiedIdx, setCopiedIdx] = useState(null);

  // Persistent Chat State using localStorage
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem("moringa_ai_chat");
      return saved
        ? JSON.parse(saved)
        : [{ sender: "ai", text: "Hi! I'm your AI assistant. How can I help you today?" }];
    } catch {
      return [{ sender: "ai", text: "Hi! I'm your AI assistant. How can I help you today?" }];
    }
  });

  const [loading, setLoading] = useState(false);
  const chatBottomRef = useRef(null);

  // Sync chat to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem("moringa_ai_chat", JSON.stringify(messages));
    } catch (err) {
      console.error("Failed to save chat to local storage:", err);
    }
  }, [messages]);

  // Quick suggestion chips customized by route
  const suggestionChips = location.pathname.includes("/create")
    ? ["✨ Suggest catchy titles", "📝 Improve post outline", "🔍 Check tone & grammar"]
    : ["💡 Give me post ideas", "❓ How does MoringaHub work?", "✍️ Help me write an article"];

  // Position state
  const [position, setPosition] = useState({
    x: Math.max(20, window.innerWidth - 380),
    y: Math.max(20, window.innerHeight - 520)
  });

  const isDragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });

  // Mouse & Touch Dragging Listeners
  useEffect(() => {
    const handleMove = (e) => {
      if (!isDragging.current) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;

      setPosition({
        x: Math.max(0, Math.min(window.innerWidth - 360, clientX - offset.current.x)),
        y: Math.max(0, Math.min(window.innerHeight - 500, clientY - offset.current.y))
      });
    };

    const handleEnd = () => {
      isDragging.current = false;
    };

    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleEnd);
    window.addEventListener("touchmove", handleMove);
    window.addEventListener("touchend", handleEnd);

    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleEnd);
      window.removeEventListener("touchmove", handleMove);
      window.removeEventListener("touchend", handleEnd);
    };
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (isOpen) {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, loading]);

  const handleStart = (e) => {
    isDragging.current = true;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    offset.current = {
      x: clientX - position.x,
      y: clientY - position.y
    };
  };

  const handleClearChat = () => {
    const initialMsg = [{ sender: "ai", text: "Hi! I'm your AI assistant. How can I help you today?" }];
    setMessages(initialMsg);
    localStorage.removeItem("moringa_ai_chat");
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleInsertIntoPost = (text) => {
    window.dispatchEvent(new CustomEvent("ai-insert-content", { detail: text }));
  };

  const handleSend = async (customPrompt) => {
    const messageToSend = typeof customPrompt === "string" ? customPrompt : prompt;
    if (!messageToSend.trim() || loading) return;

    const updatedMessages = [...messages, { sender: "user", text: messageToSend }];
    
    setMessages(updatedMessages);
    setPrompt("");
    setLoading(true);

    try {
      const recentHistory = updatedMessages.slice(-6);

      const response = await fetch(`${API_BASE_URL}/api/ai/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: messageToSend,
          history: recentHistory,
          route: location.pathname
        }),
      });
      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: data.result || data.error || "No response received." }
      ]);
    } catch (err) {
      console.error("AI Error:", err);
      setMessages((prev) => [...prev, { sender: "ai", text: "Error connecting to AI service." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            position: "fixed",
            bottom: "20px",
            right: "20px",
            background: "none",
            border: "none",
            cursor: "pointer",
            zIndex: 9999,
          }}
        >
          <AiAvatar size={56} />
        </button>
      )}

      {/* Movable Chat Window */}
      {isOpen && (
        <div
          style={{
            position: "fixed",
            left: `${position.x}px`,
            top: `${position.y}px`,
            width: "360px",
            height: "500px",
            backgroundColor: "#ffffff",
            borderRadius: "12px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
            display: "flex",
            flexDirection: "column",
            zIndex: 9999,
            overflow: "hidden",
            border: "1px solid #e2e8f0"
          }}
        >
          {/* Header */}
          <div
            onMouseDown={handleStart}
            onTouchStart={handleStart}
            style={{
              padding: "10px 14px",
              backgroundColor: "#ea580c",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "grab",
              userSelect: "none",
              touchAction: "none"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AiAvatar size={26} />
              <strong style={{ fontSize: "14px" }}>Moringa AI Assistant</strong>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button
                onClick={handleClearChat}
                title="Clear Chat History"
                style={{ background: "none", border: "none", color: "#fdba74", fontSize: "12px", cursor: "pointer" }}
              >
                Clear
              </button>
              <button
                onClick={() => setIsOpen(false)}
                style={{ background: "none", border: "none", color: "white", fontSize: "18px", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages Container */}
          <div style={{ flex: 1, padding: "12px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "10px" }}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                  backgroundColor: msg.sender === "user" ? "#ea580c" : "#f1f5f9",
                  color: msg.sender === "user" ? "#ffffff" : "#0f172a",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  maxWidth: "85%",
                  fontSize: "14px"
                }}
              >
                {msg.sender === "ai" ? (
                  <div>
                    <div className="prose prose-sm max-w-none text-slate-900 leading-relaxed">
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    </div>
                    
                    <div style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "6px" }}>
                      {idx > 0 && (
                        <button
                          onClick={() => handleCopy(msg.text, idx)}
                          style={{
                            fontSize: "11px",
                            color: "#64748b",
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            padding: "0"
                          }}
                        >
                          {copiedIdx === idx ? "✓ Copied" : "📋 Copy text"}
                        </button>
                      )}

                      {location.pathname.includes("/create") && (
                        <button
                          onClick={() => handleInsertIntoPost(msg.text)}
                          style={{
                            fontSize: "11px",
                            color: "#ea580c",
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            padding: "0",
                            fontWeight: "600"
                          }}
                        >
                          📥 Insert into Draft
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  msg.text
                )}
              </div>
            ))}

            {loading && (
              <div style={{ alignSelf: "flex-start", backgroundColor: "#f1f5f9", padding: "8px 12px", borderRadius: "8px", fontSize: "13px", color: "#64748b" }}>
                AI is thinking...
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Suggestion Chips */}
          <div style={{ display: "flex", gap: "6px", overflowX: "auto", padding: "6px 10px", borderTop: "1px solid #f1f5f9" }}>
            {suggestionChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip)}
                style={{
                  fontSize: "11px",
                  whiteSpace: "nowrap",
                  padding: "4px 8px",
                  backgroundColor: "#f8fafc",
                  border: "1px solid #cbd5e1",
                  borderRadius: "12px",
                  color: "#334155",
                  cursor: "pointer"
                }}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <div style={{ padding: "10px", borderTop: "1px solid #e2e8f0", display: "flex", gap: "8px" }}>
            <input
              type="text"
              placeholder="Ask AI anything..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              style={{ flex: 1, padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", outline: "none" }}
            />
            <button
              onClick={() => handleSend()}
              disabled={loading}
              style={{
                backgroundColor: "#ea580c",
                color: "white",
                border: "none",
                padding: "8px 14px",
                borderRadius: "6px",
                cursor: "pointer",
                opacity: loading ? 0.6 : 1
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
}