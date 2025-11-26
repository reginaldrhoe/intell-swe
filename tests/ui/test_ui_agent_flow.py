"""Playwright UI test scaffold (Python).

This is a scaffold to validate the end-to-end visible response path in the web UI.
It uses Playwright (Python). The test is intentionally minimal and configurable for CI.

To run locally:
  python -m pip install playwright
  playwright install
  pytest tests/ui/test_ui_agent_flow.py
"""
from playwright.sync_api import sync_playwright


def test_ui_agent_flow_smoke():
    """Open the UI, perform a simple agent query, and assert visible response.

    Notes:
    - Update `ui_url` to match where the frontend is served locally (default http://localhost:3000).
    - This test expects the UI to expose an input element with id `agent-query` and a submit
      button with id `agent-submit`, and that responses appear in an element with id `agent-response`.
    - Adjust selectors to match your UI.
    """
    ui_url = "http://localhost:3000"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(ui_url)

        # Wait for the page to load a known element (adjust as needed)
        try:
            page.wait_for_selector('#agent-query', timeout=5000)
        except Exception:
            # If the UI structure is different, fail early with a helpful message
            raise AssertionError('Could not find UI selector #agent-query — adjust selectors in the test')

        # Fill and submit a query
        page.fill('#agent-query', 'What color is the sky?')
        page.click('#agent-submit')

        # Wait for response to appear
        page.wait_for_selector('#agent-response', timeout=10000)
        content = page.inner_text('#agent-response')

        assert 'blue' in content.lower(), 'Expected response to mention "blue"'

        browser.close()
