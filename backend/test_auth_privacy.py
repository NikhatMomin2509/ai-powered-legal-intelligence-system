"""
test_auth_privacy.py — end-to-end security/privacy tests against a RUNNING
backend (http://127.0.0.1:8000). Not a unit test suite — it deliberately
hits the real HTTP API and inspects the real database file, because the
properties being verified (ownership isolation, no plaintext passwords,
raw-file deletion, anonymous allowance) only mean something against the
real running system.

Run with the backend up:   python test_auth_privacy.py
"""

import json
import os
import sqlite3
import sys
import time
import uuid

import requests

BASE = "http://127.0.0.1:8000"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legal_ai.db")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
SAMPLE_PDF = os.environ.get(
    "SAMPLE_PDF",
    r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf"
    if os.path.exists(r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf")
    else "/tmp/test_rental_agreement.pdf"
)

passed, failed = [], []


def check(name, condition, detail=""):
    (passed if condition else failed).append(name)
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not condition else ""))


def section(title):
    print(f"\n=== {title} ===")


run_id = uuid.uuid4().hex[:8]
EMAIL_A = f"usera_{run_id}@example.com"
EMAIL_B = f"userb_{run_id}@example.com"
PASSWORD = "CorrectHorse9!"

# ---------------------------------------------------------------------------
section("TEST 1/2 — Anonymous issue query: allowance enforced server-side")
# Requires the stub server (run_stub_server.py): it replaces ONLY the analyzer
# function, so the real anonymous-cookie / usage-tracking / persistence code runs.
MARKER = f"ANONMARKER{run_id}"
ISSUES_URL = f"{BASE}/api/issues/analyze"
q = {"query": f"My landlord is refusing to return my security deposit {MARKER} even though I left the apartment in good condition."}


def db_ids(table="issues"):
    conn = sqlite3.connect(DB_PATH)
    ids = {r[0] for r in conn.execute(f"SELECT id FROM {table}")}
    conn.close()
    return ids


def usage_rows():
    return len(db_ids("anonymous_usage"))


def db_contains(marker: str) -> bool:
    """Raw byte search of the SQLite file (and WAL if present) — far stronger
    evidence than a LIKE on one table: it finds the text in ANY table/column,
    including free pages and indexes."""
    data = open(DB_PATH, "rb").read()
    for suffix in ("-wal", "-journal"):
        if os.path.exists(DB_PATH + suffix):
            data += open(DB_PATH + suffix, "rb").read()
    return marker.encode() in data


issues_before, usage_before = db_ids(), usage_rows()

# (a) a FAILED anonymous attempt must NOT burn the one-time allowance
sess = requests.Session()  # a Session keeps cookies exactly like a browser
rf = sess.post(ISSUES_URL, json={"query": "TRIGGER_LLM_FAILURE please analyze this failing legal query"})
check("failed anonymous attempt -> 500 with a safe JSON message", rf.status_code == 500 and "detail" in rf.json())
check("failed attempt did NOT record a usage row (allowance not burned)", usage_rows() == usage_before)

# (b) the first successful anonymous analysis
r1 = sess.post(ISSUES_URL, json=q)
check("first anonymous analysis -> 200 with a real result", r1.status_code == 200 and bool(r1.json().get("issue_summary")),
      f"got {r1.status_code}: {r1.text[:150]}")
set_cookie = r1.headers.get("set-cookie", "")
check("server issued the anon_session_id cookie", "anon_session_id=" in set_cookie)
check("cookie is HttpOnly (page JavaScript cannot read or clear it)", "httponly" in set_cookie.lower())
check("cookie is SameSite=Lax", "samesite=lax" in set_cookie.lower())
check("cookie has a long Max-Age (limit is 'one ever', not 'one per day')", "max-age=" in set_cookie.lower())
check("exactly one usage row recorded for it", usage_rows() == usage_before + 1)

# (c) the SECOND attempt — and a third, simulating a page refresh (cookie persists)
r2 = sess.post(ISSUES_URL, json=q)
check("SECOND anonymous attempt (same browser) -> 401 authentication required", r2.status_code == 401, f"got {r2.status_code}")
r3 = sess.post(ISSUES_URL, json={"query": "a completely different second legal question please answer"})
check("a DIFFERENT second question is also rejected (limit is per browser, not per query text)", r3.status_code == 401)
check("401 body is clean JSON with a safe, user-readable message",
      r2.headers.get("content-type", "").startswith("application/json") and "log in" in r2.json().get("detail", "").lower())
check("401 response does not re-issue/rotate the cookie (no bypass via a fresh one)",
      "anon_session_id=" not in r2.headers.get("set-cookie", ""))

# (d) a genuinely different browser has its own allowance
check("a DIFFERENT browser still gets its own one-time allowance",
      requests.Session().post(ISSUES_URL, json={"query": "separate browser asking about a deposit dispute"}).status_code == 200)

# (e) known, documented limitation — recorded as INFO, not asserted as a guarantee
forged = requests.post(ISSUES_URL, json={"query": "forged cookie value asking about a tenancy dispute"},
                       cookies={"anon_session_id": "forged-" + uuid.uuid4().hex})
print(f"  [INFO] a client that mints its own cookie value is treated as a new browser (status {forged.status_code}) "
      "-- documented limitation: the anonymous limit is a soft, per-browser control, not an abuse-proof one")

# (f) nothing about the anonymous query was stored anywhere
check("anonymous query text appears NOWHERE in the database file (raw byte search)", not db_contains(MARKER))
new_issue_rows = db_ids() - issues_before
check("anonymous requests added ZERO rows to the issues table", len(new_issue_rows) == 0, f"new ids: {new_issue_rows}")
conn = sqlite3.connect(DB_PATH)
cols = [c[1] for c in conn.execute("PRAGMA table_info(anonymous_usage)")]
conn.close()
check("anonymous_usage has no column that could hold query text or an IP",
      not any(c in cols for c in ("query", "text", "content", "ip", "ip_address")), f"columns: {cols}")

SERVER_LOG = os.environ.get("SERVER_LOG")
if SERVER_LOG and os.path.exists(SERVER_LOG):
    check("anonymous query text appears nowhere in the server log", MARKER not in open(SERVER_LOG, errors="ignore").read())

# ---------------------------------------------------------------------------
section("TEST 3 — Anonymous document access is blocked")
for label, req in [
    ("upload", lambda: requests.post(f"{BASE}/api/documents/upload", files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")})),
    ("list", lambda: requests.get(f"{BASE}/api/documents")),
    ("get", lambda: requests.get(f"{BASE}/api/documents/some-id")),
    ("analyze", lambda: requests.post(f"{BASE}/api/documents/some-id/analyze")),
]:
    r = req()
    check(f"anonymous document {label} -> 401", r.status_code == 401, f"got {r.status_code}")

for label, req in [
    ("GET /api/issues", lambda: requests.get(f"{BASE}/api/issues")),
    ("GET /api/issues/1", lambda: requests.get(f"{BASE}/api/issues/1")),
]:
    r = req()
    check(f"anonymous {label} -> 401", r.status_code == 401, f"got {r.status_code}")

check("GET /api/health stays public", requests.get(f"{BASE}/api/health").status_code == 200)

# ---------------------------------------------------------------------------
section("TEST 4 — Register: account created, password stored ONLY as a hash")
reg = requests.post(f"{BASE}/api/auth/register", json={"email": EMAIL_A, "password": PASSWORD})
check("register user A -> 200", reg.status_code == 200, reg.text[:200])
body = reg.json() if reg.status_code == 200 else {}
check("register response includes an access token", bool(body.get("access_token")))
check("register response never includes password or hash",
      "password" not in json.dumps(body).lower() or "password_hash" not in body.get("user", {}))
check("register response user has no password_hash field", "password_hash" not in body.get("user", {}))

conn = sqlite3.connect(DB_PATH)
row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (EMAIL_A,)).fetchone()
conn.close()
check("password_hash is stored in the database", row is not None and bool(row[0]))
check("stored value is NOT the plaintext password", row is not None and row[0] != PASSWORD)
check("stored value is a bcrypt hash ($2b$ prefix)", row is not None and row[0].startswith("$2"))
check("plaintext password appears nowhere in the users table",
      PASSWORD not in json.dumps(sqlite3.connect(DB_PATH).execute("SELECT * FROM users").fetchall(), default=str))

dup = requests.post(f"{BASE}/api/auth/register", json={"email": EMAIL_A, "password": PASSWORD})
check("duplicate email registration -> 409", dup.status_code == 409, f"got {dup.status_code}")
check("short password rejected -> 422", requests.post(f"{BASE}/api/auth/register",
      json={"email": f"x_{run_id}@example.com", "password": "short"}).status_code == 422)
check("invalid email rejected -> 422", requests.post(f"{BASE}/api/auth/register",
      json={"email": "not-an-email", "password": PASSWORD}).status_code == 422)

# ---------------------------------------------------------------------------
section("TEST 5 — Login")
login = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL_A, "password": PASSWORD})
check("login with correct credentials -> 200", login.status_code == 200)
TOKEN_A = login.json().get("access_token") if login.status_code == 200 else None
check("login returns a token", bool(TOKEN_A))

bad_pw = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL_A, "password": "WrongPassword1"})
bad_user = requests.post(f"{BASE}/api/auth/login", json={"email": f"nobody_{run_id}@example.com", "password": PASSWORD})
check("wrong password -> 401", bad_pw.status_code == 401)
check("unknown email -> 401", bad_user.status_code == 401)
check("wrong-password and unknown-email errors are IDENTICAL (no email enumeration)",
      bad_pw.json() == bad_user.json(), f"{bad_pw.json()} vs {bad_user.json()}")

HA = {"Authorization": f"Bearer {TOKEN_A}"}
me = requests.get(f"{BASE}/api/auth/me", headers=HA)
check("GET /api/auth/me with valid token -> 200", me.status_code == 200)
check("/me returns the right email and no hash", me.json().get("email") == EMAIL_A and "password_hash" not in me.json())
check("GET /api/auth/me with no token -> 401", requests.get(f"{BASE}/api/auth/me").status_code == 401)
check("GET /api/auth/me with garbage token -> 401",
      requests.get(f"{BASE}/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"}).status_code == 401)
tampered = (TOKEN_A[:-4] + ("AAAA" if not TOKEN_A.endswith("AAAA") else "BBBB")) if TOKEN_A else "x"
check("GET /api/auth/me with a TAMPERED token (bad signature) -> 401",
      requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401)

# ---------------------------------------------------------------------------
section("TEST 6 — Authenticated upload: owned by user, raw file deleted after processing")
if not os.path.exists(SAMPLE_PDF):
    print(f"  (sample PDF missing at {SAMPLE_PDF} — skipping document tests)")
    DOC_A = None
else:
    with open(SAMPLE_PDF, "rb") as f:
        up = requests.post(f"{BASE}/api/documents/upload", headers=HA, files={"file": ("rental.pdf", f, "application/pdf")})
    check("authenticated upload -> 200", up.status_code == 200, up.text[:200])
    DOC_A = up.json().get("document_id") if up.status_code == 200 else None

    conn = sqlite3.connect(DB_PATH)
    owner = conn.execute("SELECT user_id FROM documents WHERE document_id = ?", (DOC_A,)).fetchone()
    uid_a = conn.execute("SELECT id FROM users WHERE email = ?", (EMAIL_A,)).fetchone()
    conn.close()
    check("uploaded document is associated with user A", owner is not None and uid_a is not None and owner[0] == uid_a[0])

    raw_before = [f for f in os.listdir(UPLOADS_DIR) if f.startswith(DOC_A)] if os.path.isdir(UPLOADS_DIR) else []
    check("raw file exists on disk BEFORE analysis (temporary storage)", len(raw_before) == 1, f"found {raw_before}")

    an = requests.post(f"{BASE}/api/documents/{DOC_A}/analyze", headers=HA)
    check("analyze runs for the owner (200, or a safe 500 if LLM unavailable — never 401/403/404)",
          an.status_code in (200, 500), f"got {an.status_code}")

    raw_after = [f for f in os.listdir(UPLOADS_DIR) if f.startswith(DOC_A)] if os.path.isdir(UPLOADS_DIR) else []
    check("RAW FILE DELETED after processing", len(raw_after) == 0, f"still on disk: {raw_after}")

    if an.status_code == 200:
        check("analysis result still retrievable after raw file deletion",
              requests.get(f"{BASE}/api/documents/{DOC_A}", headers=HA).status_code == 200)

# ---------------------------------------------------------------------------
section("TEST 7/8/9 — Isolation: user B cannot see or touch user A's data")
regB = requests.post(f"{BASE}/api/auth/register", json={"email": EMAIL_B, "password": PASSWORD})
TOKEN_B = regB.json().get("access_token")
HB = {"Authorization": f"Bearer {TOKEN_B}"}

if DOC_A:
    r = requests.get(f"{BASE}/api/documents/{DOC_A}", headers=HB)
    check("TEST 8: user B GET user A's document_id -> 404 (not 200)", r.status_code == 404, f"got {r.status_code}")
    check("response body does not leak the document", DOC_A not in r.text or "not found" in r.text.lower())
    r = requests.post(f"{BASE}/api/documents/{DOC_A}/analyze", headers=HB)
    check("user B ANALYZE user A's document_id -> 404", r.status_code == 404, f"got {r.status_code}")
    nonexist = requests.get(f"{BASE}/api/documents/{uuid.uuid4()}", headers=HB)
    check("'someone else's' and 'nonexistent' are indistinguishable (same status + body)",
          r.status_code == nonexist.status_code and
          requests.get(f"{BASE}/api/documents/{DOC_A}", headers=HB).json() == nonexist.json())
    docs_b = requests.get(f"{BASE}/api/documents", headers=HB).json()
    check("TEST 7: user B's document list does NOT contain user A's document",
          all(d["document_id"] != DOC_A for d in docs_b), f"{docs_b}")
    docs_a = requests.get(f"{BASE}/api/documents", headers=HA).json()
    check("user A's own list DOES contain it", any(d["document_id"] == DOC_A for d in docs_a))

# Issues via the REAL authenticated code path (no direct SQL seeding)
AUTHMARKER = f"AUTHMARKER{run_id}"
posts = [requests.post(ISSUES_URL, headers=HA, json={"query": f"{AUTHMARKER} authenticated question number {i} about a deposit"})
         for i in range(3)]
check("authenticated user is NOT subject to the anonymous limit (3 analyses, all 200)",
      all(p.status_code == 200 for p in posts), [p.status_code for p in posts])

issues_a = requests.get(f"{BASE}/api/issues", headers=HA).json()
mine = [i for i in issues_a if AUTHMARKER in i["query"]]
check("all 3 authenticated analyses were saved and appear in user A's history", len(mine) == 3, f"{len(mine)} found")
ISSUE_A = mine[0]["id"] if mine else None
check("POSITIVE CONTROL: authenticated query text IS found by the raw DB byte search "
      "(proves the anonymous 'not stored' check above can actually detect stored text)", db_contains(AUTHMARKER))

conn = sqlite3.connect(DB_PATH)
uid_a = conn.execute("SELECT id FROM users WHERE email = ?", (EMAIL_A,)).fetchone()[0]
owner_ok = conn.execute("SELECT COUNT(*) FROM issues WHERE query LIKE ? AND user_id = ?", (f"%{AUTHMARKER}%", uid_a)).fetchone()[0]
legacy_ids = [r[0] for r in conn.execute("SELECT id FROM issues WHERE user_id IS NULL")]
conn.close()
check("saved rows carry user A's id as owner", owner_ok == 3)

r = requests.get(f"{BASE}/api/issues/{ISSUE_A}", headers=HA)
check("owner A can GET their own issue", r.status_code == 200, f"got {r.status_code}")
r = requests.get(f"{BASE}/api/issues/{ISSUE_A}", headers=HB)
check("TEST 9: user B GET user A's issue_id -> 404", r.status_code == 404, f"got {r.status_code}")
check("404 for a foreign issue is identical to 404 for a nonexistent one",
      r.json() == requests.get(f"{BASE}/api/issues/99999999", headers=HB).json())
issues_b = requests.get(f"{BASE}/api/issues", headers=HB).json()
check("user B's issue list does NOT contain any of user A's issues", all(AUTHMARKER not in i["query"] for i in issues_b))

# Pre-existing rows from before this feature (no owner) must be invisible to everyone
if legacy_ids:
    check(f"pre-existing ownerless rows {legacy_ids} are inaccessible to every user (GET -> 404)",
          all(requests.get(f"{BASE}/api/issues/{i}", headers=h).status_code == 404 for i in legacy_ids for h in (HA, HB)))
    check("ownerless rows never appear in anyone's history",
          all(i["id"] not in legacy_ids for i in issues_a + issues_b))

# ---------------------------------------------------------------------------
section("CASE SESSIONS — authenticated follow-ups (Case 2)")
CASE_MARK = f"CASEONE{run_id}"
c1 = requests.post(ISSUES_URL, headers=HA, json={"query": f"{CASE_MARK} My landlord is refusing to return my security deposit."})
check("first authenticated question -> 200 and returns issue_id + case_id",
      c1.status_code == 200 and "case_id" in c1.json() and "issue_id" in c1.json(), c1.text[:150])
CASE_ID = c1.json().get("case_id")

fu_text = f"FOLLOWUP{run_id} What if he claims that I damaged the apartment?"
c2 = requests.post(ISSUES_URL, headers=HA, json={"query": fu_text, "case_id": CASE_ID})
check("follow-up with case_id -> 200", c2.status_code == 200, c2.text[:150])
check("follow-up stays in the SAME case", c2.json().get("case_id") == CASE_ID)
received = c2.json().get("_received_query", "")
check("EARLIER context actually reached the analyzer (follow-up is answerable)", CASE_MARK in received)
check("the follow-up's own text reached the analyzer too", fu_text in received)

conn = sqlite3.connect(DB_PATH)
stored = conn.execute("SELECT query, case_id, user_id FROM issues WHERE id = ?", (c2.json().get("issue_id"),)).fetchone()
case_row = conn.execute("SELECT user_id FROM cases WHERE id = ?", (CASE_ID,)).fetchone()
conn.close()
check("history stores ONLY what the user typed (not the composite context string)",
      stored is not None and stored[0] == fu_text and "Context from earlier" not in stored[0], stored)
check("follow-up row is linked to the case and owned by user A", stored is not None and stored[1] == CASE_ID and stored[2] == uid_a)
check("the case row is owned by user A", case_row is not None and case_row[0] == uid_a)

# context must be scoped to ONE case — a second case of the same user must not leak in
CASE2_MARK = f"CASETWO{run_id}"
other_case = requests.post(ISSUES_URL, headers=HA, json={"query": f"{CASE2_MARK} an unrelated employment matter"}).json()["case_id"]
c3 = requests.post(ISSUES_URL, headers=HA, json={"query": "another follow-up on the deposit matter", "case_id": CASE_ID})
check("a different case's content does NOT leak into this case's follow-up context",
      CASE2_MARK not in c3.json().get("_received_query", "") and CASE_MARK in c3.json().get("_received_query", ""))
check("the two cases are distinct", other_case != CASE_ID)

# ownership
rb = requests.post(ISSUES_URL, headers=HB, json={"query": "user B trying to follow up on A's case", "case_id": CASE_ID})
rn = requests.post(ISSUES_URL, headers=HB, json={"query": "user B follow up on a nonexistent case", "case_id": 99999999})
check("user B follow-up on user A's case_id -> 404", rb.status_code == 404, f"got {rb.status_code}")
check("'someone else's case' and 'nonexistent case' are indistinguishable", rb.status_code == rn.status_code and rb.json() == rn.json())
conn = sqlite3.connect(DB_PATH)
leak = conn.execute("SELECT COUNT(*) FROM issues WHERE query LIKE ?", ("%user B trying to follow up%",)).fetchone()[0]
conn.close()
check("the rejected foreign follow-up stored nothing", leak == 0)

ra = requests.post(ISSUES_URL, json={"query": "anonymous trying to follow up on a case", "case_id": CASE_ID})
check("anonymous request naming a case_id -> 401 (follow-ups need an account)", ra.status_code == 401, f"got {ra.status_code}")

# failures must not leave debris
conn = sqlite3.connect(DB_PATH)
cases_before = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
issues_cnt_before = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
conn.close()
requests.post(ISSUES_URL, headers=HA, json={"query": "TRIGGER_LLM_FAILURE brand new case that fails"})
requests.post(ISSUES_URL, headers=HA, json={"query": "TRIGGER_LLM_FAILURE follow-up that fails", "case_id": CASE_ID})
conn = sqlite3.connect(DB_PATH)
check("a FAILED analysis creates no empty case and no issue row",
      conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == cases_before and
      conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0] == issues_cnt_before)
conn.close()

hist_a = requests.get(f"{BASE}/api/issues", headers=HA).json()
check("history items expose case_id so the UI can group follow-ups", any(i.get("case_id") == CASE_ID for i in hist_a))
hist_b = requests.get(f"{BASE}/api/issues", headers=HB).json()
check("user B's history contains none of user A's case content",
      all(i.get("case_id") != CASE_ID for i in hist_b))

# ---------------------------------------------------------------------------
section("RAW-FILE RETENTION HYGIENE — uploads that are never analyzed must not linger")
if os.path.exists(SAMPLE_PDF):
    def upload(headers=HA):
        with open(SAMPLE_PDF, "rb") as f:
            return requests.post(f"{BASE}/api/documents/upload", headers=headers, files={"file": ("never_analyzed.pdf", f, "application/pdf")})

    def raw_files(doc_id):
        return [x for x in os.listdir(UPLOADS_DIR) if x.startswith(doc_id)] if os.path.isdir(UPLOADS_DIR) else []

    orphan = upload().json()["document_id"]
    check("an uploaded-but-never-analyzed file exists on disk (the risk being tested)", len(raw_files(orphan)) == 1)
    # age it past the retention window (default 60 min) by backdating its mtime
    for fn in raw_files(orphan):
        old = time.time() - 3 * 3600
        os.utime(os.path.join(UPLOADS_DIR, fn), (old, old))
    fresh = upload().json()["document_id"]  # any upload triggers the purge sweep
    check("the stale never-analyzed raw file was PURGED", len(raw_files(orphan)) == 0, f"still there: {raw_files(orphan)}")
    check("a FRESH upload is NOT purged", len(raw_files(fresh)) == 1)
    conn = sqlite3.connect(DB_PATH)
    st = conn.execute("SELECT status FROM documents WHERE document_id = ?", (orphan,)).fetchone()[0]
    conn.close()
    check("the purged document's record is marked 'expired'", st == "expired", st)
    r = requests.post(f"{BASE}/api/documents/{orphan}/analyze", headers=HA)
    check("analyzing an expired document -> 410 with a clear 'upload again' message (not a crash)",
          r.status_code == 410 and "upload" in r.json().get("detail", "").lower(), f"{r.status_code} {r.text[:120]}")
    check("user B still gets 404 (not 410) for A's expired document — no status leak",
          requests.post(f"{BASE}/api/documents/{orphan}/analyze", headers=HB).status_code == 404)

    first = requests.post(f"{BASE}/api/documents/{fresh}/analyze", headers=HA)
    check("normal analyze of the fresh upload -> 200", first.status_code == 200, first.text[:120])
    check("its raw file is deleted", len(raw_files(fresh)) == 0)
    again = requests.post(f"{BASE}/api/documents/{fresh}/analyze", headers=HA)
    check("analyzing the SAME document again -> 200 with the saved result (idempotent, no missing-file crash)",
          again.status_code == 200 and again.json() == first.json())
    conn = sqlite3.connect(DB_PATH)
    prev = conn.execute("SELECT extracted_text_preview FROM documents WHERE document_id = ?", (fresh,)).fetchone()[0]
    conn.close()
    check("NO extracted text preview is stored outside the analysis result (data minimization)", prev is None, repr(prev)[:80])

# ---------------------------------------------------------------------------
section("TEST 10 — No token (post-logout state) -> protected actions require auth again")
check("without a token, GET /api/issues -> 401", requests.get(f"{BASE}/api/issues").status_code == 401)
check("without a token, GET /api/documents -> 401", requests.get(f"{BASE}/api/documents").status_code == 401)
check("without a token, upload -> 401", requests.post(f"{BASE}/api/documents/upload",
      files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")}).status_code == 401)

# ---------------------------------------------------------------------------
section("Upload validation still enforced for authenticated users")
r = requests.post(f"{BASE}/api/documents/upload", headers=HA, files={"file": ("evil.exe", b"MZ", "application/octet-stream")})
check("unsupported file type -> 400", r.status_code == 400)
r = requests.post(f"{BASE}/api/documents/upload", headers=HA, files={"file": ("empty.pdf", b"", "application/pdf")})
check("empty file -> 400", r.status_code == 400)

# ---------------------------------------------------------------------------
section("Information-leak checks")
for label, resp in [("bad login", bad_pw), ("401 on documents", requests.get(f"{BASE}/api/documents")),
                    ("404 on foreign doc", requests.get(f"{BASE}/api/documents/{DOC_A or 'x'}", headers=HB))]:
    t = resp.text
    check(f"{label}: no stack trace / file paths / SQL in response",
          not any(s in t for s in ("Traceback", "sqlalchemy", "File \"", "/home/", "backend/uploads", "SELECT ")))

print("\n" + "=" * 60)
print(f"PASSED: {len(passed)}   FAILED: {len(failed)}")
if failed:
    print("FAILED TESTS:")
    for f in failed:
        print("  -", f)
sys.exit(1 if failed else 0)
