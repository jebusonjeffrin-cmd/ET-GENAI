import { useState } from "react";
import { investigateRCA, type RCAResult } from "../api/client";

const fixtureEquipment = [
  { tag: "P-101", risk: "Medium", lastFailure: "2025-03-12" },
  { tag: "V-200", risk: "Low", lastFailure: "—" },
  { tag: "C-305", risk: "High", lastFailure: "2026-01-04" },
];

const riskColor: Record<string, string> = {
  High: "bg-red-100 text-red-700",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-green-100 text-green-700",
};

export default function Maintenance() {
  const [description, setDescription] = useState(
    "Compressor C-305 tripped on overcurrent during startup.",
  );
  const [result, setResult] = useState<RCAResult | null>(null);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function investigate() {
    if (!description.trim() || investigating) return;
    setInvestigating(true);
    setError(null);
    try {
      setResult(await investigateRCA(description));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setInvestigating(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold">Maintenance Intelligence & RCA</h2>
      <p className="mt-1 text-slate-500">
        RCA Workspace below runs a live agentic investigation over the ingested corpus. Equipment
        Health is illustrative — a trained failure-prediction model is future work, not built this
        pass.
      </p>

      <div className="mt-6">
        <h3 className="text-lg font-medium">Equipment Health</h3>
        <table className="mt-2 w-full border-collapse overflow-hidden rounded-lg border border-slate-200 bg-white text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3">Tag</th>
              <th className="p-3">Risk</th>
              <th className="p-3">Last failure</th>
            </tr>
          </thead>
          <tbody>
            {fixtureEquipment.map((eq) => (
              <tr key={eq.tag} className="border-t border-slate-200">
                <td className="p-3">{eq.tag}</td>
                <td className="p-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor[eq.risk]}`}>
                    {eq.risk}
                  </span>
                </td>
                <td className="p-3">{eq.lastFailure}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <h3 className="text-lg font-medium">RCA Workspace</h3>
        <p className="mt-1 text-sm text-slate-500">
          Describe an incident. The agent gathers evidence from the knowledge graph and ingested
          documents before drafting a root-cause chain.
        </p>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="mt-2 w-full rounded-md border border-slate-300 p-2 text-sm"
        />
        <button
          onClick={investigate}
          disabled={investigating}
          className="mt-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {investigating ? "Investigating…" : "Investigate"}
        </button>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        {result && (
          <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-medium text-slate-700">Root-cause findings</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{result.root_cause_chain}</p>

            {result.evidence.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-medium uppercase text-slate-400">Evidence gathered</p>
                <ul className="mt-2 space-y-2">
                  {result.evidence.map((e, i) => (
                    <li key={i} className="rounded border border-slate-100 bg-slate-50 p-2 text-xs">
                      <span className="font-mono font-medium">{e.tool}</span>
                      <span className="text-slate-500"> ({JSON.stringify(e.arguments)})</span>
                      <p className="mt-1 text-slate-600">{e.result_summary}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
