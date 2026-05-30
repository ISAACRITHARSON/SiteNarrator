import { useCallback, useState, useRef, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import Layout from "../components/Layout";

type Message = {
  id: number;
  from: "agent" | "user" | "system";
  text: string;
  photos?: string[];
  actions?: { label: string; onClick: () => void }[];
};

export default function Submit() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [photos, setPhotos] = useState<File[]>([]);
  const [documents, setDocuments] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [step, setStep] = useState<"greeting" | "photos" | "analyzing" | "context" | "generating" | "done">("greeting");
  const [_superintendent] = useState(() => localStorage.getItem("superintendent") || "");
  const [_projectId] = useState(() => localStorage.getItem("project_id") || "");
  const [_projectName] = useState(() => localStorage.getItem("project_name") || "");
  const [showSetup, setShowSetup] = useState(!localStorage.getItem("superintendent"));
  const [setupName, setSetupName] = useState("");
  const [setupProject, setSetupProject] = useState("");
  const [setupProjectName, setSetupProjectName] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const msgId = useRef(0);

  const scrollToBottom = () => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  };

  const addMessage = (from: Message["from"], text: string, extras?: Partial<Message>) => {
    msgId.current += 1;
    const msg: Message = { id: msgId.current, from, text, ...extras };
    setMessages((prev) => [...prev, msg]);
    scrollToBottom();
    return msg;
  };

  // Start the conversation once setup is done
  const hasGreeted = useRef(false);
  useEffect(() => {
    if (!showSetup && step === "greeting" && !hasGreeted.current) {
      hasGreeted.current = true;
      const name = localStorage.getItem("superintendent") || "";
      const project = localStorage.getItem("project_name") || localStorage.getItem("project_id") || "your project";
      const greeting = name
        ? `Hey ${name.split(" ")[0]} 👋\n\nEnd of day on **${project}**.\nDrop your site photos and I'll build today's report.`
        : `Hey there 👋\n\nEnd of day on **${project}**.\nDrop your site photos and I'll build today's report.`;
      setTimeout(() => {
        addMessage("agent", greeting);
        setStep("photos");
      }, 500);
    }
  }, [showSetup]);

  // Photo drop handler
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const imageFiles = acceptedFiles.filter((f) => f.type.startsWith("image/"));
    const docFiles = acceptedFiles.filter((f) => !f.type.startsWith("image/"));

    if (imageFiles.length > 0) {
      setPhotos((prev) => [...prev, ...imageFiles]);
      const newPreviews = imageFiles.map((f) => URL.createObjectURL(f));
      setPreviews((prev) => [...prev, ...newPreviews]);
    }
    if (docFiles.length > 0) {
      setDocuments((prev) => [...prev, ...docFiles]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    multiple: true,
    maxFiles: 20,
  });

  // When files are added, agent acknowledges and asks for context
  useEffect(() => {
    if ((photos.length > 0 || documents.length > 0) && step === "photos") {
      setStep("analyzing");
      const parts = [];
      if (photos.length > 0) parts.push(`📷 ${photos.length} photo${photos.length > 1 ? "s" : ""}`);
      if (documents.length > 0) parts.push(`📄 ${documents.length} document${documents.length > 1 ? "s" : ""} (${documents.map(d => d.name).join(", ")})`);
      addMessage("user", parts.join(" + ") + " uploaded", { photos: previews });

      setTimeout(() => {
        addMessage("agent", `Got your files. Analyzing...\n\nI'll extract data from the images and documents. While I do that —\n\n**Anything the files don't show?**\nCrew counts, delays, deliveries, inspections — tell me in your own words or skip.`);
        setStep("context");
      }, 1500);
    }
  }, [photos.length, documents.length]);

  // User sends context or skips
  const handleSend = () => {
    if (step !== "context") return;
    const text = input.trim();
    if (text) {
      addMessage("user", text);
    } else {
      addMessage("user", "No additional notes — just the photos.");
    }
    setInput("");
    triggerGeneration(text);
  };

  const handleSkip = () => {
    addMessage("user", "Nothing else — generate the report.");
    triggerGeneration("");
  };

  const triggerGeneration = async (notes: string) => {
    setStep("generating");
    addMessage("agent", "On it. Pulling weather data, extracting observations, writing your narrative...");

    const formData = new FormData();
    formData.append("project_id", localStorage.getItem("project_id") || "PROJ-001");
    formData.append("report_date", new Date().toISOString().split("T")[0]);
    formData.append("superintendent_name", localStorage.getItem("superintendent") || "Superintendent");
    formData.append("lat", "47.6062");
    formData.append("lon", "-122.3321");
    formData.append("trade_tags", "concrete,electrical,plumbing");
    formData.append("text_notes", notes);
    formData.append("zones", "");
    photos.forEach((p) => formData.append("photos", p));
    documents.forEach((d) => formData.append("documents", d));

    try {
      const resp = await fetch("http://localhost:8000/api/v1/submissions", { method: "POST", body: formData });
      if (!resp.ok) throw new Error("Pipeline failed");
      const data = await resp.json();
      localStorage.setItem("draft_id", data.draft_id);

      setStep("done");
      addMessage("agent", `✅ **Report ready.**\n\nConfidence: ${data.quality_passed ? "High" : "Needs review"} • ${data.narrative_length} characters • Trace: ${data.trace_id?.slice(0, 8)}...\n\nSending to your PC for review now.`, {
        actions: [
          { label: "Preview Report", onClick: () => { window.location.href = "/review"; } },
          { label: "Go to Dashboard", onClick: () => { window.location.href = "/dashboard"; } },
        ],
      });
    } catch (err) {
      addMessage("agent", "Something went wrong generating the report. Want to try again?");
      setStep("context");
    }
  };

  // ─── Setup Screen ───────────────────────────────────
  if (showSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "var(--background)" }}>
        <div className="max-w-md w-full mx-auto px-6">
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold mb-2" style={{ color: "var(--primary)" }}>SiteNarrator</h1>
            <p style={{ color: "var(--foreground-muted)" }}>They build it. We write it.</p>
          </div>
          <div className="rounded-2xl shadow-lg p-8 space-y-5" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <h2 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>Let's get you set up.</h2>
            <p className="text-sm" style={{ color: "var(--foreground-muted)" }}>One time only — then it's photos and go.</p>
            <div>
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Your Name</label>
              <input type="text" value={setupName} onChange={(e) => setSetupName(e.target.value)} placeholder="John Martinez" className="mt-1.5 w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2" style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }} />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Project ID</label>
              <input type="text" value={setupProject} onChange={(e) => setSetupProject(e.target.value)} placeholder="PROJ-2024-001" className="mt-1.5 w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2" style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }} />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Project Name</label>
              <input type="text" value={setupProjectName} onChange={(e) => setSetupProjectName(e.target.value)} placeholder="Sunrise Apartments — Tower A" className="mt-1.5 w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2" style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }} />
            </div>
            <button onClick={() => { if (!setupName.trim() || !setupProject.trim()) return; localStorage.setItem("superintendent", setupName); localStorage.setItem("project_id", setupProject); localStorage.setItem("project_name", setupProjectName || setupProject); setShowSetup(false); }} disabled={!setupName.trim() || !setupProject.trim()} className="w-full py-4 rounded-full text-lg font-bold transition-all disabled:opacity-40 shadow-sm" style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}>
              Let's go →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Conversational Agent Interface ─────────────────
  return (
    <Layout activePage="submit">
      <div className="h-screen flex flex-col">

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 max-w-2xl mx-auto w-full">
        {/* Static hero banner — always visible */}
        <div className="rounded-2xl overflow-hidden mb-6" style={{ border: "1px solid var(--border)" }}>
          <div className="relative h-40 overflow-hidden">
            <img
              src="/hero.jpg"
              alt="Construction workers reviewing blueprints on site"
              className="w-full h-full object-cover opacity-60"
              style={{ objectPosition: "center 30%" }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#1a1a2e] to-transparent"></div>
            <div className="absolute bottom-4 left-5 right-5">
              <h2 className="text-lg font-bold text-white">Today's Site Report</h2>
              <p className="text-xs text-white/70 mt-0.5">Drop photos below — AI handles the rest.</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"} animate-slide-up`}>
              <div className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-sm ${msg.from === "agent" ? "rounded-tl-sm" : msg.from === "user" ? "rounded-tr-sm" : ""}`}
                style={
                  msg.from === "agent" ? { backgroundColor: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)" }
                  : msg.from === "user" ? { backgroundColor: "var(--primary)", color: "#1a1a1a" }
                  : { backgroundColor: "var(--surface)", color: "var(--foreground-muted)" }
                }
              >
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.text.split("**").map((part, i) => i % 2 === 1 ? <strong key={i} className="font-semibold">{part}</strong> : <span key={i}>{part}</span>)}
                </div>
                {msg.photos && msg.photos.length > 0 && (
                  <div className="grid grid-cols-4 gap-1.5 mt-3">
                    {msg.photos.map((src, i) => (
                      <img key={i} src={src} alt="" className="w-full aspect-square object-cover rounded-lg" />
                    ))}
                  </div>
                )}
                {msg.actions && (
                  <div className="flex gap-2 mt-4">
                    {msg.actions.map((action, i) => (
                      <button key={i} onClick={action.onClick} className="px-5 py-2.5 rounded-full text-sm font-semibold shadow-sm hover:shadow-md transition-all" style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}>
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 sticky bottom-0" style={{ borderTop: "1px solid var(--border)", backgroundColor: "var(--surface)" }}>
        <div className="max-w-2xl mx-auto">
          {step === "photos" && (
            <div {...getRootProps()} className="border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all" style={{ borderColor: isDragActive ? "var(--primary)" : "var(--border)", backgroundColor: isDragActive ? "var(--primary-subtle)" : "transparent" }}>
              <input {...getInputProps()} />
              <p className="text-lg font-bold" style={{ color: "var(--foreground)" }}>{isDragActive ? "Drop here" : "Drop site photos & documents here"}</p>
              <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>or click to browse • JPG/PNG, PDF, Excel</p>
            </div>
          )}

          {step === "context" && (
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="8 guys from Pacific Steel, rain delay 2-3:30..."
                className="flex-1 rounded-full px-5 py-3 text-sm focus:outline-none focus:ring-2"
                style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }}
              />
              <button onClick={handleSend} className="px-5 py-3 rounded-full text-sm font-semibold transition-all" style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}>
                Send
              </button>
              <button onClick={handleSkip} className="px-5 py-3 rounded-full text-sm font-semibold transition-all" style={{ border: "1px solid var(--border)", color: "var(--foreground-muted)" }}>
                Skip
              </button>
            </div>
          )}

          {step === "generating" && (
            <div className="text-center py-3 animate-gentle-pulse">
              <div className="flex items-center justify-center gap-2">
                <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: "var(--primary)", animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: "var(--primary)", animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: "var(--primary)", animationDelay: "300ms" }}></div>
              </div>
              <p className="text-xs mt-2 font-medium" style={{ color: "var(--foreground-muted)" }}>Agents working...</p>
            </div>
          )}

          {step === "done" && (
            <p className="text-center text-sm font-medium" style={{ color: "var(--foreground-muted)" }}>Report generated. See above for next steps.</p>
          )}
        </div>
      </div>
      </div>
    </Layout>
  );
}
