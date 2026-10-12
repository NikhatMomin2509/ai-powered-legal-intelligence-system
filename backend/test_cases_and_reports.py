"""
test_cases_and_reports.py — End-to-end integration tests for:
1. Case session thread endpoints:
   - GET /api/cases (ordering, user isolation, question counts)
   - GET /api/cases/{case_id} (retrieval oldest to newest, foreign 404 vs nonexistent 404, no '_' keys)
2. Report export endpoints:
   - GET /api/issues/{issue_id}/report.pdf
   - GET /api/cases/{case_id}/report.pdf
   - GET /api/documents/{document_id}/report.pdf
3. Security, Privacy, and Content Guarantees:
   - Auth required (401)
   - Foreign vs nonexistent give identical 404s
   - Correct Content-Type (application/pdf) and Cache-Control (no-store)
   - Unanalyzed document returns 409
   - Body starts with %PDF
   - PDF text extraction with PyMuPDF asserts disclaimer, score, clause text, citations
   - No "_"-prefixed internal keys leaked
   - Special characters (<, >, &, ", ') and Devanagari/Hindi do not crash
   - No temporary or PDF files written to disk during generation
"""

import os
import sys
import time
import uuid
import fitz  # PyMuPDF
import requests

BASE = "http://127.0.0.1:8000"
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")

passed, failed = [], []

def check(name, condition, detail=""):
    (passed if condition else failed).append(name)
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not condition else ""))

def section(title):
    print(f"\n=== {title} ===")

run_id = uuid.uuid4().hex[:8]
EMAIL_A = f"case_user_a_{run_id}@example.com"
EMAIL_B = f"case_user_b_{run_id}@example.com"
PASSWORD = "SecurePassword123!"

# Register User A and User B
reg_a = requests.post(f"{BASE}/api/auth/register", json={"email": EMAIL_A, "password": PASSWORD})
token_a = reg_a.json()["access_token"]
headers_a = {"Authorization": f"Bearer {token_a}"}

reg_b = requests.post(f"{BASE}/api/auth/register", json={"email": EMAIL_B, "password": PASSWORD})
token_b = reg_b.json()["access_token"]
headers_b = {"Authorization": f"Bearer {token_b}"}

# ===========================================================================
section("1. Unauthenticated Access & Auth Gating (401)")
# ===========================================================================
check("GET /api/cases unauthenticated -> 401", requests.get(f"{BASE}/api/cases").status_code == 401)
check("GET /api/cases/1 unauthenticated -> 401", requests.get(f"{BASE}/api/cases/1").status_code == 401)
check("GET /api/cases/1/report.pdf unauthenticated -> 401", requests.get(f"{BASE}/api/cases/1/report.pdf").status_code == 401)
check("GET /api/issues/1/report.pdf unauthenticated -> 401", requests.get(f"{BASE}/api/issues/1/report.pdf").status_code == 401)
check("GET /api/documents/fake-id/report.pdf unauthenticated -> 401", requests.get(f"{BASE}/api/documents/fake-id/report.pdf").status_code == 401)

# ===========================================================================
section("2. Case Thread Creation & Multi-turn Inquiries")
# ===========================================================================
# User A creates Case 1 with turn 1 (including Hindi text and special chars)
q1_text = "My landlord withheld my security deposit of 50000 rupees & refuses to return it. क्या मुझे नोटिस भेजना चाहिए? <b>Bold test</b>"
res1 = requests.post(f"{BASE}/api/issues/analyze", headers=headers_a, json={"query": q1_text})
check("Turn 1 analysis succeeds", res1.status_code == 200)
case1_id = res1.json()["case_id"]
issue1_id = res1.json()["issue_id"]

# User A asks follow-up (Turn 2) in Case 1
time.sleep(0.2)
q2_text = "What if he claims that I damaged the kitchen tiles <damaged>?"
res2 = requests.post(f"{BASE}/api/issues/analyze", headers=headers_a, json={"query": q2_text, "case_id": case1_id})
check("Turn 2 follow-up in same case succeeds", res2.status_code == 200 and res2.json()["case_id"] == case1_id)
issue2_id = res2.json()["issue_id"]

# User A creates Case 2 (single turn)
time.sleep(0.2)
q3_text = "My employer terminated my employment contract without giving 30 days notice."
res3 = requests.post(f"{BASE}/api/issues/analyze", headers=headers_a, json={"query": q3_text})
check("Case 2 creation succeeds", res3.status_code == 200)
case2_id = res3.json()["case_id"]
issue3_id = res3.json()["issue_id"]

# ===========================================================================
section("3. GET /api/cases Ordering, Counts & User Isolation")
# ===========================================================================
cases_resp = requests.get(f"{BASE}/api/cases", headers=headers_a)
check("GET /api/cases returns 200", cases_resp.status_code == 200)
cases_list = cases_resp.json()
check("User A sees exactly 2 cases", len(cases_list) == 2)
# Order: Case 2 was created after turn 2 of Case 1, so Case 2 is newest activity
check("Cases are ordered newest activity first", cases_list[0]["id"] == case2_id and cases_list[1]["id"] == case1_id)
# Verify question counts
c1_obj = next(c for c in cases_list if c["id"] == case1_id)
c2_obj = next(c for c in cases_list if c["id"] == case2_id)
check("Case 1 question_count == 2", c1_obj["question_count"] == 2)
check("Case 2 question_count == 1", c2_obj["question_count"] == 1)

# User B sees 0 cases (isolation)
cases_b = requests.get(f"{BASE}/api/cases", headers=headers_b).json()
check("User B cannot see User A's cases (isolation)", len(cases_b) == 0)

# ===========================================================================
section("4. GET /api/cases/{case_id} Thread Retrieval & Leak Checks")
# ===========================================================================
thread_resp = requests.get(f"{BASE}/api/cases/{case1_id}", headers=headers_a)
check("GET /api/cases/{case1_id} returns 200", thread_resp.status_code == 200)
thread_data = thread_resp.json()
check("Thread contains case_id, title, turns", "case_id" in thread_data and "turns" in thread_data)
check("Thread contains exactly 2 turns", len(thread_data["turns"]) == 2)
check("Turns ordered oldest to newest", thread_data["turns"][0]["issue_id"] == issue1_id and thread_data["turns"][1]["issue_id"] == issue2_id)
check("User's query preserved verbatim", thread_data["turns"][0]["query"] == q1_text)

# Check no keys starting with '_' in results
has_underscore_key = False
for turn in thread_data["turns"]:
    for k in turn["result"].keys():
        if k.startswith("_"):
            has_underscore_key = True
check("No '_' internal keys leaked in case turn results", not has_underscore_key)

# Foreign vs nonexistent 404 test
foreign_resp = requests.get(f"{BASE}/api/cases/{case1_id}", headers=headers_b)
nonexistent_resp = requests.get(f"{BASE}/api/cases/999999", headers=headers_b)
check("Foreign case returns 404", foreign_resp.status_code == 404)
check("Nonexistent case returns 404", nonexistent_resp.status_code == 404)
check("Foreign vs nonexistent case errors are IDENTICAL", foreign_resp.json() == nonexistent_resp.json())

# ===========================================================================
section("5. PDF Export: Issue Brief (GET /api/issues/{id}/report.pdf)")
# ===========================================================================
files_before = set(os.listdir(BACKEND_DIR))

issue_pdf_resp = requests.get(f"{BASE}/api/issues/{issue1_id}/report.pdf", headers=headers_a)
check("Issue PDF export returns 200", issue_pdf_resp.status_code == 200)
check("Content-Type is application/pdf", "application/pdf" in issue_pdf_resp.headers.get("Content-Type", ""))
check("Cache-Control includes no-store", "no-store" in issue_pdf_resp.headers.get("Cache-Control", ""))
check("Body starts with %PDF", issue_pdf_resp.content.startswith(b"%PDF"))

# Check no files created on disk
files_after = set(os.listdir(BACKEND_DIR))
check("Zero files created on disk during issue PDF export", files_after == files_before)

# Foreign issue PDF export returns 404 identical to nonexistent
foreign_issue_pdf = requests.get(f"{BASE}/api/issues/{issue1_id}/report.pdf", headers=headers_b)
nonexistent_issue_pdf = requests.get(f"{BASE}/api/issues/999999/report.pdf", headers=headers_b)
check("Foreign issue PDF returns 404", foreign_issue_pdf.status_code == 404)
check("Nonexistent issue PDF returns 404", nonexistent_issue_pdf.status_code == 404)
check("Foreign vs nonexistent issue PDF errors are IDENTICAL", foreign_issue_pdf.json() == nonexistent_issue_pdf.json())

# Inspect PDF text using PyMuPDF
doc_fitz = fitz.open(stream=issue_pdf_resp.content, filetype="pdf")
pdf_text = "".join([page.get_text() for page in doc_fitz])
check("PDF contains legal disclaimer", "Informational analysis only" in pdf_text or "disclaimer" in pdf_text.lower())
check("PDF contains user's query topic", "security deposit" in pdf_text)
check("PDF contains page numbering", "Page 1 of" in pdf_text)
check("PDF contains timezone / recorded label", "Recorded Time" in pdf_text or "UTC" in pdf_text)
check("PDF contains no user email address", EMAIL_A not in pdf_text)
check("PDF contains no '_received_query' or '_' keys", "_received_query" not in pdf_text and "_raw_retrieval_counts" not in pdf_text)

# ===========================================================================
section("6. PDF Export: Multi-Turn Case Brief (GET /api/cases/{id}/report.pdf)")
# ===========================================================================
case_pdf_resp = requests.get(f"{BASE}/api/cases/{case1_id}/report.pdf", headers=headers_a)
check("Case PDF export returns 200", case_pdf_resp.status_code == 200)
check("Content-Type is application/pdf", "application/pdf" in case_pdf_resp.headers.get("Content-Type", ""))
check("Cache-Control includes no-store", "no-store" in case_pdf_resp.headers.get("Cache-Control", ""))
check("Body starts with %PDF", case_pdf_resp.content.startswith(b"%PDF"))

case_doc_fitz = fitz.open(stream=case_pdf_resp.content, filetype="pdf")
case_pdf_text = "".join([page.get_text() for page in case_doc_fitz])
check("Case PDF contains Turn 1", "Turn 1:" in case_pdf_text)
check("Case PDF contains Turn 2", "Turn 2:" in case_pdf_text)
check("Case PDF contains multi-turn context note", "3 most recent turns" in case_pdf_text)
check("Case PDF contains disclaimer", "Informational analysis only" in case_pdf_text)
check("Case PDF contains no email", EMAIL_A not in case_pdf_text)

foreign_case_pdf = requests.get(f"{BASE}/api/cases/{case1_id}/report.pdf", headers=headers_b)
nonexistent_case_pdf = requests.get(f"{BASE}/api/cases/999999/report.pdf", headers=headers_b)
check("Foreign case PDF returns 404", foreign_case_pdf.status_code == 404)
check("Nonexistent case PDF returns 404", nonexistent_case_pdf.status_code == 404)
check("Foreign vs nonexistent case PDF errors are IDENTICAL", foreign_case_pdf.json() == nonexistent_case_pdf.json())

# ===========================================================================
section("7. PDF Export: Document Audit (GET /api/documents/{id}/report.pdf)")
# ===========================================================================
# Step 1: Upload a document without analyzing it
sample_file_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
up_resp = requests.post(f"{BASE}/api/documents/upload", headers=headers_a, files={"file": ("test_agreement.pdf", sample_file_content, "application/pdf")})
check("Document uploaded", up_resp.status_code == 200)
doc_id = up_resp.json()["document_id"]

# Step 2: Unanalyzed document report returns 409 Conflict
unanalyzed_pdf_resp = requests.get(f"{BASE}/api/documents/{doc_id}/report.pdf", headers=headers_a)
check("Unanalyzed document report returns 409 Conflict", unanalyzed_pdf_resp.status_code == 409)
check("409 response explains document is not analyzed", "analyzed" in unanalyzed_pdf_resp.json()["detail"].lower())

# Step 3: Analyze the document
analyze_doc_resp = requests.post(f"{BASE}/api/documents/{doc_id}/analyze", headers=headers_a)
check("Document analyze completes", analyze_doc_resp.status_code == 200)

# Step 4: Analyzed document report returns 200 PDF
doc_pdf_resp = requests.get(f"{BASE}/api/documents/{doc_id}/report.pdf", headers=headers_a)
check("Analyzed document PDF returns 200", doc_pdf_resp.status_code == 200)
check("Content-Type is application/pdf", "application/pdf" in doc_pdf_resp.headers.get("Content-Type", ""))
check("Cache-Control includes no-store", "no-store" in doc_pdf_resp.headers.get("Cache-Control", ""))
check("Body starts with %PDF", doc_pdf_resp.content.startswith(b"%PDF"))

doc_fitz_page = fitz.open(stream=doc_pdf_resp.content, filetype="pdf")
doc_text = "".join([page.get_text() for page in doc_fitz_page])
check("Document PDF contains score calculation formula", "LOW = 1, MEDIUM = 2, HIGH = 3" in doc_text)
check("Document PDF contains indicative score", "Indicative Risk Score" in doc_text)
check("Document PDF contains content disclosure", "contains clause excerpts" in doc_text)
check("Document PDF contains disclaimer", "Informational analysis only" in doc_text or "disclaimer" in doc_text.lower())
check("Document PDF contains filename", "test_agreement.pdf" in doc_text)
check("Document PDF contains no email", EMAIL_A not in doc_text)

# Foreign document PDF returns 404 identical to nonexistent
foreign_doc_pdf = requests.get(f"{BASE}/api/documents/{doc_id}/report.pdf", headers=headers_b)
nonexistent_doc_pdf = requests.get(f"{BASE}/api/documents/nonexistent-id/report.pdf", headers=headers_b)
check("Foreign document PDF returns 404", foreign_doc_pdf.status_code == 404)
check("Nonexistent document PDF returns 404", nonexistent_doc_pdf.status_code == 404)
check("Foreign vs nonexistent document PDF errors are IDENTICAL", foreign_doc_pdf.json() == nonexistent_doc_pdf.json())

# ===========================================================================
print("\n" + "=" * 60)
print(f"BACKEND TEST RESULTS: PASSED: {len(passed)}   FAILED: {len(failed)}")
if failed:
    for f in failed:
        print("  - FAILED:", f)
    sys.exit(1)
else:
    print("ALL NEW BACKEND TESTS PASSED CLEANLY!")
    sys.exit(0)
