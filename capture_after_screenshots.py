import os
import time
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "after")
os.makedirs(OUT_DIR, exist_ok=True)

APP_URL = "http://localhost:5173"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop 1440px Context
        ctx_desk = browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = ctx_desk.new_page()

        # Logged out Dashboard 1440
        page_d.goto(f"{APP_URL}/")
        page_d.wait_for_selector("text=Every legal assessment anchored to statutory authority")
        page_d.screenshot(path=os.path.join(OUT_DIR, "01_dashboard_logged_out_1440.png"), full_page=True)

        # Logged out Issue Analyzer 1440
        page_d.goto(f"{APP_URL}/issue-analyzer")
        page_d.wait_for_selector("text=Legal Issue Analyzer")
        page_d.screenshot(path=os.path.join(OUT_DIR, "02_issue_analyzer_intake_1440.png"), full_page=True)

        # Anonymous Issue Analysis 1440
        textarea = page_d.locator("textarea")
        textarea.fill("My landlord refused to return my security deposit of 50000 rupees after I vacated the premises with one month notice.")
        page_d.click("button:has-text('Analyze issue')")
        page_d.wait_for_selector("text=One-time anonymous analysis.", timeout=45000)
        page_d.wait_for_timeout(1000)
        page_d.screenshot(path=os.path.join(OUT_DIR, "03_issue_analyzer_anonymous_result_1440.png"), full_page=True)

        # Open Auth Modal over anonymous result 1440
        page_d.click("button:has-text('Ask Follow-up Question')")
        page_d.wait_for_selector("[role=dialog]")
        page_d.wait_for_timeout(500)
        page_d.screenshot(path=os.path.join(OUT_DIR, "04_auth_modal_over_result_1440.png"), full_page=True)
        # Close modal
        page_d.keyboard.press("Escape")
        page_d.wait_for_timeout(400)

        # Logged out Document Analyzer 1440
        page_d.goto(f"{APP_URL}/document-analyzer")
        page_d.wait_for_selector("text=Secure document analysis")
        page_d.screenshot(path=os.path.join(OUT_DIR, "05_document_analyzer_gated_1440.png"), full_page=True)

        # Logged out History 1440
        page_d.goto(f"{APP_URL}/history")
        page_d.wait_for_selector("text=History requires an account")
        page_d.screenshot(path=os.path.join(OUT_DIR, "06_history_gated_1440.png"), full_page=True)

        # Login page 1440
        page_d.goto(f"{APP_URL}/login")
        page_d.wait_for_selector("text=Welcome back")
        page_d.screenshot(path=os.path.join(OUT_DIR, "07_login_page_1440.png"), full_page=True)

        # Register page 1440
        page_d.goto(f"{APP_URL}/register")
        page_d.wait_for_selector("text=Create your secure workspace")
        page_d.screenshot(path=os.path.join(OUT_DIR, "08_register_page_1440.png"), full_page=True)

        # Register a test user for authenticated states
        ts = int(time.time())
        email = f"design_review_{ts}@example.com"
        page_d.fill("input[type=email]", email)
        pw_inputs = page_d.locator("input[type=password]").all()
        pw_inputs[0].fill("SecurePassword123!")
        pw_inputs[1].fill("SecurePassword123!")
        page_d.click("button:has-text('Create Account')")
        page_d.wait_for_selector(f"text={email}", timeout=15000)

        # Authenticated Dashboard 1440
        page_d.goto(f"{APP_URL}/")
        page_d.wait_for_selector("text=Issues analyzed")
        page_d.screenshot(path=os.path.join(OUT_DIR, "09_dashboard_authenticated_1440.png"), full_page=True)

        # Authenticated Document Analyzer (dropzone) 1440
        page_d.goto(f"{APP_URL}/document-analyzer")
        page_d.wait_for_selector("text=Drag and drop your contract or agreement here")
        page_d.screenshot(path=os.path.join(OUT_DIR, "10_document_analyzer_dropzone_1440.png"), full_page=True)

        # Upload and analyze document
        sample_pdf = r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf"
        if not os.path.exists(sample_pdf):
            sample_pdf = os.path.join(os.path.dirname(__file__), "test_rental_agreement.pdf")
        
        page_d.set_input_files("input[type=file]", sample_pdf)
        page_d.click("button:has-text('Analyze document')")
        page_d.wait_for_selector("text=Flagged clauses", timeout=45000)
        page_d.wait_for_timeout(1000)
        page_d.screenshot(path=os.path.join(OUT_DIR, "11_document_analyzer_result_1440.png"), full_page=True)

        # Authenticated History 1440
        page_d.goto(f"{APP_URL}/history")
        page_d.wait_for_selector("text=All Records")
        page_d.wait_for_timeout(800)
        page_d.screenshot(path=os.path.join(OUT_DIR, "12_history_authenticated_1440.png"), full_page=True)

        # 2. Tablet 1024px Context
        ctx_tab = browser.new_context(viewport={"width": 1024, "height": 768})
        page_t = ctx_tab.new_page()
        page_t.goto(f"{APP_URL}/")
        page_t.wait_for_selector("text=Every legal assessment anchored to statutory authority")
        page_t.screenshot(path=os.path.join(OUT_DIR, "13_dashboard_1024.png"), full_page=True)

        # 3. Mobile 390px Context
        ctx_mob = browser.new_context(viewport={"width": 390, "height": 844})
        page_m = ctx_mob.new_page()

        # Mobile Dashboard 390
        page_m.goto(f"{APP_URL}/")
        page_m.wait_for_selector("text=Every legal assessment")
        page_m.screenshot(path=os.path.join(OUT_DIR, "14_dashboard_mobile_390.png"), full_page=True)

        # Mobile Navigation Drawer Open 390
        page_m.click("button[aria-label='Open navigation menu']")
        page_m.wait_for_selector("text=INDIAN JURISDICTION")
        page_m.wait_for_timeout(400)
        page_m.screenshot(path=os.path.join(OUT_DIR, "15_mobile_nav_drawer_390.png"))
        page_m.click("button[aria-label='Close navigation menu']")
        page_m.wait_for_timeout(300)

        # Mobile Issue Analyzer 390
        page_m.goto(f"{APP_URL}/issue-analyzer")
        page_m.wait_for_selector("text=Legal Issue Analyzer")
        page_m.screenshot(path=os.path.join(OUT_DIR, "16_issue_analyzer_mobile_390.png"), full_page=True)

        # Mobile Document Analyzer Gated 390
        page_m.goto(f"{APP_URL}/document-analyzer")
        page_m.wait_for_selector("text=Secure document analysis")
        page_m.screenshot(path=os.path.join(OUT_DIR, "17_document_analyzer_mobile_390.png"), full_page=True)

        # Mobile Login 390
        page_m.goto(f"{APP_URL}/login")
        page_m.wait_for_selector("text=Welcome back")
        page_m.screenshot(path=os.path.join(OUT_DIR, "18_login_mobile_390.png"), full_page=True)

        browser.close()
        print("ALL_AFTER_SCREENSHOTS_CAPTURED")

if __name__ == "__main__":
    run()
