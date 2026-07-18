import { useState } from "react";
import { askCopilot } from "../api/client";

interface Turn {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
}

export default function Copilot() {
  const [turns, setTurns] = useState<Turn[]>([
    { role: "assistant", content: "Ask me anything about the ingested plant documents." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    if (!input.trim() || sending) return;
    const question = input;
    setTurns((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setSending(true);
    try {
      const result = await askCopilot(question);
      setTurns((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer || "No answer produced — the corpus may not cover this yet.",
          citations: result.citations.map((c) => `[${c.index}] document ${c.document_id}`),
        },
      ]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        { role: "assistant", content: `Couldn't reach the Copilot backend: ${(err as Error).message}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <h2 className="text-2xl font-semibold">Expert Knowledge Copilot</h2>
      <p className="mt-1 text-slate-500">
        Live RAG synthesis over the ingested corpus (hybrid vector + keyword + graph retrieval), with
        source citations.
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
            {t.citations && t.citations.length > 0 && (
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
        {sending && <p className="text-sm text-slate-400">Thinking…</p>}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question…"
          className="flex-1 rounded-md border border-slate-300 p-3 text-sm"
          disabled={sending}
        />
        <button
          onClick={send}
          disabled={sending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
