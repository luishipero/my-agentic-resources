---
name: skill-installer
description: Search, browse, and install skills from the aitmpl.com skill marketplace (https://www.aitmpl.com/skills/) into .claude/skills or .codex/skills. Use this skill whenever the user wants to find, download, or install a Claude Code skill, asks about available skills, wants to browse the skill marketplace, mentions aitmpl.com, or asks to "install a skill for X". Supports installing to both Claude Code (.claude) and Codex (.codex) targets, locally or globally.
---

# Skill Installer — aitmpl.com Marketplace

Installs skills from `https://www.aitmpl.com/skills/` (backed by the [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) GitHub repo) into `.claude/skills/` or `.codex/skills/`.

## Source

All skills live at:
```
https://api.github.com/repos/davila7/claude-code-templates/contents/cli-tool/components/skills
```
Format: `{category}/{skill-name}/SKILL.md` plus optional bundled files.

**685+ skills** across 18 categories: `ai-research`, `analytics`, `business-marketing`, `creative-design`, `database`, `development`, `document-processing`, `enterprise-communication`, `media`, `productivity`, `railway`, `scientific`, `security`, `sentry`, `utilities`, `video`, `web-development`, `workflow-automation`.

## Workflow

### Step 1 — Understand the request

Figure out:
- **What skill** the user wants (keyword, category, or "show me all X skills")
- **Target**: `.claude` (Claude Code) or `.codex` (Codex CLI), local (`./`) or global (`~/`)
- If unclear, default to local `.claude` and ask which target after showing results

### Step 2 — Search the catalog

Run `scripts/search.py` to query GitHub and filter skills:

```bash
python3 .claude/skills/skill-installer/scripts/search.py "QUERY"
# Examples:
python3 .claude/skills/skill-installer/scripts/search.py "pdf"
python3 .claude/skills/skill-installer/scripts/search.py "git workflow"
python3 .claude/skills/skill-installer/scripts/search.py --category document-processing
python3 .claude/skills/skill-installer/scripts/search.py --list-categories
```

The script outputs JSON: `[{"name", "category", "dir", "description", "path"}, ...]`

Present results clearly. If there are many matches, show top 10 and ask the user to pick.

### Step 3 — Confirm selection

Show the user:
- Skill name and description
- Install path (e.g. `.claude/skills/pdf-processing/` or `~/.codex/skills/pdf-processing/`)
- Number of files that will be downloaded

Ask for confirmation before installing.

### Step 4 — Install

Run `scripts/install.py` to download from GitHub and write files:

```bash
# Local .claude (default)
python3 .claude/skills/skill-installer/scripts/install.py "category/skill-name"

# Global ~/.claude
python3 .claude/skills/skill-installer/scripts/install.py "category/skill-name" --global

# Local .codex
python3 .claude/skills/skill-installer/scripts/install.py "category/skill-name" --target codex

# Global ~/.codex
python3 .claude/skills/skill-installer/scripts/install.py "category/skill-name" --target codex --global
```

Report what was installed and where.

## Install Path Reference

| Target | Scope  | Path                          |
|--------|--------|-------------------------------|
| claude | local  | `./.claude/skills/{name}/`    |
| claude | global | `~/.claude/skills/{name}/`    |
| codex  | local  | `./.codex/skills/{name}/`     |
| codex  | global | `~/.codex/skills/{name}/`     |

## Tips

- If a skill name has a conflict, prompt the user before overwriting
- Skills can be large (many bundled files) — mention this if downloading takes a moment
- If GitHub API rate-limits (429), suggest the user set `GITHUB_TOKEN` in their env
- After installing, remind the user the skill is active the next time Claude loads in that directory
