from playwright.sync_api import sync_playwright

from app.core.config import get_settings


def screenshot_slide(presentation_id: str, slide_id: str) -> bytes:
    settings = get_settings()
    url = f"{settings.frontend_render_url}/render/{presentation_id}/{slide_id}?mode=qa"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(url, wait_until="networkidle")
        image_bytes = page.screenshot()
        browser.close()

    return image_bytes
