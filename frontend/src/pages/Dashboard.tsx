import { useState } from "react";
import Layout from "../components/Layout";

export default function Dashboard() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState(new Date().toISOString().split("T")[0]);
  const [generating, setGenerating] = useState(false);

  const draftId = localStorage.getItem("draft_id");

  const handlePeriodReport = async () => {
    if (!dateFrom || !dateTo) return;
    setGenerating(true);
    try {
      const resp = await fetch("http://localhost:8000/api/v1/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: localStorage.getItem("project_id") || "PROJ-001",
          date_from: dateFrom,
          date_to: dateTo,
          requested_by: localStorage.getItem("superintendent") || "PC",
        }),
      });
      const data = await resp.json();
      alert(`Period report generation started. Estimated ${data.estimated_pages} pages.`);
    } catch {
      alert("Failed to generate period report.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Layout activePage="dashboard">
      <div className="p-8 max-w-5xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>Reports</h1>
          <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>Manage daily reports and generate period summaries.</p>
        </div>

        {/* Recent Reports */}
        <div className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: "var(--foreground-muted)" }}>Recent Reports</h2>
          <div className="space-y-3">
            {draftId ? (
              <div className="rounded-xl p-5 flex items-center justify-between" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
                <div>
                  <p className="font-semibold text-sm" style={{ color: "var(--foreground)" }}>Daily Report — {new Date().toLocaleDateString()}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--foreground-muted)" }}>Status: Draft Ready</p>
                </div>
                <div className="flex gap-2">
                  <a href="/review" className="px-4 py-2 rounded-lg text-xs font-medium" style={{ backgroundColor: "var(--success-subtle)", color: "var(--success)" }}>
                    Review
                  </a>
                  <a href={`/report/${draftId}`} className="px-4 py-2 rounded-lg text-xs font-medium" style={{ border: "1px solid var(--border)", color: "var(--foreground-muted)" }}>
                    View
                  </a>
                </div>
              </div>
            ) : (
              <div className="rounded-xl p-8 text-center" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
                <p className="text-sm" style={{ color: "var(--foreground-muted)" }}>No reports yet. Submit field data to generate your first report.</p>
              </div>
            )}
          </div>
        </div>

        {/* Period Summary Generator */}
        <div className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: "var(--foreground-muted)" }}>Generate Period Summary</h2>
          <div className="rounded-xl p-6" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <p className="text-sm mb-4" style={{ color: "var(--foreground-muted)" }}>
              Select a date range to generate a comprehensive summary report across all daily reports in that period.
            </p>
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="mt-1.5 w-full rounded-lg px-4 py-3 text-sm focus:outline-none"
                  style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div className="flex-1">
                <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="mt-1.5 w-full rounded-lg px-4 py-3 text-sm focus:outline-none"
                  style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <button
                onClick={handlePeriodReport}
                disabled={generating || !dateFrom || !dateTo}
                className="px-6 py-3 rounded-full text-sm font-bold disabled:opacity-40 whitespace-nowrap"
                style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}
              >
                {generating ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: "var(--foreground-muted)" }}>Quick Stats</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl p-5 text-center" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
              <p className="text-3xl font-bold" style={{ color: "var(--foreground)" }}>{draftId ? "1" : "0"}</p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Reports Today</p>
            </div>
            <div className="rounded-xl p-5 text-center" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
              <p className="text-3xl font-bold" style={{ color: "var(--success)" }}>100%</p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Quality Score</p>
            </div>
            <div className="rounded-xl p-5 text-center" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
              <p className="text-3xl font-bold" style={{ color: "var(--foreground)" }}>0</p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Pending Review</p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
