import { useEffect, useState, type ChangeEvent } from "react";
import { listDocuments, uploadDocument, type DocumentOut } from "../api/client";

export default function DocumentLibrary() {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold">Document Library</h2>
      <p className="mt-1 text-slate-500">
        Upload and browse ingested documents — backed by the live Phase 1 ingestion pipeline.
      </p>

      <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
        {uploading ? "Uploading…" : "Upload document"}
        <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
      </label>

      {error && (
        <p className="mt-3 text-sm text-red-600">
          {error} — is the backend running? (<code>uvicorn app.main:app --reload</code> in <code>backend/</code>)
        </p>
      )}

      <table className="mt-6 w-full border-collapse overflow-hidden rounded-lg border border-slate-200 bg-white text-sm">
        <thead className="bg-slate-100 text-left">
          <tr>
            <th className="p-3">Filename</th>
            <th className="p-3">Type</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr key={doc.id} className="border-t border-slate-200">
              <td className="p-3">{doc.filename}</td>
              <td className="p-3">{doc.document_type}</td>
              <td className="p-3">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    doc.status === "done"
                      ? "bg-green-100 text-green-700"
                      : doc.status === "failed"
                        ? "bg-red-100 text-red-700"
                        : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {doc.status}
                </span>
              </td>
            </tr>
          ))}
          {documents.length === 0 && !error && (
            <tr>
              <td className="p-3 text-slate-400" colSpan={3}>
                No documents ingested yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
