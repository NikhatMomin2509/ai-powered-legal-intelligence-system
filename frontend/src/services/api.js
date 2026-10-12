import axios from "axios";

/**
 * Default API host follows the PAGE'S OWN hostname instead of a hard-coded
 * 127.0.0.1. This matters for privacy, not just convenience: the one-time
 * anonymous-analysis limit is tracked with a SameSite=Lax cookie set by the
 * backend, and browsers treat "localhost" and "127.0.0.1" as DIFFERENT sites.
 * A page on localhost:5173 calling 127.0.0.1:8000 is a cross-site request, on
 * which Lax cookies are not sent — the limit would silently stop working.
 * Same hostname + different port is same-site, so the cookie flows.
 * Set VITE_API_BASE_URL only if the API really lives on another host.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `http://${window.location.hostname}:8000`;

export const TOKEN_KEY = "legal_ai_token";

// The JWT lives in localStorage. Known trade-off (documented in the README):
// any script running on this origin could read it (XSS). An httpOnly-cookie
// token would resist that but needs CSRF protection and more infrastructure
// than this project's scope calls for. Only the token is stored — never the
// password, and never any API key.
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // generous — real RAG + LLM calls can genuinely take a while
  // Required for the browser to send/accept the backend's httpOnly anonymous
  // session cookie on these cross-origin (different port) requests.
  withCredentials: true,
});

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * Normalizes any axios error into a plain, user-safe message. Never surfaces
 * raw Python tracebacks or response bodies — only ever the backend's own
 * {detail: "..."} string when present (every FastAPI HTTPException in this
 * backend returns exactly that shape), or a generic fallback otherwise.
 */
async function extractErrorMessage(error) {
  if (error.code === "ECONNABORTED") {
    return "The request took too long to respond. The analysis may still be processing — try again in a moment.";
  }
  if (!error.response) {
    return "Could not reach the server. Confirm the backend is running at " + API_BASE_URL + ".";
  }
  let data = error.response.data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      data = JSON.parse(text);
    } catch {
      // not JSON
    }
  }
  const { status } = error.response;
  const detail = data && typeof data === "object" ? data.detail : null;
  if (typeof detail === "string") return detail;

  // FastAPI/Pydantic validation errors (422) arrive as an ARRAY of {msg, ...}.
  if (status === 422 && Array.isArray(detail) && detail[0]?.msg) {
    return String(detail[0].msg).replace(/^Value error,\s*/i, "");
  }
  if (status === 404) return "The requested item could not be found.";
  if (status === 409) return typeof detail === "string" ? detail : "The document analysis is incomplete or in conflict.";
  if (status === 422) return "The request was invalid. Check the input and try again.";
  if (status >= 500) return "Something went wrong on the server. Please try again.";
  return "An unexpected error occurred.";
}

async function request(config) {
  const hadToken = Boolean(getToken());
  try {
    const response = await client.request(config);
    return response.data;
  } catch (error) {
    const message = await extractErrorMessage(error);
    const wrapped = new Error(message);
    wrapped.status = error.response?.status;
    // A 401 on a request that CARRIED a token means the session is no longer
    // valid (expired / signature no longer matches). Tell the auth layer so it
    // can sign the user out cleanly. Login 401s are just bad credentials and
    // must not trigger this.
    const isLogin = typeof config.url === "string" && config.url.startsWith("/api/auth/login");
    if (wrapped.status === 401 && hadToken && !isLogin) {
      window.dispatchEvent(new Event("auth:expired"));
    }
    throw wrapped;
  }
}

// ---------- Auth ----------

export function registerAccount(email, password) {
  return request({ method: "POST", url: "/api/auth/register", data: { email, password } });
}

export function loginAccount(email, password) {
  return request({ method: "POST", url: "/api/auth/login", data: { email, password } });
}

export function getMe() {
  return request({ method: "GET", url: "/api/auth/me" });
}

// ---------- Cases & Issues ----------

export function listCases() {
  return request({ method: "GET", url: "/api/cases" });
}

export function getCase(caseId) {
  return request({ method: "GET", url: `/api/cases/${caseId}` });
}

/** caseId (optional) continues an existing case — authenticated users only. */
export function analyzeIssue(query, caseId = null) {
  const data = { query };
  if (caseId != null) data.case_id = caseId;
  return request({ method: "POST", url: "/api/issues/analyze", data });
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

// ---------- PDF Exports ----------

export async function downloadPdfBlob(url, filename) {
  const token = getToken();
  try {
    const response = await client.get(url, {
      responseType: "blob",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = blobUrl;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Revoke object URL after brief delay to ensure browser began download
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
  } catch (error) {
    const message = await extractErrorMessage(error);
    const wrapped = new Error(message);
    wrapped.status = error.response?.status;
    throw wrapped;
  }
}

export function exportIssueReport(issueId) {
  const dateStr = new Date().toISOString().slice(0, 10);
  const filename = `legal_issue_${issueId}_${dateStr}.pdf`;
  return downloadPdfBlob(`/api/issues/${issueId}/report.pdf`, filename);
}

export function exportCaseReport(caseId) {
  const dateStr = new Date().toISOString().slice(0, 10);
  const filename = `legal_case_${caseId}_${dateStr}.pdf`;
  return downloadPdfBlob(`/api/cases/${caseId}/report.pdf`, filename);
}

export function exportDocumentReport(documentId) {
  const dateStr = new Date().toISOString().slice(0, 10);
  const sanitizedId = String(documentId).slice(0, 8);
  const filename = `document_audit_${sanitizedId}_${dateStr}.pdf`;
  return downloadPdfBlob(`/api/documents/${documentId}/report.pdf`, filename);
}

export { API_BASE_URL };
