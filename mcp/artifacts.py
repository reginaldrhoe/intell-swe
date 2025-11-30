import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _safe_read_text(path: Path, max_bytes: int = 512_000) -> Optional[str]:
    try:
        if not path.exists() or not path.is_file():
            return None
        with open(path, "rb") as fh:
            data = fh.read(max_bytes + 1)
            if len(data) > max_bytes:
                data = data[:max_bytes]
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode(errors="replace")
    except Exception:
        return None


def summarize_junit_xml(xml_path: Path) -> Optional[Dict[str, object]]:
    """Parse a JUnit XML report and return a compact summary.

    Returns a dict: {'tests': int, 'failures': int, 'errors': int, 'skipped': int,
    'suites': int, 'failed_tests': List[Tuple[test_name, message]]}
    """
    try:
        if not xml_path.exists():
            return None
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        # Normalize namespaced tags
        def _tag(t: str) -> str:
            return t.split('}', 1)[-1] if '}' in t else t
        tag = _tag(root.tag).lower()
        summary = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "suites": 0,
            "failed_tests": [],  # list of (name, message)
        }
        if tag == "testsuites":
            summary["suites"] = len(list(root))
            for suite in root:
                if _tag(suite.tag).lower() != "testsuite":
                    continue
                summary["tests"] += int(suite.attrib.get("tests", 0) or 0)
                summary["failures"] += int(suite.attrib.get("failures", 0) or 0)
                summary["errors"] += int(suite.attrib.get("errors", 0) or 0)
                summary["skipped"] += int(suite.attrib.get("skipped", 0) or 0)
                for case in suite.findall(".//testcase"):
                    # failures or errors as children
                    for child in list(case):
                        ctag = _tag(child.tag).lower()
                        if ctag in ("failure", "error"):
                            name = f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}".strip(':')
                            msg = (child.attrib.get("message") or (child.text or "").strip())[:300]
                            summary["failed_tests"].append((name, msg))
        elif tag == "testsuite":
            summary["suites"] = 1
            s = root
            summary["tests"] += int(s.attrib.get("tests", 0) or 0)
            summary["failures"] += int(s.attrib.get("failures", 0) or 0)
            summary["errors"] += int(s.attrib.get("errors", 0) or 0)
            summary["skipped"] += int(s.attrib.get("skipped", 0) or 0)
            for case in s.findall(".//testcase"):
                for child in list(case):
                    ctag = _tag(child.tag).lower()
                    if ctag in ("failure", "error"):
                        name = f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}".strip(':')
                        msg = (child.attrib.get("message") or (child.text or "").strip())[:300]
                        summary["failed_tests"].append((name, msg))
        else:
            return None
        return summary
    except Exception:
        return None


def summarize_coverage_xml(xml_path: Path) -> Optional[Dict[str, object]]:
    """Parse coverage.py or Cobertura coverage XML and return a compact summary.

    Returns: {'line_rate': float, 'lines_valid': int|None, 'lines_covered': int|None}
    """
    try:
        if not xml_path.exists():
            return None
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        tag = root.tag.split('}', 1)[-1].lower()
        out: Dict[str, object] = {"line_rate": None, "lines_valid": None, "lines_covered": None}
        # coverage.py and cobertura both often use <coverage line-rate="...">
        line_rate = root.attrib.get("line-rate") or root.attrib.get("line_rate")
        if line_rate is not None:
            try:
                out["line_rate"] = float(line_rate)
            except Exception:
                pass
        # Optional totals
        lv = root.attrib.get("lines-valid") or root.attrib.get("lines_valid")
        lc = root.attrib.get("lines-covered") or root.attrib.get("lines_covered")
        if lv is not None:
            try:
                out["lines_valid"] = int(float(lv))
            except Exception:
                pass
        if lc is not None:
            try:
                out["lines_covered"] = int(float(lc))
            except Exception:
                pass
        return out
    except Exception:
        return None


def summarize_plain_log(path: Path, max_lines: int = 150) -> Optional[Dict[str, object]]:
    """Heuristically summarize a plain text log (smoke/e2e).

    Returns: {'pass_count': int, 'fail_count': int, 'error_count': int, 'tail': str}
    """
    text = _safe_read_text(path)
    if text is None:
        return None
    lines = text.splitlines()
    tail = "\n".join(lines[-max_lines:])
    # crude counts
    import re
    pass_count = len(re.findall(r"\b(PASS|PASSED)\b", text, re.IGNORECASE))
    fail_count = len(re.findall(r"\b(FAIL|FAILED)\b", text, re.IGNORECASE))
    error_count = len(re.findall(r"\b(ERROR|EXCEPTION|TRACEBACK)\b", text, re.IGNORECASE))
    return {
        "pass_count": pass_count,
        "fail_count": fail_count,
        "error_count": error_count,
        "tail": tail,
    }


def build_markdown_summary(
    junit: Optional[Dict[str, object]],
    coverage: Optional[Dict[str, object]],
    smoke: Optional[Dict[str, object]],
    e2e: Optional[Dict[str, object]],
) -> str:
    parts: List[str] = []
    parts.append("### Attached Test Artifacts Summary\n")
    rows: List[str] = [
        "| Artifact | Signal | Notes |",
        "|---|---:|---|",
    ]
    if junit:
        tests = int(junit.get("tests") or 0)
        fails = int(junit.get("failures") or 0) + int(junit.get("errors") or 0)
        skipped = int(junit.get("skipped") or 0)
        signal = f"{tests - fails - skipped}/{tests} pass"
        rows.append(f"| JUnit | {signal} | {fails} failing, {skipped} skipped |")
    if coverage and coverage.get("line_rate") is not None:
        pct = float(coverage.get("line_rate") or 0.0) * 100.0
        rows.append(f"| Coverage | {pct:.1f}% | Overall line rate |")
    if smoke:
        rows.append(
            f"| Smoke Log | pass={int(smoke.get('pass_count') or 0)} fail={int(smoke.get('fail_count') or 0)} | tail included below |"
        )
    if e2e:
        rows.append(
            f"| E2E Log | pass={int(e2e.get('pass_count') or 0)} fail={int(e2e.get('fail_count') or 0)} | tail included below |"
        )
    parts.append("\n".join(rows))
    # Include short tails for quick context
    if smoke and smoke.get("tail"):
        parts.append("\n<details><summary>Smoke log tail</summary>\n\n````\n" + str(smoke["tail"]) + "\n````\n</details>")
    if e2e and e2e.get("tail"):
        parts.append("\n<details><summary>E2E log tail</summary>\n\n````\n" + str(e2e["tail"]) + "\n````\n</details>")
    # If there are failing unit tests list up to a few
    if junit and junit.get("failed_tests"):
        failed: List[Tuple[str, str]] = list(junit.get("failed_tests") or [])
        head = failed[:5]
        bullet = "\n".join([f"- {name}: {msg}" for name, msg in head])
        parts.append("\n**Top Failures**\n" + bullet)
    return "\n\n".join(parts)


def summarize_artifacts(artifact_paths: Dict[str, object], base_dir: Optional[Path] = None) -> Optional[str]:
    """Build a concise Markdown summary from provided artifact paths.

    artifact_paths keys may include: 'junit_xml', 'coverage_xml', 'smoke_log', 'e2e_log'.
    Values may be str or list[str]. The first existing file is used for each type.
    """
    if not isinstance(artifact_paths, dict):
        return None
    base = Path(base_dir or ".").resolve()
    def pick_path(key: str) -> Optional[Path]:
        val = artifact_paths.get(key)
        candidates: List[str] = []
        if isinstance(val, list):
            candidates = [str(v) for v in val]
        elif isinstance(val, str):
            candidates = [val]
        # default fallbacks
        if not candidates and key == "junit_xml":
            candidates = ["artifacts/pytest.xml", "artifacts/junit.xml"]
        if not candidates and key == "coverage_xml":
            candidates = ["artifacts/coverage.xml"]
        if not candidates and key == "smoke_log":
            candidates = ["artifacts/smoke.log"]
        if not candidates and key == "e2e_log":
            candidates = ["artifacts/e2e.log"]
        for c in candidates:
            p = (base / c).resolve()
            if p.exists() and p.is_file():
                return p
        return None

    junit = None
    cov = None
    smoke = None
    e2e = None
    try:
        p = pick_path("junit_xml")
        if p:
            junit = summarize_junit_xml(p)
    except Exception:
        pass
    try:
        p = pick_path("coverage_xml")
        if p:
            cov = summarize_coverage_xml(p)
    except Exception:
        pass
    try:
        p = pick_path("smoke_log")
        if p:
            smoke = summarize_plain_log(p)
    except Exception:
        pass
    try:
        p = pick_path("e2e_log")
        if p:
            e2e = summarize_plain_log(p)
    except Exception:
        pass

    if not any([junit, cov, smoke, e2e]):
        return None
    return build_markdown_summary(junit, cov, smoke, e2e)
