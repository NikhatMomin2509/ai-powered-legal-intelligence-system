# AI-Powered Legal Intelligence System

> **Status of this README:** it currently documents setup and the **Privacy & Authentication**
> feature. The full project README (architecture, datasets, RAG pipeline, viva notes) is a later,
> separate task — nothing below describes it.

This is an informational tool. It is **not legal advice**, does not predict case outcomes, and is
not a substitute for a qualified advocate.

---

## Running the project

### Backend

```bash
cd legal_rag_project
pip install -r requirements.txt            # RAG / indexing dependencies (project root)
pip install -r backend/requirements.txt    # API dependencies (includes pyjwt, bcrypt, email-validator)
```

Create `legal_rag_project/.env` (never commit it):

```
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
# optional
JWT_EXPIRY_HOURS=24
UPLOAD_TTL_MINUTES=60
```

```bash
cd backend
python -m uvicorn app.main:app --reload
```

On first start after upgrading from a pre-authentication database, the server migrates the existing
SQLite file **in place** (adds ownership columns, creates the new tables) and logs each step. It does
not drop or rewrite existing tables.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

**Do not set `VITE_API_BASE_URL` for local development.** By default the app calls the API on the
same hostname the page was opened from. This matters for privacy, not convenience: the one-time
anonymous limit uses a `SameSite=Lax` cookie, and browsers treat `localhost` and `127.0.0.1` as
different sites. Opening `http://localhost:5173` while the API is addressed as `127.0.0.1:8000`
makes every request cross-site, so the cookie is never stored and the anonymous limit silently stops
working (this was reproduced in a real browser). If you previously copied `.env.example` to
`frontend/.env`, delete that line.

---

## Privacy & Authentication

### What a visitor can and cannot do

| | Logged out | Logged in |
|---|---|---|
| Legal Issue Analyzer | **One** analysis per browser, not saved | Unlimited, saved to your account |
| Follow-up questions | Not available | Yes (within a case) |
| Document Risk Analyzer | **Not available** | Yes |
| History / Dashboard statistics | Not available | Your own data only |

### Why documents require an account

Contracts contain names, addresses, financial details and signatures. Unlike a typed question, a
file has to be written somewhere to be processed, so there is no "don't store it at all" option for
an anonymous upload. Document upload, analysis, listing and retrieval therefore all require a valid
login, enforced by the backend — the frontend merely doesn't render the upload control when logged
out (the input is absent from the page, not just disabled).

### Anonymous one-time issue analysis

- `POST /api/issues/analyze` is public. The **first** call from a browser is processed normally.
- The result is returned in that HTTP response and held only in the browser tab's memory. It is
  **not** written to the database, **not** added to History, and creates no user record.
- The limit is enforced **by the server**, not by React state. On the first successful anonymous
  analysis the server issues a random `anon_session_id` cookie (`HttpOnly`, `SameSite=Lax`, 1 year)
  and records only that identifier and a timestamp in the `anonymous_usage` table. That table has no
  column that could hold a query, an IP address, or anything about the analysis. A later anonymous
  request carrying that cookie gets `401` with a message asking the user to log in.
- A **failed** anonymous attempt (e.g. the language model was unavailable) does not consume the
  allowance.
- Refreshing the page does not reset it, because the cookie persists. (Verified in a real browser.)

### Follow-up questions and cases

A follow-up needs an account. When a logged-in user asks a question, the server creates a **case**
(a group of related questions owned by that user). A follow-up is sent with that `case_id`; the
service layer prepends the earlier questions and assessment summaries from *that case only* so the
analyzer can resolve references like "he". History stores only what the user actually typed.

If you read an anonymous answer and then sign in, **nothing is transferred**, because nothing was
stored. The UI says so and offers an explicit "Save this case" action, which re-runs the question
under your account.

### User-specific data isolation

- Every stored issue, case and document has a `user_id`. List endpoints filter **in the database
  query** (`WHERE user_id = <you>`); nothing is fetched globally and filtered afterwards.
- IDs sent by the client are never trusted. Fetching or analyzing an issue, case or document that
  belongs to someone else returns the **same `404`** as one that does not exist, so the API cannot be
  used to discover which IDs exist for other users. (A user's *own* document that was never analyzed and whose
  file was purged returns `410`; a different user still gets `404`. Re-analyzing an already-analyzed
  document simply returns the saved result.)
- Rows that predate this feature have no owner. They are invisible to every user but remain
  physically in the SQLite file until you remove them.

### Temporary document processing

```
upload (authenticated) -> saved as backend/uploads/<random-uuid>.<ext>   [RAW DOCUMENT, temporary]
analyze                -> extract text -> classify -> clauses -> risk -> retrieval -> explanation
                          raw file DELETED as soon as text extraction finishes (also if extraction fails)
saved                  -> analysis result + metadata under your account
```

| Data | What it is | Retention |
|---|---|---|
| **Raw document** | The file you uploaded | Deleted when analysis runs. If analysis never runs (tab closed, request failed), it is purged after `UPLOAD_TTL_MINUTES` (default 60), at server start and on each upload. |
| **Analysis result** | Risk score, flagged clauses **including their text**, explanations, negotiation points | Stored under your account so you can reopen it. Flagged clause text can contain personal information. |
| **Metadata** | Filename, detected type, status, score, timestamps, owner id | Stored under your account. |

No extracted text is stored outside the analysis result. An explicit "keep my original file" option
is **not implemented**; the default (delete) is the only behavior.

What the UI says, and what it deliberately does not: *"Your original document is processed
temporarily and is not retained by default."* It does not claim the system is private or secure in
any absolute sense — see the limitations below.

### Password hashing

Passwords are hashed with **bcrypt** (the `bcrypt` library directly, with a per-password random
salt). Plaintext passwords are never stored, logged, or returned. Passwords must be at least 8
characters and at most 72 bytes (bcrypt silently ignores bytes beyond 72, so longer inputs are rejected
rather than truncated).
Login returns the same error for an unknown email and a wrong password, and spends the same bcrypt
time on both paths (a ~280 ms vs ~2 ms difference was measured before this was fixed).

### Authentication mechanism

- **JWT (HS256)**, signed with `JWT_SECRET_KEY`, default lifetime 24 h, sent as
  `Authorization: Bearer <token>`.
- Endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`. Register also
  logs the user in. There is no logout endpoint: tokens are stateless, so logout discards the token
  in the browser.
- If `JWT_SECRET_KEY` is unset, the server generates a random one for that process and logs a
  warning; all logins are then invalidated on every restart. There is deliberately no built-in
  default secret.
- Protected: every `/api/documents/*` endpoint, `GET /api/issues`, `GET /api/issues/{id}`, and
  follow-ups. Public: `GET /api/health`, and the anonymous first call to `POST /api/issues/analyze`.
- On login, logout, or token expiry the frontend clears its entire query cache, so one user's cached
  data cannot appear for the next.

### Data processed by a third party

Issue text, and the text of flagged document clauses, are sent to **Groq's API** to generate
explanations. Groq's own terms and data handling apply to that text; this project cannot make
guarantees about it. Retrieval (Chroma, BM25) runs locally.

### Logging

Passwords, tokens, anonymous queries and document text are not logged. In two places where an
exception message can contain echoed model output, only the exception *type* is logged. Unexpected
errors are logged with a traceback server-side (never sent to the client) and could in rare cases
include fragments of content; send logs to access-controlled storage in any real deployment.

### Known limitations

1. **Token storage:** the JWT is kept in `localStorage`, so a cross-site-scripting bug would expose
   it. An `HttpOnly` cookie would resist that but needs CSRF protection and more infrastructure than
   this project's scope calls for.
2. **No revocation:** a stolen token is valid until it expires (24 h); logout only clears it locally.
3. **No rate limiting or lockout** on login/register, so password guessing is not throttled.
4. **Registration reveals** whether an email is already registered (`409`). Login does not.
5. **The anonymous limit is a soft, per-browser control**, not an abuse-proof one. Clearing cookies,
   a private window, another browser, or a script that supplies its own cookie value gets another
   anonymous analysis, and two simultaneous first requests can both succeed. If recording the usage
   row fails, the request is still allowed (fails open).
6. **No email verification, password reset, or self-service account/data deletion.**
7. **No transport security configured:** local development runs over plain HTTP, so passwords and
   tokens cross the network unencrypted, and the anonymous cookie has no `Secure` flag. Deployment
   would need TLS and `Secure` cookies.
8. **No encryption at rest** by the application: the SQLite file and stored JSON are plaintext
   (disk-level encryption is the operator's responsibility).
9. **Untrusted file parsing:** PyMuPDF and Tesseract process uploaded files without sandboxing, and
   file type is validated by extension and size only.
10. **Lightweight migration:** the in-place upgrade uses `ALTER TABLE ADD COLUMN`, not a migration
    framework.

This system is not claimed to be "completely secure" or "completely private". It reduces retention of
raw documents, separates users' data, and avoids storing anonymous queries; it does not make the data
immune to the limitations above.

---

## Testing the privacy / authentication behavior

`backend/test_auth_privacy.py` exercises the running API (registration, hashing, login, token
tampering, ownership isolation across two users, anonymous allowance, raw-file deletion and purge,
no-persistence checks including a raw byte search of the database file). Because it needs a live
analyzer, it is meant to be run against `backend/run_stub_server.py`, a **test-only** wrapper that
replaces only the analyzer function and leaves all authentication and privacy code real.

```bash
cd backend
python run_stub_server.py            # terminal 1 (test-only; never serve real users with this)
SERVER_LOG=... python test_auth_privacy.py   # terminal 2
```

Browser-level checks live in `e2e_auth_ui.py` and `e2e_cookie_samesite.py` (Playwright).
