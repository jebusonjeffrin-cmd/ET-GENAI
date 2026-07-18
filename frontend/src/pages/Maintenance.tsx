const fixtureEquipment = [
  { tag: "P-101", risk: "Medium", lastFailure: "2025-03-12" },
  { tag: "V-200", risk: "Low", lastFailure: "—" },
  { tag: "C-305", risk: "High", lastFailure: "2026-01-04" },
];

const fixtureRca = [
  { question: "Why did C-305 trip?", answer: "Overcurrent detected on motor phase B." },
  { question: "Why did overcurrent occur?", answer: "Bearing degradation increased mechanical load." },
  {
    question: "Why was bearing degradation not caught earlier?",
    answer: "Last inspection interval exceeded the OEM-recommended schedule.",
  },
];

const riskColor: Record<string, string> = {
  High: "bg-red-100 text-red-700",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-green-100 text-green-700",
};

export default function Maintenance() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Maintenance Intelligence & RCA</h2>
      <p className="mt-1 text-slate-500">
        Phase 3 wires this to a live agentic RCA loop over real work orders. UI is complete now.
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
        <h3 className="text-lg font-medium">RCA Workspace — C-305 (seeded scenario)</h3>
        <ol className="mt-2 space-y-2">
          {fixtureRca.map((step, i) => (
            <li key={i} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
              <p className="font-medium">{step.question}</p>
              <p className="mt-1 text-slate-600">{step.answer}</p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
