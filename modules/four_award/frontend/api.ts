import type { ModuleRunItem } from "./types";

export async function fetchFourAwardRuns(): Promise<{
  module: string;
  jobs: Array<{ name: string; enabled: boolean }>;
  runs: ModuleRunItem[];
  can_run: boolean;
  hits: number;
  limit: number;
  non_blank: boolean;
  returned: number;
  cache: boolean;
  scan_limit: number;
  scanned: number;
  scan_capped: boolean;
  unique: boolean;
}> {
  const params = new URLSearchParams({
    hits: "50",
    non_blank: "1",
    scan_limit: "50000",
    unique: "0",
  });
  const r = await fetch(`/api/v1/four-award/runs?${params.toString()}`);
  const data = await r.json();
  if (!r.ok) {
    throw new Error(data?.detail || `Failed to fetch 4award runs: ${r.status}`);
  }
  return {
    module: data.module || "four_award",
    jobs: Array.isArray(data.jobs) ? data.jobs : [],
    runs: Array.isArray(data.runs) ? data.runs : [],
    can_run: !!data.can_run,
    hits: Number(data.hits || 50),
    limit: Number(data.limit || 50),
    non_blank: !!data.non_blank,
    returned: Number(data.returned || 0),
    cache: data.cache === true,
    scan_limit: Number(data.scan_limit || 50000),
    scanned: Number(data.scanned || 0),
    scan_capped: data.scan_capped === true,
    unique: data.unique !== false,
  };
}

export async function fetchFourAwardRun(runId: number): Promise<{ run: ModuleRunItem }> {
  const r = await fetch(`/api/v1/four-award/runs/${encodeURIComponent(runId)}`);
  const data = await r.json();
  if (!r.ok) {
    throw new Error(data?.detail || `Failed to fetch 4award run: ${r.status}`);
  }
  return data;
}

export async function queueFourAwardHistoricalDiffTest(payload: {
  diff: string;
  job_name?: string;
}): Promise<{
  module: string;
  job: string;
  run_id: number;
  status: string;
  detail?: string;
}> {
  const r = await fetch("/api/v1/four-award/test-runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) {
    throw new Error(data?.detail || `Failed to queue 4award test: ${r.status}`);
  }
  return data;
}
