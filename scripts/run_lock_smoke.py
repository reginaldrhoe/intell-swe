#!/usr/bin/env python3
"""
Python sentinel-based lock smoke test.

Runs two near-concurrent POSTs to /run-agents for the same task id and
reads sentinel files from the `mcp` container to validate that one run
acquired the redis lock and the other observed a conflict.

Usage:
  python scripts/run_lock_smoke.py --task-id 11
"""
import argparse
import json
import subprocess
import threading
import time
import sys

try:
    import requests
except Exception:
    print("Please install requests: pip install requests", file=sys.stderr)
    raise


def post_run(mcp_url, task_id, result_dict, key):
    url = f"{mcp_url.rstrip('/')}/run-agents"
    payload = {"id": task_id}
    try:
        r = requests.post(url, json=payload, timeout=30)
        try:
            body = r.json()
        except Exception:
            body = r.text
        result_dict[key] = (r.status_code, body)
    except Exception as e:
        result_dict[key] = (None, str(e))


def read_sentinels():
    # find container id
    try:
        cid = subprocess.check_output(["docker", "compose", "ps", "-q", "mcp"], text=True).strip()
    except subprocess.CalledProcessError as e:
        print("Failed to run 'docker compose ps -q mcp':", e, file=sys.stderr)
        return None
    if not cid:
        print("No running 'mcp' container found (docker compose ps -q mcp returned empty).", file=sys.stderr)
        return None

    remote_cmd = (
        "echo '--- /tmp/run_agents_entered.log ---'; cat /tmp/run_agents_entered.log || true; "
        "echo '--- /tmp/run_agents_lock_acquired.log ---'; cat /tmp/run_agents_lock_acquired.log || true; "
        "echo '--- /tmp/run_agents_lock_conflict.log ---'; cat /tmp/run_agents_lock_conflict.log || true"
    )

    try:
        out = subprocess.check_output(["docker", "exec", cid, "sh", "-lc", remote_cmd], text=True, stderr=subprocess.STDOUT)
        return out
    except subprocess.CalledProcessError as e:
        print("Failed to read sentinel files from container:", e.output, file=sys.stderr)
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task-id", type=int, default=11)
    p.add_argument("--mcp-url", default="http://localhost:8001")
    p.add_argument("--sleep-ms", type=int, default=50)
    p.add_argument("--wait-secs", type=int, default=60)
    args = p.parse_args()

    results = {}

    th = threading.Thread(target=post_run, args=(args.mcp_url, args.task_id, results, "bg"), daemon=True)
    th.start()

    time.sleep(args.sleep_ms / 1000.0)

    post_run(args.mcp_url, args.task_id, results, "fg")

    th.join(timeout=args.wait_secs)

    if th.is_alive():
        print("Background request did not finish within timeout.")
        sys.exit(2)

    print("Foreground result:", json.dumps(results.get("fg"), default=str, indent=2))
    print("Background result:", json.dumps(results.get("bg"), default=str, indent=2))

    sent = read_sentinels()
    if sent is None:
        print("No sentinel output available; failing.")
        sys.exit(3)

    print("\nSentinel output:\n")
    print(sent)

    acq = sent.count("LOCK_ACQUIRED")
    conf = sent.count("LOCK_CONFLICT") + sent.count("UPFRONT_CONFLICT")
    entered = sent.count("RUN_AGENTS_ENTERED")

    print(f"Summary: entered={entered} acquired={acq} conflict={conf}")

    if entered < 2:
        print("Expected two handler entries but found less; check that both requests reached MCP.")

    if acq >= 1 and conf >= 1:
        print("SMOKE TEST PASSED")
        sys.exit(0)
    else:
        print("SMOKE TEST FAILED: expected >=1 acquired and >=1 conflict")
        sys.exit(4)


if __name__ == "__main__":
    main()
