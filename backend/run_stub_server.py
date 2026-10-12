"""
run_stub_server.py — TEST-ONLY. Starts the real FastAPI app with exactly one
thing replaced: issue_service.analyze_legal_issue, the function that needs a
live Groq key + Chroma indices. Everything this feature actually adds —
auth, JWT, bcrypt, the anonymous-allowance cookie, ownership filtering,
raw-file deletion — runs as real, unmodified production code.

Why this exists: in a sandbox with no LLM key, EVERY analysis fails with 500,
so the anonymous flow's SUCCESS path (cookie issued, allowance recorded,
second attempt rejected) can never be exercised, and "it can't be tested
here" would otherwise be an unverified assumption rather than a finding.

The stub raises LLMConfigError when the query contains TRIGGER_LLM_FAILURE,
so the "a failed attempt must not burn the anonymous allowance" rule can be
tested too. Production code contains no such hook — it lives only here.

NEVER use this to serve real users.
"""

import sys

import uvicorn

from app.main import app  # noqa: F401  (import first so config/sys.path bootstrap runs)
import app.services.issue_service as issue_service
from llm_client import LLMConfigError


def _stub_analyze(query: str) -> dict:
    if "TRIGGER_LLM_FAILURE" in query:
        raise LLMConfigError("stubbed failure for testing")
    return {
        "issue_summary": "Stubbed analysis (test server).",
        "legal_domain": "Property / Rental Dispute",
        "key_facts": ["stub fact"],
        "missing_facts": ["stub missing fact"],
        "relevant_laws": [],
        "relevant_cases": [],
        "supporting_considerations": ["stub supporting"],
        "opposing_considerations": ["stub opposing"],
        "possible_actions_or_remedies": ["stub remedy"],
        "lawyer_specialization": "Property/Rental Dispute Lawyer",
        "disclaimer": "STUB DISCLAIMER — test server only.",
        "_received_query": query,  # lets tests prove what context actually reached the analyzer
    }


issue_service.analyze_legal_issue = _stub_analyze

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
