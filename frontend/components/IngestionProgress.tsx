"use client";

import { useEffect, useRef, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { getProjectStatus } from "@/lib/api";

interface IngestionProgressProps {
  projectId: number;
  onComplete: (status: "ready" | "failed") => void;
}

const POLL_INTERVAL_MS = 2000;

export function IngestionProgress({
  projectId,
  onComplete,
}: IngestionProgressProps) {
  const [progress, setProgress] = useState(0);
  const [label, setLabel] = useState<string | null>("Starting...");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Keep onComplete in a ref so the interval closure is always fresh
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await getProjectStatus(projectId);
        setProgress(data.ingestion_progress);
        setLabel(data.current_stage_label);

        if (data.status === "ready" || data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          onCompleteRef.current(data.status);
        }
      } catch {
        // Silently ignore transient network errors while polling
      }
    };

    poll(); // immediate first call
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [projectId]);

  return (
    <div className="space-y-1.5 py-1">
      <Progress value={progress} className="h-2" />
      <p className="text-xs text-muted-foreground">{label ?? "Processing..."}</p>
    </div>
  );
}
