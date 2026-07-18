import { useEffect, useState } from "react";
import { getGraphStats, listDocuments, type DocumentOut, type GraphStats } from "../api/client";

export default function Admin() {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [stats, setStats] = useState<GraphStats | null>(null);

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => {});
    getGraphStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  const done = documents.filter((d) => d.status === "done").length;
  const failed = documents.filter((d) => d.status === "failed").length;
  const totalNodes = stats ? Object.values(stats.node_counts).reduce((a, b) => a + b, 0) : null;

  return (
    <div>
      <h2 className="text-2xl font-semibold">Admin — Ingestion Monitor</h2>
      <p className="mt-1 text-slate-500">Live numbers from the Phase 1 ingestion pipeline.</p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Documents ingested", value: documents.length },
          { label: "Succeeded", value: done },
          { label: "Failed", value: failed },
          { label: "Graph nodes", value: totalNodes ?? "—" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium text-slate-500">{s.label}</p>
            <p className="mt-1 text-xl font-semibold">{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
