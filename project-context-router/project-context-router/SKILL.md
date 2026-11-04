---
name: project-context-router
description: Builds and maintains project context routing through AGENTS.md and optional agent-specific pointers to .context-routing/index.md, which maps folders to verified CONTEXT.md files, with optional maps for agreed skills and specialists. Use when setting up or updating project context, routing tables, context maps, or folder-level context files. Also use when a meaningful change to behavior, interfaces, business rules, architecture, or responsibilities affects existing routes.
---

# Project Context Router

Give agents a small entry point to the project's code and business context,
with a folder context map and optional maps for agreed skills and specialists.
Read only the context and skills relevant to the current task.

Inspect existing instructions and routing first. Use **setup** when no routing
exists; use **maintain** for an existing system. An index is a useful signal,
not the sole test: partial or legacy routing also needs maintenance. Setup
creates missing routing files and appends root pointers; it preserves existing
content and does not infer routes or migrate older routing automatically.

## Before setup — Check the skill installation

Determine the loaded skill's actual base directory using the host's skill
metadata. Check that the complete matching package, including `SKILL.md`,
`scripts/setup.py`, `scripts/validate.py`, and referenced templates, is
available in a persistent skill location recognized by the current client.
A user, project, or managed/plugin installation counts; do not assume that a
downloaded or temporarily attached `SKILL.md` is installed or contains scripts.
Do not substitute scripts from a different copy or version.

If the package is not installed there or its required files are unavailable,
use the host's user-question tool to ask where to install the skill:

- **User level:** available across projects for that user and client.
- **Project level:** available to the project; the skill files may be shared
  with collaborators if committed.

Wait for the choice before installing or setting up routing. Use a location
supported by the active client, not one inferred from another client. For
example, Copilot CLI supports `~/.copilot/skills/` for user skills and
`.github/skills/` for project skills; Claude Code supports
`~/.claude/skills/` and `.claude/skills/`, respectively. Other supported
locations and clients may differ.

Install the complete package from the known, trusted source into the selected
scope using the client's supported mechanism. If the source is missing or
incomplete, ask the user for a complete trusted package instead of fabricating
files or downloading an unspecified version. Do not overwrite or merge an
existing destination; report conflicts and ask how to proceed. Verify the
installed instructions, scripts, and referenced files match the trusted source.
Reload or restart the client if needed and verify discovery when the host
supports it; otherwise report discovery as unverified. Run checks using that
package's actual path.

If the user declines installation, the source cannot be established, or
installation is unavailable, stop before setup and report that the required
script checks could not be run. Do not claim validation succeeded. An existing
complete, recognized installation needs no installation question.

## Step 1 — Establish the routing structure

Use this structure at the project root:

```text
AGENTS.md
CLAUDE.md                  # optional
.github/copilot-instructions.md  # optional
.context-routing/
  index.md
  skills.md        # optional
  specialists.md   # optional
```

- Root `AGENTS.md` points to `.context-routing/index.md`. Preserve unrelated
  instructions and managed blocks; keep routing tables in the routing folder.
- Pass `--claude-md` to create or update `CLAUDE.md` when Claude routing is
  selected. If the file is missing, the flag creates it with only `@AGENTS.md`.
  Without `CLAUDECODE`, an existing file with that import is left unchanged; an
  existing file without it gains the index import and pointer but not an
  `@AGENTS.md` import. When `CLAUDECODE` is set, add a normal Markdown pointer
  to the index to an existing `CLAUDE.md` if missing, preserving its contents
  and without adding an index import. For compatibility, `CLAUDECODE` without
  the flag creates a missing file with `@AGENTS.md`, the index import and a
  routing pointer.
- If an existing root `CLAUDE.md` is a symlink directly to the regular root
  `AGENTS.md`, leave the symlink untouched and update `AGENTS.md` only. Do not
  add `@AGENTS.md` to the shared file. Reject other symlink targets when
  `CLAUDE.md` is selected, including broken links.
- If GitHub.com Copilot Chat support is selected, pass
  `--copilot-instructions` to create or update `.github/copilot-instructions.md`
  with a relative pointer to the same index. Preserve existing instructions.
  Chat must have the repository attached, and following the pointer depends on
  the surface and available context; do not assume links are expanded.
- `index.md` contains the folder-to-context table, reading order, maintenance
  contract, and links to selected optional maps. It holds routing, not domain detail.
- `skills.md` optionally routes tasks to selected skills; `specialists.md`
  optionally routes tasks to selected project specialist agents.

Reuse verified entries when maintaining the system. Setup never
overwrites existing files; maintenance edits relevant files in place and
preserves unrelated content. Do not invent routes or automatically migrate
older routing. If a manual migration is requested, preserve unrelated guidance,
update moved links, and keep one maintained copy of each entry. Create root
entry files only when absent and append missing pointers to existing files.
State whether you are setting up or maintaining the system.

An existing legacy `agents.md` folder map remains supported. For a requested
migration, follow [legacy migration](references/validation-and-navigation.md#legacy-migration).

When there is no recorded architecture-overview decision, ask whether the user
wants an `ARCHITECTURE.md`: a concise system overview of components, boundaries,
and data flow. A direct request counts as selection. Continue independent routing
work while waiting; create or update the overview only after selection. Inspect
and preserve any existing file. Record the choice in `index.md` so maintenance
does not repeat the question. Follow [architecture overview](references/architecture-overview.md).

## Step 2 — Pick which folders get a CONTEXT.md

Inspect the project and propose specific folders and a detail tier for each:
**thin** for purpose and key files, **standard** for business context and
conventions as well, or **deep** for complex domains with architecture,
data flow, and impact. Favor distinct business domains, non-obvious logic,
and integration boundaries; a generic utility folder may need no file.

Skip dependencies, build output, vendored or generated code, and test fixtures.
Include test folders when their conventions matter.

Before creating or expanding folder contexts, use the host's user-question
tool (such as `AskUserQuestion` or `ask_user`) to ask these separately:

1. Show the proposed folder paths grouped by thin, standard, and deep, then
   ask: **Which folders should have a CONTEXT.md, and which detail tier should
   each use?** Offer accepting the recommendations or selecting folders and
   tiers. Allow the user to omit folders or assign different tiers.
2. Ask: **How many folder layers below the project root may contain a
   CONTEXT.md?** Offer **1 layer** (for example `src/`) and **2 layers**
   (for example `src/billing/`). The project root is layer 0. This limit
   applies to file locations, not how far to inspect source code.

Do not create a folder context until both decisions are known. If selected
paths exceed the chosen limit, identify them and ask the user to resolve the
conflict before creating them. Do not silently omit selections. If a
user-question tool is unavailable, obtain the decisions through the host's
supported user-input mechanism; do not assume approval.

Record the chosen limit in `index.md` as `Context scope: 1 layer` or
`Context scope: 2 layers`. In the folder table, include each selected tier in
the description, for example `Billing rules (tier: standard)`. The table
records selected folders alongside any preserved legacy routes; label legacy
routes without a recorded tier as unclassified, not as user-selected.
Create only the selected files within the limit.
Reuse recorded choices on maintenance without asking again unless the user
requests a change. If an existing project has no recorded choices, ask before
expanding its context scope; preserve existing files and routes, including
those outside the selected limit, unless the user explicitly authorizes changes.

## Step 3 — Write each CONTEXT.md

Use [the context template](references/context-md-template.md) for section
menus and examples:

- **Thin:** purpose and key files for simple folders.
- **Standard:** purpose, key files, business context, and conventions or gotchas.
- **Deep:** standard content plus architecture, data flow, dependencies, and
  links to related context files for core or complex domains.

Use the selected tier for each folder. Each file should explain what can safely
change here and what else it affects.
Keep shared context in one place and link to it using relative Markdown links.
Replace all template markers with project evidence. Verify declared key files,
workflow inputs and commands against the project; do not invent a check.
Declare paths in Key files and Inputs lists as `./path` relative to the context
file, or `repo:path` relative to the project root. Unmarked entries are not
validated as paths; preserve legacy contexts and update declarations when
maintaining them.
Keep thin contexts thin: workflow contracts are for repeatable procedures only.
Distinguish observed live behavior from planned, stubbed, or uncertain behavior.

## Step 4 — Write the routing maps

Use [the routing templates](references/routing-table-template.md) for the root
pointer, index, and map templates. Optional maps require explicit user selection.
Resolve Markdown links relative to the file containing them.

In `index.md`, use one row per folder that has a `CONTEXT.md`, including nested
folders. Include its path, what lives there, and a link to its context file.
Sort by folder path. Leave the table empty until actual routes are verified;
never copy illustrative rows into a project map.

Optional skill and specialist routes require explicit user selection; prior
selections and direct requests for named entries count. Discover and recommend
only relevant verified project candidates, including Copilot and Claude Code
skills and agents. Follow [optional route selection](references/optional-route-selection.md)
when considering these maps. Preserve existing maps and do not add disputed or
unselected routes.

Keep `index.md` short: select the folder context directly from its table, and
follow optional maps only when the task needs them. Move domain detail into the
owning context file rather than expanding the router into another specification.

## Step 5 — Keep the system current

Include the maintenance contracts from the map templates in their respective
files. In maintain mode, update affected context and routing in the same change:

- A meaningful change to behavior, interfaces, business rules, architecture,
  integrations, or responsibilities updates the relevant `CONTEXT.md` and any
  affected `index.md` entries (or the legacy folder map until migrated).
- Respect the recorded folder selections, tiers, and layer limit. Ask before
  adding a new context outside those selections or changing the recorded scope.
- An explicitly selected skill or specialist change updates its optional map;
  do not add new routes without selection.
- When an adopted architecture overview is affected, update it in the same
  change; keep unchanged decisions and avoid unnecessary rewrites.
- A change to the routing entry points updates `index.md` and the root pointers.

Avoid rewriting context for edits that do not change its meaning. Report what
you updated rather than leaving maintenance for a separate follow-up.

## Step 6 — Set up, validate, and navigate

Use Python 3.10 or newer with its standard library; this package has no external
dependencies. For initial setup, run the setup helper once with the existing
project root. It creates missing core routing files and validates them. After
selection, optional flags create the chosen maps; the helper never prompts and
never overwrites an existing index or map. If an existing index lacks a selected
map link, report it for authorized maintenance. For maintenance or a read-only
check, run the validator directly. When a user selects an additional entry
point in an existing project, run setup with the corresponding flag; it
preserves the existing index and other instruction content. Run the fixture
suite when developing or updating this skill package. Use the verified package
from the installation check above. Replace `<skill-dir>` with its actual
directory and `<PROJECT_ROOT>` with the project's existing root directory:

```sh
python "<skill-dir>/scripts/setup.py" "<PROJECT_ROOT>"  # core only
# After selection, optionally pass --claude-md, --copilot-instructions,
# --include-skills, and/or --include-specialists
python "<skill-dir>/scripts/validate.py" "<PROJECT_ROOT>"
# Add --claude-md and/or --copilot-instructions to require selected entry points.
python -B -m unittest discover -s "<skill-dir>/tests" -v
```

Setup validates proposed contents before writing and reports validation errors
and notes. A write-time failure may leave partial changes; review the reported
files manually. The validator accepts legacy projects
with either root entry; unselected optional instruction files without a pointer
are reported as notes. A `CLAUDE.md` with `@AGENTS.md` is valid when the
imported root `AGENTS.md` links to the index. Use the corresponding validator
flags to require optional entry points.
The validator checks routing files
and linked context documents, including basic content and declared-path checks.
It does not establish factual accuracy or discover all unmapped source folders.
See [validation and navigation](references/validation-and-navigation.md) for
the checks' Markdown-link limits and a cold navigation walkthrough.

## Step 7 — Verify context quality and report

Check the root pointers, map links, context destinations, and skill locations.
Check that existing instructions and managed blocks remain intact, and that
there are no duplicate routes or stale paths. If a skill location is not
available in this environment, report it as unverified. For deep context,
record supporting evidence, callers and integrations, validation commands,
unresolved conflicts, and what can be affected by a change.

After structural validation, use the proportional checks in [validation and
navigation](references/validation-and-navigation.md). Initial setup, routing
redesigns and consequential changes need fresh isolated navigation walks and
quality review. For genuinely small maintenance edits, check affected routes
and their source evidence; report when independent review was not performed.
For required independent checks, report unavailable evaluation as pending.

Review scope, duplicated facts, important source claims, change impact, and
context size. Resolve contradictions against the owning source and record
uncertainty instead of presenting guesses as verified. A validator pass alone
does not verify content: applicable checks must pass or limitations remain
explicit. Preserve the
user's task scope; a context-quality review does not authorize code refactoring.

Briefly report the routing location, context files created or updated, skill
entries changed, and any unresolved destinations. Link to files instead of
dumping their contents.
