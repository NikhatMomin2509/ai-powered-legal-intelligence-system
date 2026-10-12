"""
Full UI journey against the real backend (stub analyzer only) + real Vite app.
Covers the spec's UI-visible scenarios. Screenshots -> /tmp/screenshots/auth_*.png
"""
import os, sqlite3, sys, time, uuid
from playwright.sync_api import sync_playwright

WEB = "http://localhost:5173"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "backend", "legal_ai.db"))
UPLOADS = os.environ.get("UPLOADS_DIR", os.path.join(BASE_DIR, "backend", "uploads"))
PDF = os.environ.get(
    "SAMPLE_PDF",
    r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf"
    if os.path.exists(r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf")
    else os.path.join(BASE_DIR, "test_rental_agreement.pdf")
)
SHOTS_DIR = os.environ.get("SHOTS_DIR", os.path.join(BASE_DIR, "screenshots"))
os.makedirs(SHOTS_DIR, exist_ok=True)
run = uuid.uuid4().hex[:6]
passed, failed = [], []

def check(name, ok, detail=""):
    (passed if ok else failed).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if (detail and not ok) else ""))

def shot(page, name): page.screenshot(path=os.path.join(SHOTS_DIR, f"auth_{name}.png"))
def issue_rows(): 
    c = sqlite3.connect(DB); n = c.execute("SELECT COUNT(*) FROM issues").fetchone()[0]; c.close(); return n
def has(page, text, timeout=8000):
    try: page.wait_for_selector(f"text={text}", timeout=timeout); return True
    except Exception: return False

Q1 = "My landlord is refusing to return my security deposit even though I left the apartment in good condition."
EMAIL, PW = f"ui_{run}@example.com", "CorrectHorse9!"
EMAIL2 = f"ui2_{run}@example.com"

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1360, "height": 1000})
    page = ctx.new_page()
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    print("\n=== Logged-out gating (TEST 3 + History/Dashboard) ===")
    page.goto(f"{WEB}/document-analyzer", wait_until="networkidle")
    check("Document Analyzer shows 'Secure document analysis' when logged out", has(page, "Secure document analysis"))
    check("…with 'Sign in to analyze confidential legal documents.'", page.locator("text=Sign in to analyze confidential legal documents.").count() == 1)
    check("…and Log in / Create Account actions", page.locator("a:has-text('Log in')").count() >= 1 and page.locator("a:has-text('Create Account')").count() >= 1)
    check("NO file input exists in the DOM (upload is not merely disabled — it is absent)", page.locator("input[type=file]").count() == 0)
    shot(page, "01_document_gate")

    page.goto(f"{WEB}/history", wait_until="networkidle")
    check("History shows 'History requires an account' when logged out", has(page, "History requires an account"))
    shot(page, "02_history_gate")
    page.goto(f"{WEB}/", wait_until="networkidle")
    check("Dashboard shows NO statistics when logged out", page.locator("text=Issues analyzed").count() == 0 and has(page, "Your activity is private to your account"))

    print("\n=== One-time anonymous analysis (TEST 1 + 2) ===")
    before = issue_rows()
    page.goto(f"{WEB}/issue-analyzer", wait_until="networkidle")
    check("pre-submit note explains anonymous analysis is one-time and not saved", page.locator("text=An anonymous analysis is one-time only and is not saved").count() == 1)
    page.fill("textarea", Q1)
    page.click("button:has-text('Analyze issue')")
    check("anonymous analysis succeeds and shows the one-time banner", has(page, "One-time anonymous analysis.", 20000))
    check("CTA 'Want to continue exploring this case?' appears", has(page, "Want to continue exploring this case?"))
    check("CTA copy: 'Create an account or log in to save your case and ask follow-up questions.'",
          page.locator("text=Create an account or log in to save your case and ask follow-up questions.").count() == 1)
    check("CTA offers Create Account / Log In / Ask Follow-up Question",
          all(page.locator(f"button:has-text('{t}')").count() >= 1 for t in ("Create Account", "Log In", "Ask Follow-up Question")))
    check("result is NOT in History and nothing was written to the issues table", issue_rows() == before)
    page.screenshot(path=os.path.join(SHOTS_DIR, "auth_03_anonymous_result_cta.png"), full_page=True)

    print("\n=== 'Ask Follow-up Question' opens auth OVER the result (result is not lost) ===")
    page.click("button:has-text('Ask Follow-up Question')")
    check("auth dialog opens", has(page, "Create your secure workspace"))
    check("the anonymous result is still on the page behind the dialog", page.locator("text=Stubbed analysis").count() >= 1)
    time.sleep(0.5); shot(page, "04_auth_modal_over_result")

    print("\n=== Register form validation (client side) ===")
    dlg = page.locator("[role=dialog]")
    dlg.locator("input[type=email]").fill(EMAIL)
    pw = dlg.locator("input[autocomplete='new-password']")
    pw.nth(0).fill("short"); pw.nth(1).fill("short")
    dlg.locator("button:has-text('Create Account')").click()
    check("short password rejected with a clear message", dlg.locator("text=at least 8 characters").count() == 1)
    pw.nth(0).fill(PW); pw.nth(1).fill(PW + "x")
    dlg.locator("button:has-text('Create Account')").click()
    check("mismatched confirmation rejected", dlg.locator("text=passwords don't match").count() == 1)
    shot(page, "05_register_validation")

    print("\n=== TEST 4/5 — Register succeeds; UI switches to authenticated ===")
    pw.nth(0).fill(PW); pw.nth(1).fill(PW)
    dlg.locator("button:has-text('Create Account')").click()
    page.wait_for_selector("[role=dialog]", state="detached", timeout=10000)
    check("dialog closes after registering", True)
    check("sidebar shows the account email", has(page, EMAIL))
    check("anonymous result still displayed after signing in", page.locator("text=Stubbed analysis").count() >= 1)
    check("honest 'save this case?' step appears (nothing was silently transferred)", has(page, "You're signed in — save this case?"))
    check("it states the anonymous analysis was never stored", page.locator("text=was never stored, so there is nothing to transfer").count() == 1)
    shot(page, "06_signed_in_save_prompt")
    tok = page.evaluate("() => localStorage.getItem('legal_ai_token')")
    check("a JWT (not the password) is what's stored in the browser", bool(tok) and tok.count(".") == 2 and PW not in tok)
    check("password is not stored anywhere in localStorage/sessionStorage",
          PW not in page.evaluate("() => JSON.stringify([localStorage, sessionStorage])"))

    print("\n=== Save the case, then ask a follow-up in the same case ===")
    page.click("button:has-text('Save this case')")
    check("saved: banner says 'Saved to your account · Case #'", has(page, "Saved to your account", 20000))
    check("a 'Continuing case' bar is shown", has(page, "Continuing case:"))
    page.fill("textarea", "What if he claims that I damaged the apartment?")
    page.click("button:has-text('Ask follow-up')")
    check("follow-up answered", has(page, "Saved to your account", 20000))
    shot(page, "07_followup_in_case")

    print("\n=== History: cases grouped, per-user ===")
    page.goto(f"{WEB}/history?tab=issue", wait_until="networkidle")
    check("History 'Cases' tab lists the case with BOTH questions grouped", has(page, "2 questions"))
    page.click("text=2 questions")
    check("'Continue this case' is offered", has(page, "Continue this case"))
    shot(page, "08_history_case_grouped")

    print("\n=== TEST 6 — authenticated document upload through the UI ===")
    page.goto(f"{WEB}/document-analyzer", wait_until="networkidle")
    check("authenticated view shows the upload dropzone", page.locator("input[type=file]").count() == 1)
    check("privacy notice shown BEFORE upload (accurate, no overclaiming)",
          page.locator("text=Your original document is processed temporarily and is not retained by default.").count() == 1)
    shot(page, "09_document_authenticated")
    before_files = set(os.listdir(UPLOADS)) if os.path.isdir(UPLOADS) else set()
    page.set_input_files("input[type=file]", PDF)
    page.click("button:has-text('Analyze document')")
    check("document analysis completes and results render", has(page, "Flagged clauses", 40000))
    time.sleep(0.5)
    after_files = set(os.listdir(UPLOADS)) if os.path.isdir(UPLOADS) else set()
    check("the raw uploaded file is gone from disk after analysis", after_files == before_files, f"leftover: {after_files - before_files}")
    shot(page, "10_document_results")

    print("\n=== TEST 10 — Logout ===")
    page.locator("button[aria-haspopup=menu]").click()
    check("account menu offers My Cases / My Documents / Logout",
          all(page.locator(f"[role=menuitem]:has-text('{t}')").count() == 1 for t in ("My Cases", "My Documents", "Logout")))
    time.sleep(0.5); shot(page, "11_account_menu")
    page.click("[role=menuitem]:has-text('Logout')")
    page.goto(f"{WEB}/history", wait_until="networkidle")
    check("after logout History requires an account again", has(page, "History requires an account"))
    check("after logout the token is removed from the browser", page.evaluate("() => localStorage.getItem('legal_ai_token')") is None)
    page.goto(f"{WEB}/document-analyzer", wait_until="networkidle")
    check("after logout Document Analyzer is gated again", has(page, "Secure document analysis"))

    print("\n=== Login errors + no cross-user leakage in the UI ===")
    page.goto(f"{WEB}/login", wait_until="networkidle")
    check("login page says 'Welcome back'", has(page, "Welcome back"))
    page.fill("input[type=email]", EMAIL); page.fill("input[autocomplete='current-password']", "WrongPassword1")
    page.click("button:has-text('Log in')")
    check("wrong password shows a generic inline error", has(page, "Incorrect email or password"))
    shot(page, "12_login_error")
    # a second user in the SAME browser must not see the first user's cached data
    page.goto(f"{WEB}/register", wait_until="networkidle")
    page.fill("input[type=email]", EMAIL2)
    pwf = page.locator("input[autocomplete='new-password']"); pwf.nth(0).fill(PW); pwf.nth(1).fill(PW)
    page.click("button:has-text('Create Account')")
    page.wait_for_url(f"{WEB}/", timeout=10000)
    page.goto(f"{WEB}/history", wait_until="networkidle")
    check("second user's History does NOT show the first user's case or document",
          has(page, "Nothing here yet") and page.locator("text=2 questions").count() == 0 and page.locator("text=test_rental_agreement.pdf").count() == 0)
    shot(page, "13_second_user_empty_history")

    check("no uncaught JavaScript errors during the whole journey", not js_errors, "; ".join(js_errors)[:300])
    browser.close()

print("\n" + "=" * 60)
print(f"UI PASSED: {len(passed)}   FAILED: {len(failed)}")
for f in failed: print("  -", f)
sys.exit(1 if failed else 0)
