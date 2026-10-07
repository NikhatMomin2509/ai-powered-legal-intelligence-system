/**
 * Small, deliberate normalization layer. The backend is frozen, and it has
 * two real inconsistencies worth absorbing in exactly one place rather than
 * re-checking in every component:
 *
 * 1. GET /api/issues (list) uses "issue_type"; GET /api/issues/{id} and the
 *    raw POST /api/issues/analyze response use "legal_domain" for the same
 *    concept. getIssueDomain() reads whichever is present.
 *
 * 2. Clause-level risk_level inside a document's risky_clauses is UPPERCASE
 *    ("HIGH"); the document-level risk_level is Title Case ("High").
 *    normalizeRiskLevel() upper-cases either into one of LOW/MEDIUM/HIGH so
 *    color/label lookups never miss a case.
 */

export function getIssueDomain(issue) {
  return issue?.legal_domain || issue?.issue_type || "Uncategorized";
}

export function normalizeRiskLevel(level) {
  const upper = (level || "").toString().toUpperCase();
  if (upper === "HIGH" || upper === "MEDIUM" || upper === "LOW") return upper;
  return "UNKNOWN";
}

export const RISK_LEVEL_LABEL = {
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
  UNKNOWN: "Unknown",
};
