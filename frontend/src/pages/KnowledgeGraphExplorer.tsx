import { useEffect, useState } from "react";
import { getEquipment360, getGraphStats, type Equipment360, type GraphStats } from "../api/client";

export default function KnowledgeGraphExplorer() {
  const [tag, setTag] = useState("");
  const [result, setResult] = useState<Equipment360 | null>(null);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getGraphStats()
      .then(setStats)
      .catch((e) => setError((e as Error).message));
  }, []);

  async function search() {
    if (!tag) return;
    try {
      setResult(await getEquipment360(tag));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const totalNodes = stats ? Object.values(stats.node_counts).reduce((a, b) => a + b, 0) : null;

  return (
    <div>
      <h2 className="text-2xl font-semibold">Knowledge Graph Explorer</h2>
      <p className="mt-1 text-slate-500">
        Search an equipment tag to see its 360° view — every linked document and person.
      </p>

      {stats && (
        <div className="mt-4 flex gap-4 text-sm text-slate-600">
          <span>Nodes: {totalNodes}</span>
          <span>Edges: {stats.edge_count}</span>
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <input
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="Equipment tag, e.g. P-101"
          className="w-64 rounded-md border border-slate-300 p-2 text-sm"
        />
        <button
          onClick={search}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Search
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {result && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
          {result.equipment ? (
            <>
              <p className="font-medium">{result.equipment.properties?.tag ?? tag}</p>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                {result.linked.map((l, i) => (
                  <li key={i}>
                    {l.relationship} → {l.node?.label ?? "?"} ({JSON.stringify(l.node?.properties ?? {})})
                  </li>
                ))}
                {result.linked.length === 0 && <li className="text-slate-400">No linked records yet.</li>}
              </ul>
            </>
          ) : (
            <p className="text-slate-400">
              No equipment found for &quot;{tag}&quot; yet — ingest a document that mentions it first.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
