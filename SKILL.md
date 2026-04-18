---
name: repo-maintainer
description: Organize, consolidate, and professionalize GitHub repositories and local codebases. Use when the user asks to clean up GitHub repos, organize repositories, merge related repos, archive outdated projects, standardize README/LICENSE/.gitignore across repos, rename repositories, restructure code, or improve repo professionalism. Covers remote GitHub operations via API and local code refactoring. Triggers on phrases like "整理github仓库", "整理代码", "合并仓库", "归档项目", "统一README", "仓库重命名", "repo cleanup".
---

# Repository Maintainer

Systematic workflow for transforming fragmented GitHub profiles into clean, maintainable, professional repositories.

## Overview

Execute cleanup in 6 phases. Skip phases not applicable. Always get user confirmation on destructive actions (deletion, renaming, merging).

## Phase 1: Scan & Diagnose

Fetch complete repo list via GitHub API:
```bash
curl -sH "Authorization: Bearer TOKEN" \
  "https://api.github.com/user/repos?per_page=100&affiliation=owner"
```

Check for each repo:
- Missing `LICENSE`, `.gitignore`, `README.md`
- Empty `description` field
- Naming inconsistencies (mixed case, overly long names)
- Obvious duplicates or series (e.g., `project`, `project-v2`, `project-mineru`)
- Names containing `outdated`, `deprecated`, `old`, `test`

## Phase 2: Standardize Foundation Files

For every active repo, ensure minimum file set exists:

| File | Rule |
|------|------|
| `LICENSE` | Default to MIT unless user specifies otherwise |
| `.gitignore` | Match primary language (Python/PHP/Node) |
| `README.md` | Must exist; rewrite if only placeholder |
| GitHub Description | One-sentence summary via API |

Bulk update via GitHub Contents API (PUT `/repos/{owner}/{repo}/contents/{path}`).

**Critical: PowerShell here-strings corrupt triple-backtick code blocks in Markdown.** Use Python scripts for bulk README generation to avoid `` ` `` → ` ``` ` escaping failures.

## Phase 3: Handle Outdated Repos

Decision tree:

| Condition | Action |
|-----------|--------|
| Name contains `outdated` / `deprecated` / `old` | Archive or delete |
| Superseded by newer repo | Archive + README successor link |
| History contains leaked secrets (API keys) | **Delete** (archive leaves history intact) |
| Useful as reference but unmaintained | Archive |

Archived repos are read-only. To modify an archived repo (rename, update README), unarchive first (`PATCH {"archived": false}`), make changes, then re-archive.

## Phase 4: Merge Related Repositories

When 2+ repos are variants of the same system (different backends, engines, adapters):

**Option A — Monorepo (Recommended)**
Create a new clean repo (no history). Place each variant in `engines/{name}/` subdirectory.
```
project-suite/
├── main.py              # default engine
├── engines/
│   ├── babeldoc/
│   └── mineru/
└── README.md
```
Preserve each engine's entry point and config. Update root README to explain switching.

**Option B — Git Submodule**
Keep repos independent. Add submodules in parent. Use when history preservation matters more than simplicity.

**Option C — Keep Independent + Link**
Do not merge. Add cross-links in READMEs. Use when variants have diverged significantly.

**If history contains secrets**: Always create a new clean repo and copy current snapshot (via zip download + re-commit). Do not use `git merge` or `git submodule` as history leaks will persist.

## Phase 5: Rename Repositories

Patch API: `PATCH /repos/{owner}/{repo}` with `{"name": "new-name"}`.

Guidelines:
- All lowercase, hyphens only
- Max 3-4 words
- Remove redundant words (`based-on`, `design-and-development`)
- Add `outdated` suffix to archived repos if not already present

GitHub automatically redirects old URLs for a period, but bookmarks and scripts may break. Confirm with user before renaming starred/forked repos.

## Phase 6: Code-Level Refactoring

After remote structure is clean, refactor code inside repos:

1. **Unified terminology** — Replace hardcoded brand names with generic terms (`GPTProcessor` → `LLMProcessor`) while preserving actual API model IDs (`gpt-4`, `gpt-5`).
2. **File renaming** — GitHub Contents API has no rename; create new file with updated content, delete old file.
3. **Directory reorganization** — Use `engines/`, `variants/`, or `core/` + `adapters/` patterns for multi-flavor projects.

## Pushing Large Local Refactors to Remote

When the user downloads code locally, makes heavy changes (file renames, variable renames, structural rewrites), and needs to push back to the remote repo.

### Decision Tree

| Situation | Recommended Action |
|-----------|-------------------|
| Local repo has **no `.git`** (downloaded zip / copied files) | See **Scenario A** below |
| Local is `git clone` with history, remote **unchanged** | Normal `git add → commit → push` |
| Local is `git clone`, remote has new commits | `git pull --rebase` or merge, resolve conflicts, push |
| Local is `git clone`, changes are massive renames + rewrites | See **Scenario B** below |
| Want to preserve remote history but replace all code | See **Scenario C** below |

### Scenario A: Local Has No Git History

Most common when user downloads zip, edits extensively, then wants to sync back.

**Option A1 — Force Push (Personal / Solo Projects)**
```bash
# In local project folder
git init
git add .
git commit -m "refactor: major rewrite"
git remote add origin https://github.com/OWNER/REPO.git
git branch -M main
git push -u origin main --force
```
⚠️ Destroys remote history. Only use when user confirms remote history is disposable.

**Option A2 — Preserve Remote History (Recommended for Valuable Repos)**
```bash
git clone https://github.com/OWNER/REPO.git temp-repo
cp -r temp-repo/.git ./your-local-project/
cd your-local-project
git add .
git commit -m "refactor: major rewrite"
git push
```
This keeps all prior commits and appends the refactor as a single new commit.

**Option A3 — New Clean Repo**
If the rewrite is so radical it is essentially a new project:
1. Create new repo on GitHub
2. Push local code there
3. Archive old repo with successor link in README

### Scenario B: Massive Renames + Rewrites in a Cloned Repo

**Critical rule: never mix file renames and content changes in the same commit.** Git will treat it as "delete old file + create new file" and lose history linkage.

**Step-by-step commit strategy:**
```bash
# Step 1: Rename only
git mv old_module.py new_module.py
git mv old_utils/ new_utils/
git commit -m "refactor: rename modules"

# Step 2: Variable/class renames
git add .
git commit -m "refactor: rename variables and classes"

# Step 3: Logic changes
git add .
git commit -m "feat: update core logic"
```

If user already mixed everything in working tree:
```bash
# Stash current changes, replay in stages
git stash push -m "mixed refactor"

# Restore renames only (use git mv or manual mv + git add)
git mv old_file new_file
git commit -m "refactor: rename files"

# Restore content changes
git stash pop
# Resolve conflicts if any, then commit
```

### Scenario C: Replace All Code but Keep History

Useful when user wants to start fresh code but keep stars/issues/URL.
```bash
git checkout --orphan fresh-start
git rm -rf .
# Copy new local code here
git add .
git commit -m "init: clean rewrite"
git branch -D main
git branch -m main
git push -u origin main --force
```

### Checking Rename Detection

After pushing, verify Git correctly tracked renames:
```bash
git log --follow -- new_file.py
```
If history is broken (shows file as brand new), the rename and content change were committed together.

## Security & Compliance

- **Token hygiene**: After bulk operations, instruct user to revoke the PAT immediately at `https://github.com/settings/tokens`.
- **Secret history**: If a repo ever committed API keys, deleting the repo is the only way to purge history from GitHub. Force-pushing sanitized history does not guarantee removal from GitHub's backup systems.
- **Archived repos with secrets**: If deletion is unacceptable, at minimum remove the repo from public visibility (make private) or delete and recreate empty with clean code.

## Technical Reference

### Encoding Traps (Windows)

PowerShell defaults to CP1252 for stdout, destroying Chinese characters and Markdown code blocks. Always reconfigure:
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

When using `Invoke-RestMethod` in PowerShell with JSON bodies containing backticks or triple backticks, prefer Python scripts for content generation to avoid JSON serialization mangling ` ``` ` into `` ` ``.

### GitHub API Patterns

Create/update file:
```python
import base64, json, urllib.request

payload = {
    "message": "commit msg",
    "content": base64.b64encode(content.encode('utf-8')).decode(),
    "sha": existing_sha  # required for updates
}
req = urllib.request.Request(
    f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
    method="PUT",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {token}", ...}
)
```

Archive/unarchive:
```python
api_call("PATCH", f"/repos/{owner}/{repo}", {"archived": True})
```

Rename repo:
```python
api_call("PATCH", f"/repos/{owner}/{repo}", {"name": "new-name"})
```

Delete repo:
```python
api_call("DELETE", f"/repos/{owner}/{repo}")
```

### Bulk Download Without Clone

Download repo snapshot as zip to avoid slow `git clone` over unstable networks:
```bash
curl -sL "https://github.com/{owner}/{repo}/archive/refs/heads/main.zip" -o {repo}.zip
```

## Bundled Resources

- `scripts/repo_analyzer.py` — Scan user's GitHub repos and generate cleanup recommendations
- `scripts/bulk_file_updater.py` — Batch create/update LICENSE, .gitignore, README via GitHub API
