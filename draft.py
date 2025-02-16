def _init_browser():
    """
    Initializes and returns a singleton Playwright browser instance.
    """
    global _browser
    if _browser is None:
        # If using a special AWS-compatible version, replace with that approach:
        playwright = sync_playwright().start()
        _browser = playwright.chromium.launch(headless=True)
    return _browser

# JavaScript code to hide modal elements
HIDE_MODAL_ELEMENTS_JS = """
() => {
    const shift = 30; // Margin to define corners
    const allElements = document.querySelectorAll('*');
    Array.from(allElements).forEach(element => {
        const style = window.getComputedStyle(element);
        if (style.position === 'fixed') {
            const rect = element.getBoundingClientRect();
            const inCorner = (
                (rect.top < shift && rect.left < shift && rect.height < window.innerHeight - (2 * shift)) ||  // Top-left corner
                (rect.top < shift && rect.right > window.innerWidth - shift && rect.height < window.innerHeight - (2 * shift)) ||  // Top-right corner
                (rect.bottom > window.innerHeight - shift && rect.right > window.innerWidth - shift && rect.width < window.innerWidth - (2 * shift))  // Bottom-right corner
            );
            if (!inCorner) {
                element.style.opacity = 0.3;
            }
        }
    });
}
"""


def get_screen_shot(url: str) -> bytes:
    """
    For a given URL, captures a screenshot of the page (up to 1024px height),
    after executing the 'hideModalElements' JS script in the browser.
    """
    logger.info(f"Capturing screenshot for URL: {url}")
    browser = _init_browser()
    context = browser.new_context(viewport={"width": 1280, "height": 1024})
    page = context.new_page()
    #stealth_sync(page)

    try:
        page.goto(url, wait_until="networkidle")
        page.evaluate(HIDE_MODAL_ELEMENTS_JS)
        screenshot = page.screenshot(full_page=False)
    except Exception as e:
        logger.error(f"Failed to capture screenshot for {url}: {e}")
        raise
    finally:
        context.close()
    return screenshot

