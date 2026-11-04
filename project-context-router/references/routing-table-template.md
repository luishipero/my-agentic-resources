# Project routing templates

Use these sections for the project's routing structure. Preserve unrelated
root instructions. Setup extracts the fenced Markdown blocks under these exact
headings; keep all six headings and blocks intact. The tables are intentionally
empty until routes are verified from the project. Fill them with real paths and
ordinary relative Markdown links from the file containing each link.

## Root AGENTS.md

```markdown
## Context Routing

Before interacting with this project, read the [context routing index](.context-routing/index.md)
and follow the routes relevant to your task.
Use the task and folder descriptions to select relevant routes; open only those
context files and dependencies needed for the task.
```

## Root CLAUDE.md

```markdown
@AGENTS.md
@.context-routing/index.md

## Context Routing

Before interacting with this project, read the [context routing index](.context-routing/index.md)
and follow the routes relevant to your task.
Use the task and folder descriptions to select relevant routes; open only those
context files and dependencies needed for the task.
```

## .github/copilot-instructions.md

```markdown
## Context Routing

Before interacting with this project, read the [context routing index](../.context-routing/index.md)
and follow the routes relevant to your task.
Use the task and folder descriptions to select relevant routes; open only those
context files and dependencies needed for the task.
```

## .context-routing/index.md

```markdown
# Context routing

Select rows using the task, folder path, and description; then read only the
selected CONTEXT.md files and necessary dependencies. Do not open all context
files to choose a route. Folder paths below are relative to the project root;
links are relative to this file.

| Folder | What's there | Context file |
|---|---|---|

## Maintenance contract

Whenever you add, move, or meaningfully change a covered folder, its behavior,
interfaces, business rules, architecture, integrations, or responsibilities,
update its CONTEXT.md and any affected routing entries in the same change. Add
new context files only after user selection and within the recorded scope.
Preserve selected tiers and the layer limit; ask before changing them. Remove
or repair stale entries when folders move or disappear.
Keep selected optional skill and specialist maps linked from this index.
```

Use one row per folder with a CONTEXT.md, sorted by path. Keep this table
header-only when no routes have been verified. Each destination must exist.

Illustrative fictional example only; never copy these rows into a project map
without verifying the project paths and descriptions:

```markdown
| Folder | What's there | Context file |
|---|---|---|
| `src/billing/` | Billing rules | [Context](../src/billing/CONTEXT.md) |
| `src/catalog/` | Product catalogue | [Context](../src/catalog/CONTEXT.md) |
```

## .context-routing/skills.md

```markdown
# Skill routing

Use this map to select a skill for the task, then read its entry point.

| When to use | Skill | Entry point |
|---|---|---|

## Maintenance contract

When a selected skill moves, is removed, changes purpose, or changes entry
point, update its entry in this map in the same change. New skill routes require
user selection. Verify entry points and keep instructions in the skill itself.
```

Keep this table header-only when no relevant skill has been verified. Use
relative links for project-local skills. For an external skill, put its verified
absolute path or `~` path in backticks and mark it as machine-specific, for
example `C:\Users\name\.agents\skills\example\SKILL.md` (machine-specific).
Do not create or install skills to fill the table. Missing project-local paths
are errors; unavailable external paths are reported as notes.

## .context-routing/specialists.md

```markdown
# Specialist routing

Use this map to select an agreed project-specific specialist for the task.

| When to use | Specialist | Entry point |
|---|---|---|

## Maintenance contract

Keep selected entries current when their purpose or entry point changes or they
move or are removed. New specialist routes require user selection. Do not copy
global role definitions or workflows into this map.
```

Use verified project-local relative links to specialist definitions. An external
entry requires a verified absolute or `~` path and a machine-specific note.
