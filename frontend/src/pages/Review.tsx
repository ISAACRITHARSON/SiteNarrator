import { useEffect, useState } from "react";
import Layout from "../components/Layout";

interface QualityReport {
  confidence_score: number;
  flags: { section: string; issue: string; severity: string }[];
  summary: string;
  passed: boolean;
}

interface DraftData {
  draft_id: string;
  status: string;
  narrative: string;
  quality_report: QualityReport | null;
  eval_report: { overall_score: number; hallucination_score: number; citation_accuracy: number } | null;
  trace_id: string;
}

export default function Review() {
  const [draft, setDraft] = useState<DraftData | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectComment, setRejectComment] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [approved, setApproved] = useState(false);
  const [pdfUrl, setPdfUrl] = useState("");

  const draftId = localStorage.getItem("draft_id");

  const fetchDraft = () => {
    if (!draftId) { window.location.href = "/"; return; }
    fetch(`http://localhost:8000/api/v1/drafts/${draftId}`)
      .then((r) => r.json())
      .then((data) => { setDraft(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchDraft(); }, []);

  const handleApprove = async () => {
    if (!draft) return;
    setApproving(true);
    try {
      const resp = await fetch(`http://localhost:8000/api/v1/drafts/${draft.draft_id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: localStorage.getItem("superintendent") || "PC", edits_made: false }),
      });
      const data = await resp.json();
      setApproved(true);
      setPdfUrl(data.pdf_download_url);
    } catch {
      alert("Approval failed.");
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!draft || !rejectComment.trim()) return;
    setRejecting(true);
    try {
      await fetch(`http://localhost:8000/api/v1/drafts/${draft.draft_id}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rejected_by: localStorage.getItem("superintendent") || "PC", section_comments: { "General": rejectComment } }),
      });
      setShowReject(false);
      setRejectComment("");
      fetchDraft();
    } catch {
      alert("Revision request failed.");
    } finally {
      setRejecting(false);
    }
  };

  // Loading
  if (loading) {
    return (
      <Layout activePage="review">
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="text-4xl mb-4 animate-pulse">📄</div>
            <p className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>Loading draft...</p>
          </div>
        </div>
      </Layout>
    );
  }

  // No draft
  if (!draft || !draft.narrative) {
    return (
      <Layout activePage="review">
        <div className="flex items-center justify-center h-screen">
          <div className="text-center max-w-md">
            <div className="text-4xl mb-4">📭</div>
            <p className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>No draft available yet</p>
            <p className="text-sm mt-2" style={{ color: "var(--foreground-muted)" }}>The pipeline may still be processing.</p>
            <div className="flex gap-3 justify-center mt-6">
              <button onClick={fetchDraft} className="px-5 py-2.5 rounded-full text-sm font-semibold" style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}>Refresh</button>
              <a href="/" className="px-5 py-2.5 rounded-full text-sm font-semibold" style={{ border: "2px solid var(--border)", color: "var(--foreground)" }}>New Submission</a>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // Approved
  if (approved) {
    return (
      <Layout activePage="review">
        <div className="flex items-center justify-center h-screen">
          <div className="text-center max-w-md">
            <div className="text-5xl mb-4">✅</div>
            <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--foreground)" }}>Report Approved</h1>
            <p className="mb-6" style={{ color: "var(--foreground-muted)" }}>PDF generated and ready for delivery.</p>
            <div className="flex flex-col gap-3">
              <a href={`http://localhost:8000${pdfUrl}`} target="_blank" className="px-6 py-3 rounded-full text-base font-semibold text-center" style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}>
                Download PDF
              </a>
              <a href={`/report/${draft.draft_id}`} className="px-6 py-3 rounded-full text-base font-semibold text-center" style={{ border: "2px solid var(--border)", color: "var(--foreground)" }}>
                View Client Report
              </a>
              <a href="/dashboard" className="text-sm mt-2" style={{ color: "var(--foreground-muted)" }}>← Back to Dashboard</a>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // Review Interface
  return (
    <Layout activePage="review">
      <div className="p-8 max-w-4xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>Review Draft</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--foreground-muted)" }}>Review and approve before client delivery.</p>
          </div>
          {draft.quality_report && (
            <div className="px-4 py-2 rounded-full text-sm font-medium" style={{ backgroundColor: draft.quality_report.passed ? "var(--success-subtle)" : "var(--primary-subtle)", color: draft.quality_report.passed ? "var(--success)" : "var(--primary)", border: `1px solid ${draft.quality_report.passed ? "rgba(76,175,80,0.3)" : "rgba(232,168,48,0.3)"}` }}>
              {draft.quality_report.passed ? "✓" : "⚠"} Confidence: {Math.round(draft.quality_report.confidence_score * 100)}%
            </div>
          )}
        </div>

        {/* Narrative Card */}
        <div className="rounded-xl p-8 mb-6" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="prose prose-sm max-w-none">
            {draft.narrative.split("\n").map((line, i) => {
              if (line.startsWith("## ")) return <h3 key={i} className="text-base font-bold mt-6 mb-2 pb-1" style={{ color: "var(--foreground)", borderBottom: "1px solid var(--border)" }}>{line.replace("## ", "").replace(/^\d+\.\s*/, "")}</h3>;
              if (line.startsWith("### ")) return <h4 key={i} className="text-sm font-semibold mt-4 mb-1" style={{ color: "var(--foreground)" }}>{line.replace("### ", "")}</h4>;
              if (line.startsWith("|")) return <p key={i} className="font-mono text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>{line}</p>;
              if (line.startsWith("- ")) return <p key={i} className="ml-4 text-sm" style={{ color: "var(--foreground)" }}>• {line.slice(2)}</p>;
              if (line.trim() === "") return <div key={i} className="h-3" />;
              return <p key={i} className="text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>{line}</p>;
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button onClick={handleApprove} disabled={approving} className="flex-1 py-4 rounded-full text-lg font-bold transition-all disabled:opacity-50" style={{ backgroundColor: "var(--success)", color: "#fff" }}>
            {approving ? "Generating PDF..." : "Approve & Generate PDF"}
          </button>
          <button onClick={() => setShowReject(!showReject)} className="px-8 py-4 rounded-full text-lg font-bold transition-all" style={{ border: "2px solid var(--destructive)", color: "var(--destructive)" }}>
            Request Revision
          </button>
        </div>

        {/* Reject Form */}
        {showReject && (
          <div className="mt-4 rounded-xl p-6" style={{ backgroundColor: "var(--card)", border: "1px solid var(--destructive)" }}>
            <label className="text-sm font-medium mb-2 block" style={{ color: "var(--destructive)" }}>What needs to change?</label>
            <textarea
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="e.g., Concrete section should say Level 3 not Level 2..."
              rows={3}
              className="w-full rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2"
              style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            />
            <button onClick={handleReject} disabled={rejecting || !rejectComment.trim()} className="mt-3 px-6 py-2.5 rounded-full text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: "var(--destructive)" }}>
              {rejecting ? "Revising..." : "Send Back for Revision"}
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
