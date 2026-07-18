const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface DocumentOut {
  id: string;
  filename: string;
  status: string;
  document_type: string;
}

export interface GraphNodeOut {
  id: string;
  label: string;
  properties: Record<string, string>;
}

export interface LinkedRecord {
  relationship: string;
  node: GraphNodeOut | null;
}

export interface Equipment360 {
  equipment: GraphNodeOut | null;
  linked: LinkedRecord[];
}

export interface GraphStats {
  node_counts: Record<string, number>;
  edge_count: number;
}

export interface CopilotCitation {
  index: number;
  document_id: string;
  chunk_id: string;
  text: string;
}

export interface CopilotAnswer {
  answer: string;
  citations: CopilotCitation[];
}

export interface RCAEvidence {
  tool: string;
  arguments: Record<string, unknown>;
  result_summary: string;
}

export interface RCAResult {
  root_cause_chain: string;
  evidence: RCAEvidence[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocumentOut> {
  const form = new FormData();
  form.append("file", file);
  return request<DocumentOut>("/documents", { method: "POST", body: form });
}

export async function listDocuments(): Promise<DocumentOut[]> {
  return request<DocumentOut[]>("/documents");
}

export async function getEquipment360(tag: string): Promise<Equipment360> {
  return request<Equipment360>(`/graph/equipment/${encodeURIComponent(tag)}`);
}

export async function getGraphStats(): Promise<GraphStats> {
  return request<GraphStats>("/graph/stats");
}

export async function askCopilot(question: string): Promise<CopilotAnswer> {
  return request<CopilotAnswer>("/copilot/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export async function investigateRCA(description: string): Promise<RCAResult> {
  return request<RCAResult>("/rca/investigate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description }),
  });
}
