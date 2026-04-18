#!/usr/bin/env python3
"""Bulk GitHub Repository File Updater.

Batch create or update LICENSE, .gitignore, README.md, and descriptions
across multiple repositories via GitHub API.

Usage:
    python bulk_file_updater.py <username> <token> <repo1,repo2,...> <action>

Actions:
    license       — Add MIT LICENSE
    gitignore     — Add language-specific .gitignore (auto-detect Python/PHP)
    readme        — Add minimal README if missing
    description   — Update GitHub description from a JSON map file
    all           — Run license + gitignore + readme + description

Example:
    python bulk_file_updater.py tzwkb ghp_xxx repo1,repo2,repo3 all
"""

import base64
import json
import sys
import urllib.request
from pathlib import Path


HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
}

MIT_LICENSE = """MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

PYTHON_GITIGNORE_URL = (
    "https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore"
)
PHP_GITIGNORE_URL = (
    "https://raw.githubusercontent.com/github/gitignore/main/PHP.gitignore"
)


def api_call(token: str, method: str, url: str, data: dict | None = None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    for k, v in HEADERS_BASE.items():
        req.add_header(k, v)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def fetch_gitignore_template(lang: str) -> str:
    url = PYTHON_GITIGNORE_URL if lang == "Python" else PHP_GITIGNORE_URL
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  Warning: failed to fetch {lang} .gitignore: {e}")
        return ""


def get_file_sha(token: str, owner: str, repo: str, path: str) -> str | None:
    s, r = api_call(
        token, "GET", f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    )
    return r.get("sha") if s == 200 else None


def put_file(
    token: str, owner: str, repo: str, path: str, content: str, message: str, sha: str | None = None
):
    b64 = base64.b64encode(content.encode("utf-8")).decode()
    payload = {"message": message, "content": b64}
    if sha:
        payload["sha"] = sha
    return api_call(
        token,
        "PUT",
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        payload,
    )


def add_license(token: str, owner: str, repo: str, year: str = "2026"):
    sha = get_file_sha(token, owner, repo, "LICENSE")
    if sha:
        print(f"  [{repo}] LICENSE already exists, skipping")
        return
    content = MIT_LICENSE.format(year=year, owner=owner)
    s, _ = put_file(token, owner, repo, "LICENSE", content, "chore: add MIT LICENSE")
    print(f"  [{repo}] LICENSE -> {'OK' if s in (200, 201) else f'FAIL {s}'}")


def add_gitignore(token: str, owner: str, repo: str):
    sha = get_file_sha(token, owner, repo, ".gitignore")
    if sha:
        print(f"  [{repo}] .gitignore already exists, skipping")
        return
    # Detect language
    s, r = api_call(
        token, "GET", f"https://api.github.com/repos/{owner}/{repo}/languages"
    )
    lang = "Python"
    if s == 200 and r:
        top = max(r, key=r.get)
        lang = top if top in ("Python", "PHP") else "Python"
    template = fetch_gitignore_template(lang)
    if not template:
        print(f"  [{repo}] .gitignore -> SKIP (no template)")
        return
    s2, _ = put_file(
        token, owner, repo, ".gitignore", template, f"chore: add {lang} .gitignore"
    )
    print(f"  [{repo}] .gitignore -> {'OK' if s2 in (200, 201) else f'FAIL {s2}'}")


def add_readme(token: str, owner: str, repo: str):
    sha = get_file_sha(token, owner, repo, "README.md")
    if sha:
        print(f"  [{repo}] README.md already exists, skipping")
        return
    title = repo.replace("-", " ").replace("_", " ").title()
    content = f"""# {title}

> A project by {owner}.

## License

[MIT](LICENSE)
"""
    s, _ = put_file(token, owner, repo, "README.md", content, "docs: add README")
    print(f"  [{repo}] README.md -> {'OK' if s in (200, 201) else f'FAIL {s}'}")


def update_description(token: str, owner: str, repo: str, description: str):
    s, _ = api_call(
        token,
        "PATCH",
        f"https://api.github.com/repos/{owner}/{repo}",
        {"description": description},
    )
    print(f"  [{repo}] description -> {'OK' if s == 200 else f'FAIL {s}'}")


def run_action(token: str, owner: str, repos: list[str], action: str, desc_map: dict | None = None):
    for repo in repos:
        print(f"\n>>> {repo}")
        if action in ("license", "all"):
            add_license(token, owner, repo)
        if action in ("gitignore", "all"):
            add_gitignore(token, owner, repo)
        if action in ("readme", "all"):
            add_readme(token, owner, repo)
        if action in ("description", "all"):
            if desc_map and repo in desc_map:
                update_description(token, owner, repo, desc_map[repo])
            else:
                print(f"  [{repo}] description -> SKIP (not in map)")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)

    owner, token, repo_list, action = sys.argv[1:5]
    repos = [r.strip() for r in repo_list.split(",")]

    desc_map = None
    if action in ("description", "all"):
        desc_file = Path("descriptions.json")
        if desc_file.exists():
            with open(desc_file, "r", encoding="utf-8") as f:
                desc_map = json.load(f)
        else:
            print("Warning: descriptions.json not found, descriptions will be skipped in 'all' mode.")

    run_action(token, owner, repos, action, desc_map)
    print("\nDone. Reminder: revoke your PAT at https://github.com/settings/tokens")
