#!/usr/bin/env python3
"""Generate a simple RELEASE_NOTES.md from git tags and commits.

Usage:
  python scripts/generate_release_notes.py            # write RELEASE_NOTES.md for latest tag
  python scripts/generate_release_notes.py -o NOTES.md --tag v1.0.0

The script locates the latest tag (or uses `--tag`), finds the previous
tag (if any), and lists commits between the previous tag and the chosen tag.
Output is written to the file provided with `-o` (default: `RELEASE_NOTES.md`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Iterable
try:
    from urllib.request import Request, urlopen
except Exception:  # pragma: no cover - stdlib always available
    Request = None


FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def get_tags() -> list[str]:
    out = run(["git", "tag", "--sort=-creatordate"])  # newest first
    return [t for t in out.splitlines() if t]


def get_tag_date(tag: str) -> str:
    out = run(["git", "log", "-1", "--format=%aI", tag])
    return out


def get_commits_range(old: str | None, new: str) -> list[dict]:
    if old:
        rng = f"{old}..{new}"
    else:
        rng = new
    fmt = f"%h{FIELD_SEP}%H{FIELD_SEP}%s{FIELD_SEP}%b{FIELD_SEP}%an{FIELD_SEP}%ae{RECORD_SEP}"
    out = run(["git", "log", f"--pretty=format:{fmt}", rng])
    records = [r for r in out.split(RECORD_SEP) if r.strip()]
    commits: list[dict] = []
    for rec in records:
        parts = rec.split(FIELD_SEP)
        if len(parts) < 6:
            continue
        short, full, subject, body, author, email = parts[:6]
        commits.append({
            "short": short,
            "hash": full,
            "subject": subject.strip(),
            "body": body.strip(),
            "author": author.strip(),
            "email": email.strip(),
        })
    return commits


CONVENTIONAL_TYPES = ["feat", "fix", "docs", "chore", "perf", "refactor", "test", "ci"]
TYPE_RE = re.compile(r"^(?P<type>" + "|".join(CONVENTIONAL_TYPES) + r")(?:\([^)]+\))?:\s*(?P<body>.*)", re.I)
PR_RE = re.compile(r"#(?P<number>\d+)")


def classify_commit(subject: str) -> str:
    m = TYPE_RE.match(subject)
    if m:
        return m.group("type").lower()
    return "other"


def extract_pr_numbers(text: str) -> list[int]:
    return [int(m.group("number")) for m in PR_RE.finditer(text)]


def get_github_repo() -> tuple[str, str] | None:
    try:
        url = run(["git", "remote", "get-url", "origin"]).strip()
    except Exception:
        return None
    # support git@github.com:owner/repo.git and https://github.com/owner/repo.git
    m = re.search(r"github.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", url)
    if not m:
        return None
    return m.group("owner"), m.group("repo")


def fetch_pr_description(owner: str, repo: str, pr: int, token: str) -> str | None:
    if not Request:
        return None
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            body = data.get("body") or ""
            # Extract first non-empty paragraph
            for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
                return para
    except Exception:
        return None
    return None


def generate_for_tag(tag: str, prev_tag: str | None, include_pr_descriptions: bool = False) -> str:
    date = get_tag_date(tag)
    try:
        dt = datetime.fromisoformat(date)
        date_s = dt.date().isoformat()
    except Exception:
        date_s = date

    commits = get_commits_range(prev_tag, tag)
    by_type: dict[str, list[dict]] = {}
    for c in commits:
        t = classify_commit(c["subject"])
        by_type.setdefault(t, []).append(c)

    owner_repo = get_github_repo() if include_pr_descriptions else None
    token = os.environ.get("GITHUB_TOKEN") if include_pr_descriptions else None

    lines: list[str] = [f"## {tag} — {date_s}", ""]
    if not commits:
        lines.append("- (no commits found)")
        lines.append("")
        return "\n".join(lines)

    # Order types: conventional ones first, then 'other'
    ordered = [t for t in CONVENTIONAL_TYPES if t in by_type] + (["other"] if "other" in by_type else [])
    for t in ordered:
        entries = by_type.get(t, [])
        if not entries:
            continue
        header = t.capitalize() if t != "other" else "Other"
        lines.append(f"### {header}")
        for c in entries:
            subject = c["subject"]
            short = c["short"]
            author = c["author"]
            line = f"- {subject} ({short}) — {author}"
            lines.append(line)
            # optionally fetch PR descriptions
            if include_pr_descriptions:
                pr_nums = extract_pr_numbers(subject + "\n" + c.get("body", ""))
                if pr_nums and owner_repo and token:
                    owner, repo = owner_repo
                    for pr in pr_nums:
                        desc = fetch_pr_description(owner, repo, pr, token)
                        if desc:
                            # indent the PR description
                            for para in [p for p in desc.split("\n\n") if p.strip()][:1]:
                                lines.append(f"  > {para}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--output", default="RELEASE_NOTES.md")
    p.add_argument("--tag", help="Tag to generate notes for (default: latest tag)")
    p.add_argument("--include-pr-descriptions", action="store_true", help="Fetch PR descriptions from GitHub when possible (requires GITHUB_TOKEN)")
    args = p.parse_args()

    try:
        tags = get_tags()
    except subprocess.CalledProcessError:
        print("Error: Not a git repository or git command failed.", file=sys.stderr)
        return 2

    if not tags:
        print("No tags found in repository.")
        return 1

    tag = args.tag or tags[0]
    if tag not in tags:
        print(f"Tag '{tag}' not found.")
        return 1

    # find previous tag in the sorted list
    prev_tag = None
    try:
        idx = tags.index(tag)
        if idx + 1 < len(tags):
            prev_tag = tags[idx + 1]
    except ValueError:
        prev_tag = None

    header = ["# Release Notes", "", f"Generated: {datetime.utcnow().isoformat()}Z", ""]
    body = generate_for_tag(tag, prev_tag, include_pr_descriptions=args.include_pr_descriptions)
    content = "\n".join(header) + body

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Wrote release notes for {tag} to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
