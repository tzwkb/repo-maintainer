# repo-maintainer

Agent skill for systematic GitHub repository cleanup, consolidation, and maintenance.

## What It Does

This skill provides a complete workflow for:
- Scanning and diagnosing repository health
- Standardizing LICENSE / .gitignore / README across repos
- Archiving or deleting outdated projects
- Merging related repositories (monorepo strategies)
- Renaming repositories professionally
- Refactoring code inside repos (terminology unification, file renames)
- Pushing large local refactors back to remote

## Structure

`
repo-maintainer/
├── SKILL.md                        # Core workflow and decision trees
└── scripts/
    ├── repo_analyzer.py            # Analyze repos and generate cleanup report
    └── bulk_file_updater.py        # Batch update LICENSE, .gitignore, README
`

## Usage

Place this folder in your Agent skills directory:
- Windows: ~/.kimi/skills/repo-maintainer/
- Linux/macOS: ~/.config/agents/skills/repo-maintainer/

Trigger phrases include:
- "整理我的 GitHub 仓库"
- "统一所有仓库的 README"
- "合并相关仓库"
- "归档旧项目"
- "大重构后怎么传回远程"

## License

MIT
