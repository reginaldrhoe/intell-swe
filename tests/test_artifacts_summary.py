import tempfile
from pathlib import Path
from mcp.artifacts import summarize_artifacts, summarize_junit_xml, summarize_coverage_xml

SAMPLE_JUNIT = """
<testsuite name="pytest" tests="3" failures="1" errors="0" skipped="1">
  <testcase classname="a" name="test_ok" time="0.01"/>
  <testcase classname="a" name="test_skip">
    <skipped/>
  </testcase>
  <testcase classname="a" name="test_fail">
    <failure message="boom">AssertionError</failure>
  </testcase>
</testsuite>
"""

SAMPLE_COVERAGE = """
<coverage line-rate="0.85" lines-valid="200" lines-covered="170" version="7.5" timestamp="123456"/>
"""


def test_summarize_artifacts_end_to_end():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "artifacts").mkdir()
        junit = d / "artifacts" / "pytest.xml"
        cov = d / "artifacts" / "coverage.xml"
        smoke = d / "artifacts" / "smoke.log"
        e2e = d / "artifacts" / "e2e.log"

        junit.write_text(SAMPLE_JUNIT, encoding="utf-8")
        cov.write_text(SAMPLE_COVERAGE, encoding="utf-8")
        smoke.write_text("PASS: ping endpoint\nFAIL: something broke\n", encoding="utf-8")
        e2e.write_text("All good PASSED\n", encoding="utf-8")

        summary = summarize_artifacts({}, base_dir=d)
        assert summary is not None
        assert "JUnit" in summary
        assert "Coverage" in summary
        assert "Smoke Log" in summary
        assert "E2E Log" in summary

        # Spot-check numbers
        assert "3" in summary  # total tests
        assert "1 failing" in summary
        assert "85.0%" in summary


def test_junit_and_coverage_parsers():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        junit = d / "j.xml"
        cov = d / "c.xml"
        junit.write_text(SAMPLE_JUNIT, encoding="utf-8")
        cov.write_text(SAMPLE_COVERAGE, encoding="utf-8")

        j = summarize_junit_xml(junit)
        c = summarize_coverage_xml(cov)
        assert j and j["tests"] == 3 and j["failures"] == 1 and j["skipped"] == 1
        assert c and abs(float(c["line_rate"]) - 0.85) < 1e-6
