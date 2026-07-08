"use client";

import { Trash2, FileCode, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProjectResponse } from "@/lib/api";

interface ProjectCardProps {
  project: ProjectResponse;
  onDelete: (id: number) => void;
  onClick?: (id: number) => void;
}

const STATUS_BADGE: Record<
  ProjectResponse["status"],
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  pending:   { label: "Pending",   variant: "secondary" },
  ingesting: { label: "Ingesting", variant: "outline" },
  ready:     { label: "Ready",     variant: "default" },
  failed:    { label: "Failed",    variant: "destructive" },
};

export function ProjectCard({ project, onDelete, onClick }: ProjectCardProps) {
  const badge = STATUS_BADGE[project.status];

  const handleCardClick = () => {
    if (project.status === "ready") onClick?.(project.id);
  };

  return (
    <Card
      className={`transition-shadow ${
        project.status === "ready"
          ? "cursor-pointer hover:shadow-md"
          : "opacity-80"
      }`}
      onClick={handleCardClick}
    >
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-semibold truncate pr-2">
          {project.name}
        </CardTitle>
        <Badge variant={badge.variant} className="shrink-0">
          {badge.label}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-2">
        {/* File count */}
        {project.total_files != null && (
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <FileCode size={14} />
            <span>{project.total_files.toLocaleString()} files</span>
          </div>
        )}

        {/* Created date */}
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Calendar size={14} />
          <span>{new Date(project.created_at).toLocaleDateString()}</span>
        </div>

        {/* Error message */}
        {project.status === "failed" && project.error_message && (
          <p className="text-xs text-destructive mt-1 line-clamp-2">
            {project.error_message}
          </p>
        )}

        {/* Delete button — stops propagation so the card click doesn't fire */}
        <div className="flex justify-end pt-1">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(project.id);
            }}
          >
            <Trash2 size={14} className="mr-1" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
