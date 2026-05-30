import type { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
  activePage?: "submit" | "review" | "dashboard" | "report" | "history" | "evaluation";
}

const NAV_ITEMS = [
  { id: "submit", label: "Capture", href: "/" },
  { id: "review", label: "Review", href: "/review" },
  { id: "dashboard", label: "Reports", href: "/dashboard" },
  { id: "history", label: "History", href: "/history" },
  { id: "evaluation", label: "Evaluation", href: "/evaluation" },
];

export default function Layout({ children, activePage = "submit" }: LayoutProps) {
  const projectName = localStorage.getItem("project_name") || "My Project";
  const superintendent = localStorage.getItem("superintendent") || "";
  const today = new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: "var(--background)" }}>
      {/* Sidebar */}
      <aside className="w-60 flex flex-col fixed h-full z-20" style={{ backgroundColor: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}>
        {/* Logo */}
        <div className="px-6 py-5" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
          <h1 className="text-lg font-extrabold tracking-tight" style={{ color: "var(--primary)" }}>SiteNarrator</h1>
          <p className="text-[10px] mt-0.5 uppercase tracking-widest" style={{ color: "var(--foreground-muted)" }}>Construction AI</p>
        </div>

        {/* Project Card — clickable to switch */}
        <div
          className="mx-3 mt-4 mb-2 p-4 rounded-xl cursor-pointer transition-all"
          style={{ backgroundColor: "var(--primary-subtle)", border: "1px solid var(--border)" }}
          onClick={() => { window.location.href = "/new-project"; }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
        >
          <div className="flex items-center justify-between">
            <p className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: "var(--primary)" }}>Active Project</p>
            <span className="text-[10px]" style={{ color: "var(--foreground-muted)" }}>Switch ↗</span>
          </div>
          <p className="text-sm font-bold mt-1 truncate" style={{ color: "var(--foreground)" }}>{projectName}</p>
          <p className="text-xs mt-0.5" style={{ color: "var(--foreground-muted)" }}>{today}</p>
        </div>

        {/* New Project Button */}
        <div className="mx-3 mb-4">
          <a
            href="/new-project"
            className="block w-full px-4 py-2.5 rounded-lg text-xs font-medium text-center transition-all"
            style={{ border: "1px dashed var(--border)", color: "var(--foreground-muted)" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.color = "var(--primary)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--foreground-muted)"; }}
          >
            + New Project
          </a>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.id}
              href={item.href}
              className="block px-4 py-3 rounded-lg text-sm font-medium transition-all"
              style={
                activePage === item.id
                  ? { backgroundColor: "var(--primary)", color: "#1a1a1a" }
                  : { color: "var(--foreground-muted)" }
              }
              onMouseEnter={(e) => { if (activePage !== item.id) e.currentTarget.style.backgroundColor = "var(--card)"; }}
              onMouseLeave={(e) => { if (activePage !== item.id) e.currentTarget.style.backgroundColor = "transparent"; }}
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Status */}
        <div className="mx-3 mb-3 p-3 rounded-lg" style={{ backgroundColor: "var(--success-subtle)", border: "1px solid rgba(76,175,80,0.2)" }}>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: "var(--success)" }}></div>
            <p className="text-xs font-medium" style={{ color: "var(--success)" }}>System Online</p>
          </div>
        </div>

        {/* User */}
        {superintendent && (
          <div className="px-4 py-4" style={{ borderTop: "1px solid var(--sidebar-border)" }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold" style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}>
                {superintendent.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{superintendent}</p>
                <p className="text-[11px]" style={{ color: "var(--foreground-muted)" }}>Superintendent</p>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-60">
        {children}
      </main>
    </div>
  );
}
