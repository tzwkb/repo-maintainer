#!/usr/bin/env python3
"""GitHub Repository Cleanup Analyzer.

Scans a user's GitHub repos and generates a structured cleanup report
including missing files, naming issues, outdated markers, and merge candidates.

Usage:
    python repo_analyzer.py <github_username> <personal_access_token>
"""

import json
import sys
import urllib.request
from datetime import datetime


def api_call(token: str, url: str, method: str = "GET", data: dict | None = None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def analyze_repos(username: str, token: str):
    repos = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?per_page=100&page={page}&sort=updated"
        )
        status, data = api_call(token, url)
        if status != 200 or not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    if not repos:
        print("No repos found or API error.")
        return

    report = {
        "total": len(repos),
        "missing_license": [],
        "missing_gitignore": [],
        "missing_readme": [],
        "missing_description": [],
        "outdated_candidates": [],
        "long_names": [],
        "merge_candidates": {},
        "empty_repos": [],
    }

    name_prefixes: dict[str, list[str]] = {}

    for r in repos:
        name = r["name"]
        desc = r.get("description") or ""
        lic = r.get("license")
        size = r.get("size", 0)

        if not lic:
            report["missing_license"].append(name)
        if not desc:
            report["missing_description"].append(name)
        if size == 0:
            report["empty_repos"].append(name)

        # Check root files
        s2, contents = api_call(
            token, f"https://api.github.com/repos/{username}/{name}/contents"
        )
        if s2 == 200:
            files = {f["name"].lower() for f in contents}
            if ".gitignore" not in files:
                report["missing_gitignore"].append(name)
            if "readme.md" not in files:
                report["missing_readme"].append(name)
        else:
            report["missing_gitignore"].append(name)
            report["missing_readme"].append(name)

        # Outdated markers
        lowered = name.lower()
        if any(x in lowered for x in ("outdated", "deprecated", "old", "legacy")):
            report["outdated_candidates"].append(name)

        # Long names
        if len(name) > 40:
            report["long_names"].append(name)

        # Prefix grouping for merge detection
        parts = lowered.replace("_", "-").split("-")
        if len(parts) >= 2:
            prefix = "-".join(parts[:2])
            name_prefixes.setdefault(prefix, []).append(name)

    # Detect merge candidates (3+ repos sharing same prefix)
    for prefix, names in name_prefixes.items():
        if len(names) >= 3 and prefix not in ("journal", "article", "project"):
            report["merge_candidates"][prefix] = names

    # Output
    print("=" * 60)
    print(f"Repository Cleanup Report for {username}")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 60)

    print(f"\nTotal repos: {report['total']}")

    def section(title: str, items: list):
        print(f"\n{title} ({len(items)}):")
        for item in items:
            print(f"  - {item}")

    section("Missing LICENSE", report["missing_license"])
    section("Missing .gitignore", report["missing_gitignore"])
    section("Missing README", report["missing_readme"])
    section("Missing Description", report["missing_description"])
    section("Outdated candidates", report["outdated_candidates"])
    section("Overly long names", report["long_names"])
    section("Empty repos (0KB)", report["empty_repos"])

    if report["merge_candidates"]:
        print(f"\nPotential merge families ({len(report['merge_candidates'])}):")
        for prefix, names in report["merge_candidates"].items():
            print(f"  [{prefix}] -> {', '.join(names)}")
    else:
        print("\nNo obvious merge families detected.")

    print("\n" + "=" * 60)
    print("Recommended action order:")
    print("  1. Archive/delete outdated repos")
    print("  2. Rename long repos")
    print("  3. Merge families if user confirms")
    print("  4. Bulk add LICENSE + .gitignore + README")
    print("  5. Update descriptions")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python repo_analyzer.py <username> <token>")
        sys.exit(1)
    analyze_repos(sys.argv[1], sys.argv[2])
