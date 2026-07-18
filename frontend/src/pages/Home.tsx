import { useRole } from "../layout/RoleContext";

export default function Home() {
  const { role } = useRole();
  return (
    <div>
      <h2 className="text-2xl font-semibold">Welcome back — viewing as {role}</h2>
      <p className="mt-1 text-slate-500">
        Command center for plant knowledge, maintenance intelligence, and compliance.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { title: "Recent documents", value: "See Document Library" },
          { title: "Active RCA investigations", value: "Seeded scenario — see Maintenance & RCA" },
          { title: "Knowledge graph coverage", value: "See Knowledge Graph" },
        ].map((card) => (
          <div key={card.title} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-500">{card.title}</p>
            <p className="mt-2 text-lg font-semibold">{card.value}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 rounded-lg border border-brand-100 bg-brand-50 p-4">
        <p className="text-sm font-medium text-brand-700">Ask anything</p>
        <p className="mt-1 text-sm text-brand-600">
          Go to Copilot to ask a question across the ingested corpus.
        </p>
      </div>
    </div>
  );
}
