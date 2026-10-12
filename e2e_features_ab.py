"""
e2e_features_ab.py — End-to-end tests for:
  Feature A: Case Thread (Multi-turn case thread, pinned composer, collapse/expand, refresh safety, History -> Continue)
  Feature B: PDF Export (Case PDF and Document PDF verification via PyMuPDF; client-side anonymous export network isolation)
"""

import io
import os
import sqlite3
import sys
import time
import uuid
import pymupdf
from playwright.sync_api import sync_playwright

WEB = "http://localhost:5173"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_SAMPLE = os.environ.get(
    "SAMPLE_PDF",
    r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf"
    if os.path.exists(r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf")
    else os.path.join(BASE_DIR, "test_rental_agreement.pdf")
)
SHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SHOTS_DIR, exist_ok=True)

run_id = uuid.uuid4().hex[:6]
EMAIL = f"feature_user_{run_id}@example.com"
PASSWORD = "CorrectHorse9!"

passed, failed = [], []

def check(name, ok, detail=""):
    (passed if ok else failed).append(name)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not ok else ""))

def shot(page, name):
    page.screenshot(path=os.path.join(SHOTS_DIR, f"{name}.png"))

def has(page, text, timeout=12000):
    try:
        page.wait_for_selector(f"text={text}", timeout=timeout)
        return True
    except Exception:
        return False

print("\n" + "=" * 60)
print("RUNNING FEATURE A & FEATURE B PLAYWRIGHT E2E TESTS")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    page = ctx.new_page()

    # Track network requests to report endpoints
    report_requests = []
    page.on("request", lambda r: report_requests.append(r.url) if "/report.pdf" in r.url else None)

    # -------------------------------------------------------------------------
    print("\n=== 1. Anonymous Analysis & Zero-Server-Export Network Assertion ===")
    page.goto(f"{WEB}/issue-analyzer", wait_until="networkidle")
    check("Pre-submit notice appears for anonymous user",
          page.locator("text=An anonymous analysis is one-time only and is not saved").count() >= 1)

    Q1 = "My landlord is refusing to return my security deposit even though I left the apartment in good condition."
    page.fill("textarea", Q1)
    page.click("button:has-text('Analyze issue')")
    check("Anonymous turn 1 finishes and displays one-time banner", has(page, "One-time anonymous analysis.", 20000))
    check("Export report button is present", page.locator("button:has-text('Export report')").count() >= 1)

    # Trigger anonymous Export report — must NEVER send a network request to any report endpoint
    report_requests_before = len(report_requests)
    # Mock window.print in page so it does not block the test runner
    page.evaluate("() => { window.__printed = false; window.print = () => { window.__printed = true; }; }")
    page.click("button:has-text('Export report')")
    time.sleep(1)

    was_printed = page.evaluate("() => window.__printed")
    check("Anonymous export triggered client-side print dialog", was_printed is True)
    check("Anonymous export made ZERO network requests to any /report.pdf endpoint",
          len(report_requests) == report_requests_before)

    # Verify anonymous follow-up gate is unchanged
    check("CTA offers 'Ask Follow-up Question'", page.locator("button:has-text('Ask Follow-up Question')").count() >= 1)
    page.click("button:has-text('Ask Follow-up Question')")
    check("Auth dialog opens over anonymous result", has(page, "Create your secure workspace"))
    shot(page, "feat_01_anon_gate")

    # -------------------------------------------------------------------------
    print("\n=== 2. Register & Save Case (Becomes Turn 1) ===")
    dlg = page.locator("[role=dialog]")
    dlg.locator("input[type=email]").fill(EMAIL)
    pwf = dlg.locator("input[autocomplete='new-password']")
    pwf.nth(0).fill(PASSWORD)
    pwf.nth(1).fill(PASSWORD)
    dlg.locator("button:has-text('Create Account')").click()
    page.wait_for_selector("[role=dialog]", state="detached", timeout=10000)
    check("User registered and logged in", has(page, "You're signed in — save this case?"))

    page.click("button:has-text('Save this case')")
    check("Case saved: 'Saved to your account' appears", has(page, "Saved to your account", 20000))
    check("Continuing case bar is visible", has(page, "Continuing case:"))
    check("Turn 1 is labeled 'Question 1'", has(page, "Question 1"))
    shot(page, "feat_02_saved_turn1")

    # -------------------------------------------------------------------------
    print("\n=== 3. Multi-turn Continuation: Follow-Up Appends as Turn 2 ===")
    Q2 = "What if the landlord claims deductions for normal wear and tear to walls?"
    page.fill("textarea", Q2)
    page.click("button:has-text('Ask follow-up')")
    check("Turn 2 answers successfully", has(page, "Question 2", 20000))
    check("Question 2 contains user query", has(page, "normal wear and tear"))
    check("Question 1 is still present in the thread", has(page, "Question 1"))
    check("Question 1 is collapsed by default in multi-turn view", page.locator("button:has-text('Expand brief')").count() >= 1)
    check("Opposing considerations are present in Turn 2", has(page, "Opposing Considerations"))
    shot(page, "feat_03_multiturn_thread")

    # Expand/collapse test
    page.click("button:has-text('Expand brief')")
    check("Clicking 'Expand brief' expands Turn 1 full analysis", page.locator("button:has-text('Collapse brief')").count() >= 1)
    page.click("button:has-text('Collapse brief')")
    check("Clicking 'Collapse brief' collapses Turn 1 back", page.locator("button:has-text('Expand brief')").count() >= 1)

    # -------------------------------------------------------------------------
    print("\n=== 4. Deep Link & Refresh Safety ===")
    curr_url = page.url
    check("URL updated to deep-link format /case/", "/case/" in curr_url or "caseId" in curr_url)
    page.reload(wait_until="networkidle")
    check("After page refresh, Question 1 is restored", has(page, "Question 1", 10000))
    check("After page refresh, Question 2 is restored", has(page, "Question 2", 10000))
    check("Thread view has both questions after refresh", page.locator("text=Question 1").count() >= 1 and page.locator("text=Question 2").count() >= 1)
    shot(page, "feat_04_thread_after_refresh")

    # -------------------------------------------------------------------------
    print("\n=== 5. History -> Continue This Case ===")
    page.goto(f"{WEB}/history?tab=issue", wait_until="networkidle")
    check("History tab shows the 2-question case", has(page, "2 questions"))
    page.click("text=2 questions")
    check("'Continue this case' button is available", has(page, "Continue this case"))
    page.click("button:has-text('Continue this case')")
    check("Navigates back to case thread with Question 1 and Question 2 intact",
          has(page, "Question 1", 10000) and has(page, "Question 2", 10000))
    shot(page, "feat_05_continued_from_history")

    # -------------------------------------------------------------------------
    print("\n=== 6. PDF Export: Case Brief Download & Text Extraction ===")
    with page.expect_download() as download_info:
        page.click("button:has-text('Export report')")
    case_download = download_info.value
    case_pdf_path = os.path.join(SHOTS_DIR, "test_downloaded_case.pdf")
    case_download.save_as(case_pdf_path)

    check("Case report downloaded successfully", os.path.exists(case_pdf_path))
    pdf_bytes = open(case_pdf_path, "rb").read()
    check("Downloaded file starts with %PDF", pdf_bytes.startswith(b"%PDF"))

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    case_text = "\n".join(page_obj.get_text() for page_obj in doc)
    check("Case PDF contains user Query 1", "security deposit" in case_text.lower())
    check("Case PDF contains user Query 2", "normal wear and tear" in case_text.lower())
    check("Case PDF contains multi-turn context note", "most recent turns" in case_text.lower())
    check("Case PDF contains legal disclaimer", "disclaimer" in case_text.lower() or "informational" in case_text.lower())
    check("Case PDF contains timezone label", "utc" in case_text.lower())
    check("Case PDF contains page numbering", "page 1 of" in case_text.lower())
    check("Case PDF contains NO user email", EMAIL not in case_text)
    check("Case PDF leaks NO internal '_' keys", "_received_query" not in case_text and "_raw_retrieval_counts" not in case_text)

    # -------------------------------------------------------------------------
    print("\n=== 7. PDF Export: Document Audit Download & Text Extraction ===")
    page.goto(f"{WEB}/document-analyzer", wait_until="networkidle")
    check("Document Analyzer file input available", page.locator("input[type=file]").count() == 1)
    page.set_input_files("input[type=file]", PDF_SAMPLE)
    page.click("button:has-text('Analyze document')")
    check("Document analysis completed", has(page, "Executive Risk Summary", 60000))
    check("Export analysis button is available and enabled", page.locator("button:has-text('Export analysis')").count() >= 1)

    with page.expect_download() as doc_download_info:
        page.click("button:has-text('Export analysis')")
    doc_download = doc_download_info.value
    doc_pdf_path = os.path.join(SHOTS_DIR, "test_downloaded_document.pdf")
    doc_download.save_as(doc_pdf_path)

    check("Document audit downloaded successfully", os.path.exists(doc_pdf_path))
    doc_bytes = open(doc_pdf_path, "rb").read()
    check("Document PDF starts with %PDF", doc_bytes.startswith(b"%PDF"))

    d_doc = pymupdf.open(stream=doc_bytes, filetype="pdf")
    doc_text = "\n".join(p_obj.get_text() for p_obj in d_doc)
    check("Document PDF contains score calculation methodology", "score is calculated" in doc_text.lower() or "indicative score" in doc_text.lower())
    check("Document PDF contains risk score or level", "/100" in doc_text or "risk level" in doc_text.lower())
    check("Document PDF contains user document content disclosure", "contains text from" in doc_text.lower())
    check("Document PDF contains legal disclaimer", "disclaimer" in doc_text.lower() or "informational" in doc_text.lower())
    check("Document PDF contains NO user email", EMAIL not in doc_text)
    check("Document PDF leaks NO internal '_' keys", "_received_query" not in doc_text and "_raw_retrieval_counts" not in doc_text)
    shot(page, "feat_06_document_analyzed")

    browser.close()

print("\n" + "=" * 60)
print(f"PLAYWRIGHT E2E FEATURE RESULTS: PASSED: {len(passed)}   FAILED: {len(failed)}")
if failed:
    print("FAILED CHECKS:")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL PLAYWRIGHT E2E FEATURE CHECKS PASSED CLEANLY!")
    sys.exit(0)
