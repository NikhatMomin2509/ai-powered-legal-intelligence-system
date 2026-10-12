import os
import time
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", "baseline")
os.makedirs(OUT, exist_ok=True)
PDF = r"c:\Users\nikha\Downloads\test_rental_agreement_for_legal_risk_analyzer.pdf"

def capture_suite():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        for width, label in [(1440, "1440"), (390, "390")]:
            ctx = browser.new_context(viewport={"width": width, "height": 900 if width==1440 else 844})
            page = ctx.new_page()
            
            # 1. Dashboard logged out
            page.goto("http://localhost:5173/", wait_until="networkidle")
            page.screenshot(path=os.path.join(OUT, f"dashboard_logged_out_{label}.png"), full_page=True)
            
            # 2. Issue Analyzer logged out empty
            page.goto("http://localhost:5173/issue-analyzer", wait_until="networkidle")
            page.screenshot(path=os.path.join(OUT, f"issue_analyzer_empty_{label}.png"), full_page=True)
            
            # 3. Document Analyzer logged out gate
            page.goto("http://localhost:5173/document-analyzer", wait_until="networkidle")
            page.screenshot(path=os.path.join(OUT, f"document_analyzer_gate_{label}.png"), full_page=True)
            
            # 4. History logged out gate
            page.goto("http://localhost:5173/history", wait_until="networkidle")
            page.screenshot(path=os.path.join(OUT, f"history_gate_{label}.png"), full_page=True)
            
            # 5. Login page
            page.goto("http://localhost:5173/login", wait_until="networkidle")
            page.screenshot(path=os.path.join(OUT, f"login_{label}.png"), full_page=True)
            
            # 6. Register page
            page.goto("http://localhost:5173/register", wait_until="networkidle")
            page.screenshot(path=os.path.join(OUT, f"register_{label}.png"), full_page=True)
            
            # 7. Anonymous issue analysis result
            page.goto("http://localhost:5173/issue-analyzer", wait_until="networkidle")
            page.fill("textarea", "My landlord is refusing to return my security deposit even though I left the apartment in good condition.")
            page.click("button:has-text('Analyze issue')")
            page.wait_for_selector("text=One-time anonymous analysis.", timeout=20000)
            time.sleep(1)
            page.screenshot(path=os.path.join(OUT, f"issue_analyzer_anon_result_{label}.png"), full_page=True)
            
            # 8. Auth modal over anonymous result
            page.click("button:has-text('Ask Follow-up Question')")
            page.wait_for_selector("text=Create your secure workspace", timeout=5000)
            time.sleep(0.5)
            page.screenshot(path=os.path.join(OUT, f"auth_modal_overlay_{label}.png"))
            
            ctx.close()
            
        browser.close()
        print("Baseline screenshots taken successfully!")

if __name__ == "__main__":
    capture_suite()
