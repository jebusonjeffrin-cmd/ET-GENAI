import { useState } from "react";

interface Turn {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
}

const FIXTURE_RESPONSE: Turn = {
  role: "assistant",
  content:
    "This is a Phase 0 mock response. Once Phase 2 lands, this answer will be generated live by the local model against your ingested corpus, with real source citations.",
  citations: ["mock-source-1.pdf", "mock-source-2.pdf"],
};

export default function Copilot() {
  const [turns, setTurns] = useState<Turn[]>([
    { role: "assistant", content: "Ask me anything about the ingested plant documents." },
  ]);
  const [input, setInput] = useState("");

  function send() {
    if (!input.trim()) return;
    const userTurn: Turn = { role: "user", content: input };
    setTurns((prev) => [...prev, userTurn, FIXTURE_RESPONSE]);
    setInput("");
  }

  return (
    <div className="flex h-full flex-col">
      <h2 className="text-2xl font-semibold">Expert Knowledge Copilot</h2>
      <p className="mt-1 text-slate-500">
        Phase 2 wires this to live RAG synthesis against the local model. UI is complete and mobile-first now.
      </p>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
        {turns.map((t, i) => (
          <div
            key={i}
            className={`max-w-lg rounded-lg p-3 text-sm ${
              t.role === "user" ? "ml-auto bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
            }`}
          >
            <p>{t.content}</p>
            {t.citations && (
              <div className="mt-2 flex flex-wrap gap-1">
                {t.citations.map((c) => (
                  <span key={c} className="rounded bg-white/70 px-2 py-0.5 text-xs text-brand-700">
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question…"
          className="flex-1 rounded-md border border-slate-300 p-3 text-sm"
        />
        <button
          onClick={send}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Send
        </button>
      </div>
    </div>
  );
}
