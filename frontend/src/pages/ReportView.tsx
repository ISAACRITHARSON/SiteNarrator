import { useEffect, useState } from "react";
import Layout from "../components/Layout";

interface ChatMsg {
  role: "client" | "assistant";
  content: string;
}

function generateQuestions(narrative: string): string[] {
  const questions: string[] = [];
  const lower = narrative.toLowerCase();

  // Detect sections and generate contextual questions
  if (lower.includes("weather") || lower.includes("temperature")) {
    questions.push("Did weather affect any work today?");
  }
  if (lower.includes("concrete") || lower.includes("pour")) {
    questions.push("What's the status of the concrete work?");
  }
  if (lower.includes("electrical") || lower.includes("conduit")) {
    questions.push("What electrical work was completed?");
  }
  if (lower.includes("delay") || lower.includes("rain")) {
    questions.push("What caused the delays and how long?");
  }
  if (lower.includes("inspection") || lower.includes("passed")) {
    questions.push("Were any inspections conducted today?");
  }
  if (lower.includes("safety") || lower.includes("ppe")) {
    questions.push("Any safety concerns reported?");
  }
  if (lower.includes("next day") || lower.includes("planned") || lower.includes("tomorrow")) {
    questions.push("What's planned for the next day?");
  }
  if (lower.includes("crew") || lower.includes("headcount") || lower.includes("workers")) {
    questions.push("How many workers were on site today?");
  }
  if (lower.includes("equipment") || lower.includes("crane")) {
    questions.push("What equipment was used today?");
  }
  if (lower.includes("material") || lower.includes("delivery")) {
    questions.push("Were there any material deliveries?");
  }

  // Return max 4 questions
  return questions.slice(0, 4);
}

export default function ReportView() {
  const [narrative, setNarrative] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);

  const reportId = localStorage.getItem("draft_id") || window.location.pathname.split("/").pop() || "";

  useEffect(() => {
    fetch(`http://localhost:8000/api/v1/drafts/${reportId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.narrative) {
          setNarrative(data.narrative);
          setSuggestedQuestions(generateQuestions(data.narrative));
        }
      })
      .catch(() => {});
  }, [reportId]);

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const userMsg: ChatMsg = { role: "client", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    try {
      const resp = await fetch(`http://localhost:8000/api/v1/reports/${reportId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await resp.json();
      const assistantMsg: ChatMsg = {
        role: "assistant",
        content: data.response?.content || "I can help you with questions about this report.",
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I couldn't process that. Please try again." }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <Layout activePage="report">
      <div className="p-8 max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>Daily Construction Report</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--foreground-muted)" }}>Client-facing report view</p>
        </div>

        {/* Report Content */}
        <div className="rounded-xl p-8" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          {narrative ? (
            <div>
              {narrative.split("\n").map((line, i) => {
                if (line.startsWith("## ")) return <h3 key={i} className="text-base font-bold mt-6 mb-2 pb-1" style={{ color: "var(--foreground)", borderBottom: "1px solid var(--border)" }}>{line.replace("## ", "").replace(/^\d+\.\s*/, "")}</h3>;
                if (line.startsWith("### ")) return <h4 key={i} className="text-sm font-semibold mt-4 mb-1" style={{ color: "var(--foreground)" }}>{line.replace("### ", "")}</h4>;
                if (line.startsWith("|")) return <p key={i} className="font-mono text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>{line}</p>;
                if (line.startsWith("- ")) return <p key={i} className="ml-4 text-sm" style={{ color: "var(--foreground)" }}>• {line.slice(2)}</p>;
                if (line.trim() === "") return <div key={i} className="h-3" />;
                return <p key={i} className="text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>{line}</p>;
              })}
            </div>
          ) : (
            <p className="text-center py-12" style={{ color: "var(--foreground-muted)" }}>Loading report...</p>
          )}
        </div>
      </div>

      {/* Chat Widget - Bottom Right */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 w-16 h-16 rounded-full shadow-lg flex items-center justify-center text-3xl hover:scale-110 transition-transform"
          style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}
        >
          👷🏻
        </button>
      )}

      {chatOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[500px] rounded-2xl shadow-2xl flex flex-col overflow-hidden" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          {/* Chat Header */}
          <div className="px-4 py-3 flex items-center justify-between" style={{ backgroundColor: "var(--primary)" }}>
            <div>
              <p className="text-sm font-bold" style={{ color: "#1a1a1a" }}>Ask about this report</p>
              <p className="text-xs" style={{ color: "rgba(0,0,0,0.6)" }}>Powered by SiteNarrator AI</p>
            </div>
            <button onClick={() => setChatOpen(false)} className="text-lg" style={{ color: "rgba(0,0,0,0.6)" }}>✕</button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <p className="text-3xl mb-2">👋</p>
                <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>Ask me anything about this report.</p>
                <p className="text-xs mt-1 mb-4" style={{ color: "var(--foreground-muted)" }}>Here are some things I can help with:</p>
                {/* Recommended questions — generated from report content */}
                <div className="space-y-2 text-left">
                  {suggestedQuestions.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => { setInput(q); }}
                      className="w-full text-left px-3 py-2 rounded-lg text-xs transition-all"
                      style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--foreground-muted)" }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.color = "var(--foreground)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--foreground-muted)"; }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "client" ? "justify-end" : "justify-start"}`}>
                <div className="max-w-[80%] px-4 py-2.5 rounded-2xl text-sm"
                  style={msg.role === "client"
                    ? { backgroundColor: "var(--primary)", color: "#1a1a1a", borderBottomRightRadius: "4px" }
                    : { backgroundColor: "var(--surface)", color: "var(--foreground)", borderBottomLeftRadius: "4px" }
                  }
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="px-4 py-2.5 rounded-2xl text-sm" style={{ backgroundColor: "var(--surface)", color: "var(--foreground-muted)" }}>
                  Thinking...
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Ask a question..."
                className="flex-1 px-4 py-2.5 rounded-full text-sm focus:outline-none focus:ring-2"
                style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
              <button
                onClick={sendMessage}
                disabled={sending || !input.trim()}
                className="w-10 h-10 rounded-full flex items-center justify-center disabled:opacity-50"
                style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}
              >
                ↑
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
