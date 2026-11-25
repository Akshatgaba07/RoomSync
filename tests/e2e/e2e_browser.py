"""Real-browser end-to-end test (Playwright + Chromium) against a running backend (:8000) and frontend (:5173).
Start both first (see README 'Quick demo without MongoDB'), then: python tests/e2e/e2e_browser.py"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

SHOTS = Path(__file__).parent / "screenshots"; SHOTS.mkdir(exist_ok=True)
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
EMAIL = f"e2e{int(time.time())}@test.com"

def answer_step(page):
    """Answer every question on the current step by clicking the first option / a mid scale value."""
    for g in page.locator("fieldset.field").all():
        if g.locator("[role=radiogroup]").count() == 0: continue
        radios = g.locator("[role=radio]")
        n = radios.count()
        radios.nth(min(2, n - 1) if n == 5 else 0).click()

with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(viewport={"width": 1280, "height": 900})
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL); expect(page.get_by_role("heading", name="Find a roommate you can actually live with.")).to_be_visible()
    page.screenshot(path=SHOTS / "01_landing.png")
    page.get_by_role("link", name="Create your profile").click()
    page.get_by_label("Full name").fill("E2E Tester"); page.get_by_label("Email").fill(EMAIL); page.get_by_label("Password").fill("supersecret1")
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Tell us how you live")).to_be_visible()
    # validation: cannot continue with unanswered step
    page.get_by_role("button", name="Continue").click(); expect(page.get_by_text("Please answer every question")).to_be_visible()
    steps = 0
    while True:
        answer_step(page)
        if page.get_by_role("button", name="Save & find roommates").count(): break
        page.get_by_role("button", name="Continue").click(); steps += 1; page.wait_for_timeout(300)
        if steps == 2: page.screenshot(path=SHOTS / "02_questionnaire.png")
        if steps > 12: raise SystemExit("questionnaire did not terminate")
    # preferences step: dealbreaker + priorities
    page.get_by_role("button", name="Plays music or videos on speaker").click()
    for pr in ["Sleep schedule", "Cleanliness"]: page.get_by_role("button", name=pr, exact=True).click()
    page.screenshot(path=SHOTS / "03_preferences_step.png")
    page.get_by_role("button", name="Save & find roommates").click()
    expect(page.get_by_text("Your top recommendations")).to_be_visible(timeout=10000)
    page.screenshot(path=SHOTS / "04_dashboard.png")
    page.get_by_role("link", name="Roommates").click()
    expect(page.get_by_text("Recommended roommates")).to_be_visible()
    page.wait_for_selector(".match-row"); n1 = page.locator(".match-row").count()
    first = page.locator(".match-row").first.inner_text()
    page.screenshot(path=SHOTS / "05_matches.png", full_page=True)
    assert "Demo" in first or "Synthetic" in first
    # dealbreaker toggle changes results
    page.get_by_label("Hide dealbreaker conflicts").uncheck(); page.wait_for_timeout(800)
    n2 = page.locator(".match-row").count(); assert n2 >= n1, (n1, n2)
    page.get_by_label("Hide dealbreaker conflicts").check(); page.wait_for_selector(".match-row")
    page.locator(".match-row").first.click()
    expect(page.get_by_text("Compatibility breakdown")).to_be_visible(); expect(page.get_by_text("Where you fit")).to_be_visible()
    page.screenshot(path=SHOTS / "06_detail.png", full_page=True)
    # edit preferences -> recalculated
    page.get_by_role("link", name="Preferences").click()
    page.get_by_role("button", name="Has overnight guests often").click(); page.get_by_role("button", name="Save preferences").click()
    expect(page.get_by_text("recalculated")).to_be_visible()
    # mobile layout
    page.set_viewport_size({"width": 390, "height": 800}); page.goto(URL + "/matches"); page.wait_for_selector(".match-row")
    page.screenshot(path=SHOTS / "07_mobile_matches.png")
    assert page.evaluate("document.documentElement.scrollWidth") <= 392, "horizontal overflow on mobile"
    # logout + protected route + wrong password
    page.set_viewport_size({"width": 1280, "height": 900}); page.get_by_role("button", name="Log out").click()
    page.goto(URL + "/matches"); expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    page.get_by_label("Email").fill(EMAIL); page.get_by_label("Password").fill("wrongwrong1"); page.get_by_role("button", name="Log in").click()
    expect(page.get_by_text("Incorrect email or password")).to_be_visible()
    page.get_by_label("Password").fill("supersecret1"); page.get_by_role("button", name="Log in").click()
    expect(page.get_by_text("Recommended roommates")).to_be_visible(timeout=8000)
    assert not errors, errors
    print(f"E2E PASS: {n1} matches strict, {n2} non-strict, no JS errors"); b.close()
