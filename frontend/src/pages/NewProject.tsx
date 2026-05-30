import Layout from "../components/Layout";
import { useState } from "react";

export default function NewProject() {
  const [name, setName] = useState("");
  const [projectId, setProjectId] = useState("");
  const [location, setLocation] = useState("");

  // Load saved projects from localStorage
  const savedProjectsRaw = localStorage.getItem("saved_projects");
  let savedProjects: { name: string; id: string; location: string }[] = savedProjectsRaw ? JSON.parse(savedProjectsRaw) : [];

  // Always include the current active project in the list
  const currentName = localStorage.getItem("project_name") || "";
  const currentId = localStorage.getItem("project_id") || "";
  const currentLocation = localStorage.getItem("project_location") || "";
  if (currentId && !savedProjects.find(p => p.id === currentId)) {
    savedProjects = [{ name: currentName, id: currentId, location: currentLocation }, ...savedProjects];
  }

  const handleCreate = () => {
    if (!name.trim() || !projectId.trim()) return;
    localStorage.setItem("project_name", name);
    localStorage.setItem("project_id", projectId);
    if (location) localStorage.setItem("project_location", location);

    // Save to project list
    const updated = [...savedProjects.filter(p => p.id !== projectId), { name, id: projectId, location }];
    localStorage.setItem("saved_projects", JSON.stringify(updated));

    window.location.href = "/";
  };

  const handleSelectProject = (project: { name: string; id: string; location: string }) => {
    localStorage.setItem("project_name", project.name);
    localStorage.setItem("project_id", project.id);
    if (project.location) localStorage.setItem("project_location", project.location);
    window.location.href = "/";
  };

  return (
    <Layout activePage="submit">
      <div className="p-8 max-w-lg">
        <div className="mb-8">
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>New Project</h1>
          <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>Set up a new construction site to start generating reports.</p>
        </div>

        <div className="rounded-xl p-6 space-y-5" style={{ backgroundColor: "var(--card)", border: "1px solid var(--border)" }}>
          {/* Previous Projects */}
          {savedProjects.length > 0 && (
            <div className="mb-6">
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Previous Projects</label>
              <div className="mt-2 space-y-2">
                {savedProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => handleSelectProject(project)}
                    className="w-full text-left px-4 py-3 rounded-lg transition-all flex items-center justify-between"
                    style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                  >
                    <div>
                      <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{project.name}</p>
                      <p className="text-xs" style={{ color: "var(--foreground-muted)" }}>{project.id}{project.location ? ` • ${project.location}` : ""}</p>
                    </div>
                    <span className="text-xs font-medium" style={{ color: "var(--primary)" }}>Select →</span>
                  </button>
                ))}
              </div>
              <div className="my-4 flex items-center gap-3">
                <div className="flex-1 h-px" style={{ backgroundColor: "var(--border)" }}></div>
                <span className="text-xs" style={{ color: "var(--foreground-muted)" }}>or create new</span>
                <div className="flex-1 h-px" style={{ backgroundColor: "var(--border)" }}></div>
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Project Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Sunrise Apartments — Tower B"
              className="mt-1.5 w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2"
              style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }}
            />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Project ID</label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="PROJ-2024-002"
              className="mt-1.5 w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2"
              style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }}
            />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--foreground-muted)" }}>Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="1234 Pine Street, Seattle, WA"
              className="mt-1.5 w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2"
              style={{ backgroundColor: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--foreground)" }}
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || !projectId.trim()}
            className="w-full py-3.5 rounded-full text-sm font-bold transition-all disabled:opacity-40"
            style={{ backgroundColor: "var(--primary)", color: "#1a1a1a" }}
          >
            Create Project →
          </button>
        </div>
      </div>
    </Layout>
  );
}
