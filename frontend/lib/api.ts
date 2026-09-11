const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export interface Paragraph {
  id: number;
  idx: number;
  text: string;
}

export interface Reply {
  id: number;
  annotation_id: number;
  author_name: string;
  author_role: string;
  content: string;
  created_at: string;
}

export interface Annotation {
  id: number;
  document_id: number;
  paragraph_id: number;
  start_offset: number;
  end_offset: number;
  quoted_text: string;
  comment: string;
  author_name: string;
  author_role: string;
  status: "open" | "resolved";
  created_at: string;
  replies: Reply[];
}

export interface DocumentListItem {
  id: number;
  filename: string;
  file_type: string;
  created_at: string;
  annotation_count: number;
  open_count: number;
}

export interface DocumentDetail {
  id: number;
  filename: string;
  file_type: string;
  created_at: string;
  paragraphs: Paragraph[];
}

export type AuthorRole = "legal" | "business";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function fetchDocuments(): Promise<DocumentListItem[]> {
  return request("/api/documents/");
}

export function uploadDocument(file: File): Promise<DocumentDetail> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/documents/", { method: "POST", body: form });
}

export function fetchDocument(id: number): Promise<DocumentDetail> {
  return request(`/api/documents/${id}`);
}

export function fetchAnnotations(documentId: number): Promise<Annotation[]> {
  return request(`/api/documents/${documentId}/annotations`);
}

export interface AnnotationPayload {
  paragraph_id: number;
  start_offset: number;
  end_offset: number;
  comment: string;
  author_name: string;
  author_role: AuthorRole;
}

export function createAnnotation(
  documentId: number,
  payload: AnnotationPayload
): Promise<Annotation> {
  return request(`/api/documents/${documentId}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateAnnotationStatus(
  annotationId: number,
  status: "open" | "resolved"
): Promise<Annotation> {
  return request(`/api/annotations/${annotationId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export function deleteAnnotation(annotationId: number): Promise<void> {
  return request(`/api/annotations/${annotationId}`, { method: "DELETE" });
}

export interface ReplyPayload {
  author_name: string;
  author_role: AuthorRole;
  content: string;
}

export function createReply(
  annotationId: number,
  payload: ReplyPayload
): Promise<Reply> {
  return request(`/api/annotations/${annotationId}/replies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
