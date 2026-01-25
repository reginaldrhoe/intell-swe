"""Playwright UI test scaffold (Python).

This is a scaffold to validate the end-to-end visible response path in the web UI.
It uses Playwright (Python). The test is intentionally minimal and configurable for CI.

To run locally:
  python -m pip install playwright
  playwright install
  pytest tests/ui/test_ui_agent_flow.py
"""
import os

import pytest
import requests
from playwright.sync_api import sync_playwright


def test_ui_agent_flow_smoke():
    """Open the UI, perform a simple agent query, and assert visible response.

    Notes:
    - Update `ui_url` to match where the frontend is served locally (default http://localhost:3000).
    - This test expects the UI to expose an input element with id `agent-query` and a submit
      button with id `agent-submit`, and that responses appear in an element with id `agent-response`.
    - Adjust selectors to match your UI.
    """
    if os.getenv("RUN_UI_TESTS") != "1":
        pytest.skip("UI smoke test disabled; set RUN_UI_TESTS=1 to enable")

    ui_url = os.getenv("UI_URL", "http://localhost:3000")

    # Skip early if the UI isn't reachable (common in CI without the frontend running)
    try:
      resp = requests.get(ui_url, timeout=2)
      if resp.status_code >= 500:
        pytest.skip(f"UI not reachable: {ui_url} returned {resp.status_code}")
    except Exception:
      pytest.skip(f"UI not reachable at {ui_url}; set UI_URL or start the frontend to run this test")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(ui_url)

        # Wait for the page to load a known element (adjust as needed)
        page.wait_for_selector('#agent-query', timeout=5000)

        # Fill and submit a query
        page.fill('#agent-query', 'What color is the sky?')
        page.click('#agent-submit')

        # Wait for response to appear
        page.wait_for_selector('#agent-response', timeout=10000)
        content = page.inner_text('#agent-response')

        # Assert we got some response (not just the placeholder)
        assert content.strip(), 'Expected response to have content'
        assert 'Response will appear here' not in content, 'Expected actual response, not placeholder'

        browser.close()
