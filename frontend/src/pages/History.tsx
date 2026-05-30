import Layout from "../components/Layout";

interface ReportEntry {
  draft_id: string;
  date: string;
  project: string;
  status: string;
  photoCount: number;
  narrativeLength: number;
  qualityScore: number;
}

export default function History() {
  // Load history from localStorage
  const historyRaw = localStorage.getItem("report_history");
  const history: ReportEntry[] = historyRaw ? JSON.parse(historyRaw) : [];

  // If no history, show sample data for demo
  const reports: ReportEntry[] = history.length > 0 ? history : [
    { draft_id: localStorage.getItem("draft_id") || "demo-001", date: new Date().toISOString().split("T")[0], project: localStorage.getItem("project_name") || "My Project", status: "approved", photoCount: 5, narrativeLength: 1920, qualityScore: 95 },
  ].filter(r => r.draft_id !== "demo-001" || localStorage.getItem("draft_id"));

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return { bg: "var(--success-subtle)", color: "var(--success)", label: "Approved" };
      case "draft_ready":
        return { bg: "var(--primary-subtle)", color: "var(--primary)", label: "Draft Ready" };
      case "processing":
        return { bg: "rgba(136,146,164,0.1)", color: "var(--foreground-muted)", label: "Processing" };
      default:
        return { bg: "rgba(136,146,164,0.1)", color: "var(--foreground-muted)", label: status };
    }
  };

  return (
    <Layout activePage="dashboard">
      <div className="p-8 max-w-5xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>Report History</h1>
          <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>
            All generated reports with source documents and status.
          </p>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <p className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>{reports.length}</p>
            <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Total Reports</p>
          </div>
          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <p className="text-2xl font-bold" style={{ color: "var(--success)" }}>{reports.filter(r => r.status === "approved").length}</p>
            <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Approved</p>
          </div>
          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <p className="text-2xl font-bold" style={{ color: "var(--primary)" }}>{reports.reduce((sum, r) => sum + r.photoCount, 0)}</p>
            <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Photos Processed</p>
          </div>
          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
            <p className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>{reports.length > 0 ? Math.round(reports.reduce((sum, r) => sum + r.qualityScore, 0) / reports.length) : 0}%</p>
            <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>Avg Quality</p>
          </div>
        </div>

        {/* Report Table */}
        <div className="rounded-xl overflow-hidden" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 px-5 py-3 text-xs font-semibold uppercase tracking-wide" style={{ backgroundColor: "var(--surface)", color: "var(--foreground-muted)", borderBottom: "1px solid var(--border)" }}>
            <div className="col-span-2">Date</div>
            <div className="col-span-3">Project</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-1">Photos</div>
            <div className="col-span-2">Quality</div>
            <div className="col-span-2">Actions</div>
          </div>

          {/* Table Rows */}
          {reports.length === 0 ? (
            <div className="px-5 py-12 text-center">
              <p className="text-sm" style={{ color: "var(--foreground-muted)" }}>No reports yet. Submit your first daily report to see history here.</p>
            </div>
          ) : (
            reports.map((report, i) => {
              const badge = getStatusBadge(report.status);
              return (
                <div key={i} className="grid grid-cols-12 gap-4 px-5 py-4 items-center transition-all hover:opacity-90" style={{ borderBottom: i < reports.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <div className="col-span-2">
                    <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{report.date}</p>
                  </div>
                  <div className="col-span-3">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--foreground)" }}>{report.project}</p>
                    <p className="text-xs truncate" style={{ color: "var(--foreground-muted)" }}>{report.narrativeLength} chars</p>
                  </div>
                  <div className="col-span-2">
                    <span className="inline-flex px-2.5 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: badge.bg, color: badge.color }}>
                      {badge.label}
                    </span>
                  </div>
                  <div className="col-span-1">
                    <p className="text-sm" style={{ color: "var(--foreground)" }}>{report.photoCount}</p>
                  </div>
                  <div className="col-span-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: "var(--surface)" }}>
                        <div className="h-full rounded-full" style={{ width: `${report.qualityScore}%`, backgroundColor: report.qualityScore >= 80 ? "var(--success)" : "var(--primary)" }}></div>
                      </div>
                      <span className="text-xs font-medium" style={{ color: "var(--foreground-muted)" }}>{report.qualityScore}%</span>
                    </div>
                  </div>
                  <div className="col-span-2 flex gap-2">
                    <a href={`/review`} onClick={() => localStorage.setItem("draft_id", report.draft_id)} className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all" style={{ backgroundColor: "var(--primary-subtle)", color: "var(--primary)" }}>
                      View
                    </a>
                    <a href={`http://localhost:8000/api/v1/drafts/${report.draft_id}/pdf`} target="_blank" className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all" style={{ border: "1px solid var(--border)", color: "var(--foreground-muted)" }}>
                      PDF
                    </a>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </Layout>
  );
}
