import asyncio
import json
from agents.agents import (
    EngineerCodeReviewAgent,
    RootCauseInvestigatorAgent,
    DefectDiscoveryAgent,
    RequirementsTracingAgent,
    PerformanceMetricsAgent,
    AuditAgent,
)

"""
Agent Delegation Demo (sequential + conditional delegation)

Demonstrates a simple delegation pattern:
- Phase 1: EngineerCodeReviewAgent produces review notes and a list of candidate files.
- Phase 2: Delegates to RootCause + Defect agents with augmented context from Phase 1.
- Phase 3: Requirements + Metrics + Audit finalize with evidence-aware summaries.

Outputs a structured JSON report showing per-phase results and delegation provenance.
"""


async def run_delegation(task):
    report = {
        "task": {k: task.get(k) for k in ("id", "title", "description")},
        "phases": {},
        "delegation": [],
    }

    # Phase 1: Engineer review
    engineer = EngineerCodeReviewAgent("EngineerAgent")
    phase1_out = await engineer.process(task)
    report["phases"]["phase1_engineer_review"] = phase1_out

    # Extract candidate files if present in free-form text
    files = task.get("files") or []
    if not files and isinstance(phase1_out, str):
        # naive heuristic: look for 'files [' pattern
        import re
        m = re.search(r"files\s*\[([^\]]+)\]", phase1_out)
        if m:
            items = [x.strip() for x in m.group(1).split(",")]
            files = [i for i in items if i]

    delegated_task = dict(task)
    if files:
        delegated_task["files"] = files
    delegated_task["engineer_notes"] = phase1_out

    report["delegation"].append({
        "from": "EngineerAgent",
        "to": ["RootCauseAgent", "DiscoveryAgent"],
        "context_keys": ["files", "engineer_notes"],
    })

    # Phase 2: Root cause + defect discovery with augmented context (run in parallel)
    root_cause = RootCauseInvestigatorAgent("RootCauseAgent")
    discovery = DefectDiscoveryAgent("DiscoveryAgent")
    rc_task = asyncio.create_task(root_cause.process(delegated_task))
    dd_task = asyncio.create_task(discovery.process(delegated_task))
    rc_out, dd_out = await asyncio.gather(rc_task, dd_task)
    report["phases"]["phase2_root_cause"] = rc_out
    report["phases"]["phase2_defect_discovery"] = dd_out

    # Phase 3: Requirements + metrics + audit (parallel), also consume previous outputs
    requirements = RequirementsTracingAgent("RequirementsAgent")
    metrics = PerformanceMetricsAgent("MetricsAgent")
    audit = AuditAgent("AuditAgent")

    phase3_task = dict(delegated_task)
    phase3_task["root_cause_summary"] = rc_out
    phase3_task["defect_summary"] = dd_out

    req_t = asyncio.create_task(requirements.process(phase3_task))
    met_t = asyncio.create_task(metrics.process(phase3_task))
    aud_t = asyncio.create_task(audit.process(phase3_task))
    req_out, met_out, aud_out = await asyncio.gather(req_t, met_t, aud_t)
    report["phases"]["phase3_requirements"] = req_out
    report["phases"]["phase3_metrics"] = met_out
    report["phases"]["phase3_audit"] = aud_out

    return report


def main():
    task = {
        "id": 1001,
        "title": "Delegation demo",
        "description": "Demonstrate agent-to-agent delegation with evidence flow",
        "files": ["auth.py", "pipeline.py"],
    }
    report = asyncio.run(run_delegation(task))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
