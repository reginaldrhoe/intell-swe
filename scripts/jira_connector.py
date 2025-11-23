"""Simple JIRA connector to fetch issues and ingest into RAG/Qdrant.

Environment variables expected:
- JIRA_API_URL (e.g., https://yourcompany.atlassian.net)
- JIRA_API_USER (email)
- JIRA_API_TOKEN (API token)

This script fetches issues matching a JQL and writes JSON to stdout.
"""
import os
import requests
import json


def fetch_issues(jql: str = "project = TEST ORDER BY updated DESC", max_results: int = 50):
    base = os.getenv("JIRA_API_URL")
    user = os.getenv("JIRA_API_USER")
    token = os.getenv("JIRA_API_TOKEN")
    if not base or not user or not token:
        raise RuntimeError("JIRA_API_URL, JIRA_API_USER, and JIRA_API_TOKEN must be set")
    url = base.rstrip("/") + "/rest/api/2/search"
    headers = {"Content-Type": "application/json"}
    auth = (user, token)
    payload = {"jql": jql, "maxResults": max_results}
    resp = requests.post(url, headers=headers, auth=auth, json=payload)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--jql", default="project = TEST ORDER BY updated DESC")
    p.add_argument("--max", type=int, default=50)
    args = p.parse_args()
    issues = fetch_issues(args.jql, args.max)
    print(json.dumps(issues, indent=2))
