"""Does the one-time anonymous limit actually hold in a REAL browser?
Usage: python e2e_cookie_samesite.py <label>   (page is always http://localhost:5173)"""
import sys, time
from playwright.sync_api import sync_playwright

label = sys.argv[1]
Q1 = "My landlord is refusing to return my security deposit even though I left the apartment in good condition."
Q2 = "A completely different second question about my tenancy dispute and the deposit."

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1300, "height": 900})
    page = ctx.new_page()
    reqs = []
    page.on("request", lambda r: reqs.append(r) if "/api/issues/analyze" in r.url else None)

    page.goto("http://localhost:5173/issue-analyzer", wait_until="networkidle")
    print(f"[{label}] page origin: localhost:5173 | API base the app is using: ", end="")
    print(page.evaluate("() => performance.getEntriesByType('resource').length >= 0 ? 'see request url below' : ''"))
    page.fill("textarea", Q1)
    page.click("button:has-text('Analyze issue')")
    page.wait_for_selector("text=One-time anonymous analysis.", timeout=20000)
    print(f"[{label}] request URL used: {reqs[-1].url}")
    print(f"[{label}] 1st anonymous analysis: result shown")
    cookies = ctx.cookies()
    print(f"[{label}] cookies the browser actually stored: {[(c['name'], c['domain'], c['httpOnly'], c['sameSite']) for c in cookies]}")

    # refresh wipes the in-memory 'already used' flag, so ONLY the server can stop request #2
    page.reload(wait_until="networkidle")
    page.fill("textarea", Q2)
    page.click("button:has-text('Analyze issue')")
    outcome = None
    for _ in range(40):
        if page.locator("[role=dialog]").count() > 0:
            outcome = "BLOCKED (auth dialog opened — server returned 401)"
            break
        if page.locator("text=One-time anonymous analysis.").count() > 0:
            outcome = "BYPASSED (a SECOND anonymous analysis succeeded)"
            break
        time.sleep(0.5)
    print(f"[{label}] 2nd anonymous attempt after page refresh: {outcome}")
    browser.close()
