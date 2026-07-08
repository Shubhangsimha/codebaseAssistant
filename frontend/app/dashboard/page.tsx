"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "@/components/ProjectCard";
import { CreateProjectModal } from "@/components/CreateProjectModal";
import { IngestionProgress } from "@/components/IngestionProgress";
import {
  getProjects,
  deleteProject,
  triggerIngestion,
  type ProjectResponse,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  // Track which project IDs are actively being ingested
  const [ingestingIds, setIngestingIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchProjects();
  }, []);

  async function fetchProjects() {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch {
      toast.error("Failed to load projects.");
    } finally {
      setLoading(false);
    }
  }

  async function handleProjectCreated(project: ProjectResponse) {
    // Add to list immediately with pending status
    setProjects((prev) => [project, ...prev]);
    setModalOpen(false);

    // Start ingestion
    setIngestingIds((prev) => new Set(prev).add(project.id));
    try {
      await triggerIngestion(project.id);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message ?? "Ingestion failed.";
      toast.error(msg);
      // Refresh to get the failed status from the server
      await fetchProjects();
      setIngestingIds((prev) => {
        const s = new Set(prev);
        s.delete(project.id);
        return s;
      });
    }
  }

  function handleIngestionComplete(
    projectId: number,
    status: "ready" | "failed"
  ) {
    setIngestingIds((prev) => {
      const s = new Set(prev);
      s.delete(projectId);
      return s;
    });

    if (status === "ready") {
      toast.success("Project is ready!");
    } else {
      toast.error("Ingestion failed. Check the project for details.");
    }

    // Refresh the full list to get updated file counts etc.
    fetchProjects();
  }

  async function handleDelete(projectId: number) {
    try {
      await deleteProject(projectId);
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
      toast.success("Project deleted.");
    } catch {
      toast.error("Failed to delete project.");
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">CodeSage</h1>
            <p className="text-sm text-muted-foreground">
              AI Developer Intelligence Platform
            </p>
          </div>
          <Button onClick={() => setModalOpen(true)}>
            <Plus size={16} className="mr-1.5" />
            New Project
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-40 rounded-lg bg-muted animate-pulse"
              />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <p className="text-2xl font-semibold mb-2">No projects yet</p>
            <p className="text-muted-foreground mb-6">
              Create your first project to start exploring a codebase with AI.
            </p>
            <Button onClick={() => setModalOpen(true)}>
              <Plus size={16} className="mr-1.5" />
              New Project
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <div key={project.id} className="flex flex-col gap-2">
                <ProjectCard
                  project={project}
                  onDelete={handleDelete}
                  onClick={(id) => router.push(`/projects/${id}`)}
                />
                {ingestingIds.has(project.id) && (
                  <IngestionProgress
                    projectId={project.id}
                    onComplete={(status) =>
                      handleIngestionComplete(project.id, status)
                    }
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      <CreateProjectModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={handleProjectCreated}
      />
    </div>
  );
}
