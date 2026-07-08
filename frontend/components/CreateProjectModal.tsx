"use client";

import { useState, useRef, type ChangeEvent } from "react";
import { GitBranch, Upload, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createProject, type ProjectResponse } from "@/lib/api";

interface CreateProjectModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (project: ProjectResponse) => void;
}

const MAX_ZIP_BYTES = 100 * 1024 * 1024; // 100 MB

export function CreateProjectModal({
  open,
  onClose,
  onCreated,
}: CreateProjectModalProps) {
  const [tab, setTab] = useState<"github" | "zip">("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [projectName, setProjectName] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function reset() {
    setGithubUrl("");
    setProjectName("");
    setZipFile(null);
    setError(null);
    setLoading(false);
    setTab("github");
  }

  function handleClose() {
    if (loading) return;
    reset();
    onClose();
  }

  function handleOpenChange(open: boolean) {
    if (!open) handleClose();
  }

  async function handleSubmit() {
    setError(null);

    if (!projectName.trim()) {
      setError("Project name is required.");
      return;
    }

    if (tab === "github") {
      if (!githubUrl.startsWith("https://github.com/")) {
        setError("URL must start with https://github.com/");
        return;
      }
    } else {
      if (!zipFile) {
        setError("Please select a ZIP file.");
        return;
      }
      if (zipFile.size > MAX_ZIP_BYTES) {
        setError("ZIP file must be under 100 MB.");
        return;
      }
    }

    setLoading(true);
    try {
      const project = await createProject({
        name: projectName.trim(),
        source_type: tab,
        source_url: tab === "github" ? githubUrl.trim() : undefined,
      });
      reset();
      onCreated(project);
    } catch (err: unknown) {
      const msg =
        (err as { message?: string })?.message ?? "Failed to create project.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Project</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="proj-name">Project name</Label>
            <Input
              id="proj-name"
              placeholder="My Awesome Repo"
              value={projectName}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setProjectName(e.target.value)
              }
              disabled={loading}
            />
          </div>

          <Tabs
            value={tab}
            onValueChange={(v: string) => setTab(v as "github" | "zip")}
          >
            <TabsList className="w-full">
              <TabsTrigger value="github" className="flex-1">
                <GitBranch size={14} className="mr-1.5" />
                GitHub URL
              </TabsTrigger>
              <TabsTrigger value="zip" className="flex-1">
                <Upload size={14} className="mr-1.5" />
                ZIP Upload
              </TabsTrigger>
            </TabsList>

            <TabsContent value="github" className="mt-3">
              <div className="space-y-1.5">
                <Label htmlFor="github-url">Repository URL</Label>
                <Input
                  id="github-url"
                  placeholder="https://github.com/owner/repo"
                  value={githubUrl}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setGithubUrl(e.target.value)
                  }
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Public repositories only.
                </p>
              </div>
            </TabsContent>

            <TabsContent value="zip" className="mt-3">
              <div className="space-y-1.5">
                <Label>ZIP file (max 100 MB)</Label>
                <div
                  className="border-2 border-dashed rounded-md p-6 text-center cursor-pointer hover:border-primary transition-colors"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {zipFile ? (
                    <p className="text-sm font-medium">{zipFile.name}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Click to select a .zip file
                    </p>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  className="hidden"
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setZipFile(e.target.files?.[0] ?? null)
                  }
                />
              </div>
            </TabsContent>
          </Tabs>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && (
              <Loader2 size={14} className="mr-1.5 animate-spin" />
            )}
            Create Project
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
