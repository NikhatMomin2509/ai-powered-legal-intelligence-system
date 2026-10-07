import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // generous — real RAG + LLM calls can genuinely take a while
});

/**
 * Normalizes any axios error into a plain, user-safe message. Never surfaces
 * raw Python tracebacks or response bodies — only ever the backend's own
 * {detail: "..."} string when present (every FastAPI HTTPException in this
 * backend returns exactly that shape), or a generic fallback otherwise.
 */
function normalizeError(error) {
  if (error.code === "ECONNABORTED") {
    return "The request took too long to respond. The analysis may still be processing — try again in a moment.";
  }
  if (!error.response) {
    return "Could not reach the server. Confirm the backend is running at " + API_BASE_URL + ".";
  }
  const { status, data } = error.response;
  const detail = data && typeof data === "object" && typeof data.detail === "string" ? data.detail : null;
  if (detail) return detail;
  if (status === 404) return "The requested item could not be found.";
  if (status === 422) return "The request was invalid. Check the input and try again.";
  if (status >= 500) return "Something went wrong on the server. Please try again.";
  return "An unexpected error occurred.";
}

async function request(config) {
  try {
    const response = await client.request(config);
    return response.data;
  } catch (error) {
    const message = normalizeError(error);
    const wrapped = new Error(message);
    wrapped.status = error.response?.status;
    throw wrapped;
  }
}

// ---------- Issues ----------

export function analyzeIssue(query) {
  return request({ method: "POST", url: "/api/issues/analyze", data: { query } });
}

export function listIssues() {
  return request({ method: "GET", url: "/api/issues" });
}

export function getIssue(issueId) {
  return request({ method: "GET", url: `/api/issues/${issueId}` });
}

// ---------- Documents ----------

export function uploadDocument(file, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);
  return request({
    method: "POST",
    url: "/api/documents/upload",
    data: formData,
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
}

export function analyzeDocument(documentId) {
  return request({ method: "POST", url: `/api/documents/${documentId}/analyze` });
}

export function listDocuments() {
  return request({ method: "GET", url: "/api/documents" });
}

export function getDocument(documentId) {
  return request({ method: "GET", url: `/api/documents/${documentId}` });
}

export { API_BASE_URL };
