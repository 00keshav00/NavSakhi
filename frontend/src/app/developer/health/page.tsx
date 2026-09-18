"use client";

import { useHealth } from "../../../hooks/useHealth";

export default function HealthCheckPage() {
  const { data, error, isLoading } = useHealth();

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background p-6">
      <div className="flex w-full max-w-md flex-col items-center justify-center gap-6 rounded-3xl border border-border bg-card p-10 text-center shadow-2xl">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          System Connectivity
        </h1>

        {isLoading && (
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">Pinging SafeShe Backend...</p>
          </div>
        )}

        {error && (
          <div className="flex w-full flex-col items-center gap-3 rounded-2xl border border-danger/30 bg-danger/10 p-6">
            <span className="rounded-full bg-danger px-3 py-1 text-xs font-bold uppercase tracking-wider text-white">
              Connection Failed
            </span>
            <p className="text-sm text-danger">{error.message}</p>
          </div>
        )}

        {data && (
          <div className="flex w-full flex-col items-center gap-3 rounded-2xl border border-success/30 bg-success/10 p-6">
            <span className="rounded-full bg-success px-3 py-1 text-xs font-bold uppercase tracking-wider text-white">
              Backend Connected
            </span>
            <div className="mt-2 text-sm text-foreground">
              <p><strong>App:</strong> {data.app}</p>
              <p><strong>Version:</strong> {data.version}</p>
              <p><strong>Status:</strong> {data.status}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
