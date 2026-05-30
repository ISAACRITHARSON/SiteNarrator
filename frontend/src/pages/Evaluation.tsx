import { useState } from "react";
import Layout from "../components/Layout";

interface TraceStep {
  action: string;
  input: string;
  output: string;
  duration: string;
  status: string;
}

function TracePhase({ agent, duration, status, steps }: { agent: string; duration: string; status: string; steps: TraceStep[] }) {
  const [open, setOpen] = useState(false);

  const statusColor = status === "success" ? "var(--success)" : status === "pending" ? "var(--foreground-muted)" : "var(--primary)";
  const statusBg = status === "success" ? "var(--success-subtle)" : status === "pending" ? "var(--surface)" : "var(--primary-subtle)";

  return (
    <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left transition-all"
        style={{ backgroundColor: open ? "var(--surface)" : "transparent" }}
      >
        <span className="text-xs" style={{ color: "var(--foreground-muted)" }}>{open ? "▼" : "▶"}</span>
        <span className="text-sm font-semibold flex-1" style={{ color: "var(--foreground)" }}>{agent}</span>
        <span className="text-xs font-mono" style={{ color: "var(--foreground-muted)" }}>{duration}</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: statusBg, color: statusColor }}>
          {status === "success" ? "✓ Done" : status === "pending" ? "Pending" : status}
        </span>
      </button>
      {open && (
        <div className="px-4 pb-3">
          <div className="space-y-1 ml-5">
            {steps.map((step, i) => (
              <div key={i} className="flex items-center gap-3 py-1.5 text-xs">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: step.status === "success" ? "var(--success)" : step.status === "skipped" ? "var(--foreground-muted)" : step.status === "enforced" ? "var(--primary)" : "var(--foreground-muted)" }}></div>
                <span className="w-40 font-medium" style={{ color: "var(--foreground)" }}>{step.action}</span>
                <span className="w-36 truncate" style={{ color: "var(--foreground-muted)" }}>{step.input}</span>
                <span className="flex-1 truncate" style={{ color: "var(--foreground-muted)" }}>{step.output}</span>
                <span className="font-mono w-14 text-right" style={{ color: "var(--foreground-muted)" }}>{step.duration}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const AVAILABLE_MODELS = [
  { id: "claude-sonnet", name: "Claude Sonnet 4.5", provider: "AWS Bedrock" },
  { id: "claude-opus", name: "Claude Opus 4", provider: "AWS Bedrock" },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "gemini-pro", name: "Gemini 2.5 Pro", provider: "Google" },
  { id: "llama-4", name: "Llama 4 Scout", provider: "AWS Bedrock" },
];

const MODEL_METRICS: Record<string, { overall: number; hallucination: number; citation: number; relevancy: number; tone: number; latency: number; cost: number; promptTokens: number; completionTokens: number }> = {
  "claude-sonnet": { overall: 88, hallucination: 2.0, citation: 95, relevancy: 88, tone: 92, latency: 4.2, cost: 0.045, promptTokens: 8200, completionTokens: 3100 },
  "claude-opus": { overall: 92, hallucination: 1.2, citation: 97, relevancy: 93, tone: 95, latency: 8.1, cost: 0.12, promptTokens: 8200, completionTokens: 4200 },
  "gpt-4o": { overall: 85, hallucination: 3.5, citation: 91, relevancy: 84, tone: 88, latency: 3.8, cost: 0.038, promptTokens: 8400, completionTokens: 2900 },
  "gemini-pro": { overall: 83, hallucination: 4.1, citation: 89, relevancy: 82, tone: 85, latency: 3.2, cost: 0.032, promptTokens: 8100, completionTokens: 3300 },
  "llama-4": { overall: 79, hallucination: 5.8, citation: 84, relevancy: 78, tone: 80, latency: 2.9, cost: 0.018, promptTokens: 8500, completionTokens: 3600 },
};

export default function Evaluation() {
  const [selectedModel, setSelectedModel] = useState("claude-sonnet");
  const traceId = localStorage.getItem("trace_id") || "d0a4a39fb318";

  const metrics = MODEL_METRICS[selectedModel];
  const model = AVAILABLE_MODELS.find(m => m.id === selectedModel)!;

  const MetricCard = ({ value, label, color }: { value: string; label: string; color: string }) => (
    <div className="rounded-xl p-5 text-center" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="text-3xl font-bold" style={{ color }}>{value}</div>
      <p className="text-xs mt-2 uppercase tracking-wide font-medium" style={{ color: "var(--foreground-muted)" }}>{label}</p>
    </div>
  );

  const ProgressBar = ({ label, value, color }: { label: string; value: number; color: string }) => (
    <div className="flex items-center gap-4">
      <span className="text-sm w-36 font-medium" style={{ color: "var(--foreground-muted)" }}>{label}</span>
      <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ backgroundColor: "var(--surface)" }}>
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${value}%`, backgroundColor: color }}></div>
      </div>
      <span className="text-sm font-bold w-12 text-right" style={{ color: "var(--foreground)" }}>{value}%</span>
    </div>
  );

  return (
    <Layout activePage="evaluation">
      <div className="p-8 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>Evaluation & Traceability</h1>
          <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>AI model performance metrics and pipeline traceability.</p>
        </div>

        {/* Trace + Model Selector Row */}
        <div className="flex gap-4 mb-6">
          <div className="flex-1 rounded-xl p-4" style={{ backgroundColor: "var(--primary-subtle)", border: "1px solid var(--border)" }}>
            <p className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: "var(--primary)" }}>Pipeline Trace</p>
            <p className="text-sm font-mono mt-0.5" style={{ color: "var(--foreground)" }}>{traceId}</p>
          </div>
          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <p className="text-[10px] uppercase tracking-wide font-semibold mb-1.5" style={{ color: "var(--foreground-muted)" }}>Model</p>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="px-3 py-1.5 rounded-lg text-sm font-medium cursor-pointer"
              style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            >
              {AVAILABLE_MODELS.map((m) => (
                <option key={m.id} value={m.id}>{m.name} ({m.provider})</option>
              ))}
            </select>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <MetricCard value={`${metrics.overall}%`} label="Overall Score" color={metrics.overall >= 85 ? "var(--success)" : "var(--primary)"} />
          <MetricCard value={`${metrics.hallucination}%`} label="Hallucination" color={metrics.hallucination <= 3 ? "var(--success)" : "#ef5350"} />
          <MetricCard value={`${metrics.citation}%`} label="Citation Accuracy" color={metrics.citation >= 90 ? "var(--success)" : "var(--primary)"} />
          <MetricCard value={model.name} label="Model Used" color="var(--foreground)" />
        </div>

        {/* Quality Breakdown */}
        <div className="rounded-xl p-6 mb-8" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          <h3 className="text-sm font-bold mb-5" style={{ color: "var(--foreground)" }}>Quality Breakdown</h3>
          <div className="space-y-4">
            <ProgressBar label="Factual Grounding" value={100 - metrics.hallucination} color="#4caf50" />
            <ProgressBar label="Citation Accuracy" value={metrics.citation} color="#2196f3" />
            <ProgressBar label="Relevancy" value={metrics.relevancy} color="#9c27b0" />
            <ProgressBar label="Tone Consistency" value={metrics.tone} color="#ff9800" />
          </div>
        </div>

        {/* Performance + Tokens */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="rounded-xl p-6" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <h3 className="text-sm font-bold mb-4" style={{ color: "var(--foreground)" }}>Performance</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm" style={{ color: "var(--foreground-muted)" }}>Latency</span>
                <span className="text-sm font-bold" style={{ color: "var(--foreground)" }}>{metrics.latency}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm" style={{ color: "var(--foreground-muted)" }}>Cost per Report</span>
                <span className="text-sm font-bold" style={{ color: "var(--foreground)" }}>${metrics.cost}</span>
              </div>
              <div className="flex justify-between pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                <span className="text-sm" style={{ color: "var(--foreground)" }}>Provider</span>
                <span className="text-sm font-bold" style={{ color: "var(--primary)" }}>{model.provider}</span>
              </div>
            </div>
          </div>
          <div className="rounded-xl p-6" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <h3 className="text-sm font-bold mb-4" style={{ color: "var(--foreground)" }}>Token Usage</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm" style={{ color: "var(--foreground-muted)" }}>Prompt</span>
                <span className="text-sm font-bold" style={{ color: "var(--foreground)" }}>{metrics.promptTokens.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm" style={{ color: "var(--foreground-muted)" }}>Completion</span>
                <span className="text-sm font-bold" style={{ color: "var(--foreground)" }}>{metrics.completionTokens.toLocaleString()}</span>
              </div>
              <div className="flex justify-between pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                <span className="text-sm" style={{ color: "var(--foreground)" }}>Total</span>
                <span className="text-sm font-bold" style={{ color: "var(--primary)" }}>{(metrics.promptTokens + metrics.completionTokens).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Pipeline Steps */}
        <div className="rounded-xl p-6" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          <h3 className="text-sm font-bold mb-4" style={{ color: "var(--foreground)" }}>Pipeline Trace Steps</h3>
          <div className="space-y-2">
            {[
              { step: "Input Validation", duration: "120ms" },
              { step: "Voice Transcription", duration: "1.2s" },
              { step: "Box AI Extract (photos)", duration: "2.8s" },
              { step: "Weather API", duration: "340ms" },
              { step: "Ingest Agent", duration: "3.1s" },
              { step: "Synthesis Agent", duration: `${metrics.latency - 1.2}s` },
              { step: "Quality Agent", duration: "1.1s" },
              { step: "Eval Agent", duration: "890ms" },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 py-2 px-3 rounded-lg" style={{ backgroundColor: i % 2 === 0 ? "var(--surface)" : "transparent" }}>
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--success)" }}></div>
                <span className="text-sm flex-1" style={{ color: "var(--foreground)" }}>{item.step}</span>
                <span className="text-xs font-mono" style={{ color: "var(--foreground-muted)" }}>{item.duration}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Traceability — Collapsible by Phase */}
        <div className="rounded-xl p-6 mt-8" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          <h3 className="text-sm font-bold mb-2" style={{ color: "var(--foreground)" }}>Agent Traceability — End-to-End Workflow</h3>
          <p className="text-xs mb-5" style={{ color: "var(--foreground-muted)" }}>Click each phase to expand details.</p>

          <div className="space-y-2">
            <TracePhase
              agent="Submission & Upload"
              duration="1.2s"
              status="success"
              steps={[
                { action: "Receive files", input: "2 photos, 0 docs", output: "Saved to temp", duration: "50ms", status: "success" },
                { action: "Upload to Box", input: "Photos + documents", output: "/PROJ-001/2026-05-30/sources/", duration: "1.1s", status: "success" },
              ]}
            />
            <TracePhase
              agent="Ingest Agent"
              duration="3.1s"
              status="success"
              steps={[
                { action: "Box AI Extract", input: "2 photos", output: "work_type, progress, safety, materials", duration: "2.8s", status: "success" },
                { action: "Weather API", input: "GPS: 47.6, -122.3", output: "72°F, Partly cloudy", duration: "340ms", status: "success" },
                { action: "Voice Transcription", input: "—", output: "—", duration: "—", status: "skipped" },
                { action: "Structured Extraction", input: "Notes + transcript", output: "Labor, equipment, delays", duration: "120ms", status: "success" },
                { action: "Build ObservationBundle", input: "All extracted data", output: "JSON bundle", duration: "10ms", status: "success" },
              ]}
            />
            <TracePhase
              agent="Synthesis Agent"
              duration={`${metrics.latency - 1.2}s`}
              status="success"
              steps={[
                { action: "Query AgentCore Memory", input: "Project ID", output: "Tone prefs, style history", duration: "200ms", status: "success" },
                { action: "Generate 10-section narrative", input: "ObservationBundle", output: `1,718 chars, [Photo 1] [Photo 2]`, duration: `${(metrics.latency - 1.6).toFixed(1)}s`, status: "success" },
                { action: "Save draft to Box", input: "Markdown narrative", output: "/drafts/draft_v1.md", duration: "400ms", status: "success" },
              ]}
            />
            <TracePhase
              agent="Quality Agent"
              duration="1.1s"
              status="success"
              steps={[
                { action: "Validate schema", input: "Draft narrative", output: "10/10 sections present", duration: "300ms", status: "success" },
                { action: "Check citations", input: "Narrative + photo IDs", output: `${metrics.citation}% accuracy`, duration: "250ms", status: "success" },
                { action: "Check trade coverage", input: "Trades in bundle vs narrative", output: "All trades covered", duration: "150ms", status: "success" },
                { action: "Compute confidence", input: "Density + completeness + specificity", output: `${metrics.overall}%`, duration: "100ms", status: "success" },
                { action: "Save quality report", input: "QualityReport JSON", output: "quality-report.json → Box", duration: "300ms", status: "success" },
              ]}
            />
            <TracePhase
              agent="Eval Agent"
              duration="890ms"
              status="success"
              steps={[
                { action: "Hallucination detection", input: "Narrative vs ObservationBundle", output: `${metrics.hallucination}% hallucinated`, duration: "350ms", status: "success" },
                { action: "Citation verification", input: "[Photo N] → file IDs", output: `${metrics.citation}% correct`, duration: "200ms", status: "success" },
                { action: "Tone consistency", input: "Narrative vs memory style", output: `${metrics.tone}% consistent`, duration: "150ms", status: "success" },
                { action: "Log to CloudWatch", input: "Metrics + tokens + cost", output: `$${metrics.cost}, ${(metrics.promptTokens + metrics.completionTokens).toLocaleString()} tokens`, duration: "190ms", status: "success" },
              ]}
            />
            <TracePhase
              agent="Policy & Delivery"
              duration="—"
              status="pending"
              steps={[
                { action: "Cedar Policy check", input: "Delivery request", output: "Blocked until PC approval", duration: "—", status: "enforced" },
                { action: "PC Review", input: "Draft + quality report", output: "Awaiting approval", duration: "—", status: "pending" },
                { action: "PDF Generation", input: "Approved narrative", output: "report.pdf → Box /approved/", duration: "—", status: "pending" },
                { action: "Client Q&A Chat", input: "Report content", output: "Answers + escalation", duration: "—", status: "pending" },
              ]}
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}
