# CONTEXT.md templates by depth

Use the tier selected for the folder (see SKILL.md Step 2).
These are starting shapes, not rigid schemas — drop or add sections as the
folder actually warrants.

## Thin (utility / generic folders)

```markdown
# CONTEXT: <folder path>

**Purpose:** <1-2 sentences — what this folder holds and why>

**Key files:**
- `./file.ts` — <what it does, one line>
- `./other.ts` — <what it does, one line>
```

## Standard (most business/module folders)

```markdown
# CONTEXT: <folder path>

**Purpose:** <what this folder is for, in code terms>

**Business context:** <why it exists in product terms — what user-facing
or business capability it supports>

**Key files:**
- `./file.ts` — <role>
- `./file2.ts` — <role>

**Conventions / gotchas:**
- <non-obvious decision, naming convention, or trap someone would hit
  editing here without this context>
```

## Deep (core domains, high-complexity or high-blast-radius folders)

```markdown
# CONTEXT: <folder path>

**Purpose:** <what this folder is for>

**Business context:** <product/business role — who relies on this and why
it matters if it breaks>

**Architecture / data flow:**
<how data or control enters and leaves this folder; key sequence if
there's a non-obvious flow — e.g. webhook → validation → queue → handler>

**Key files:**
- `./file.ts` — <role, and anything sharp-edged about it>

**Evidence and impact:**
- Evidence: <tests, source locations, or observed behavior supporting this description>
- Callers / integrations: <who uses this area and what it depends on>
- Change impact: <behavior, data, or responsibilities affected by a change>

**Validation:**
- `<command>` — <what it checks>

**Unresolved conflicts:**
- <contradiction between sources or an explicit statement that none are known>

**Conventions / gotchas:**
- <traps, required ordering, feature flags, etc.>

**Related context:**
- [Related folder](../related-folder/CONTEXT.md) — <why it's related>
```

## Notes

- Use ordinary relative Markdown links for related context. Links resolve from
  the file containing them; do not use wiki-link syntax such as `[[path]]`.
- Keep each CONTEXT.md scoped to its own folder. If two folders share a
  lot of context, that's usually a sign one of them should link to the
  other rather than duplicate the explanation.
- Record a source revision or date when freshness affects whether the context
  can be trusted; do not add timestamps without that reason.
- Replace unfinished template markers. Verify declared paths, important source
  claims and documented commands. Distinguish live behavior from planned or
  stubbed behavior; record uncertainty instead of guessing.
- Put paths in backticks under Key files or Inputs list headings. Prefix paths
  with `./` for this CONTEXT.md's directory, or `repo:` for the project root.
  For example, `./Makefile` and `repo:src/api/schema.json` are checked;
  unmarked entries such as `Invoice.total` are not checked. Paths must stay
  within the project, including when resolved through symlinks. Key files and
  reference inputs must exist. Working/per-run inputs may be future artifacts
  when their parent directory exists. Fence illustrative examples.
- Keep domain facts in one owned context and routing descriptions short. Review
  the actual loaded context size during a fresh walk; individual file sizes do
  not measure the complete task's context cost.

## Optional workflow contract

Add this only when a folder owns a repeatable multi-step procedure. It is an
optional shape, not a required section for every context file:

```markdown
### Workflow: <name>

**Purpose**
<result this procedure produces>

**Inputs**
- Per-run working inputs: <task-specific files or state to inspect or change>
- Stable reference inputs: <read-only source material or configuration>

**Process**
1. <inspect current state>
2. <make the smallest required change>

**Outputs**
<files or state produced>

**Check**
<command or observable condition that confirms the result>

**Stop conditions**
<missing input, conflicting source, or failed check>
```

Illustrative example only — replace paths and commands with verified project
details before using it:

```markdown
### Workflow: Refresh the local API schema

**Purpose**
Regenerate the checked-in schema after an API contract change. Paths below are
relative to the repository root; run the command from that root.

**Inputs**
- Per-run working input: `repo:src/api/schema.json`, the generated target to refresh.
- Stable reference inputs: `repo:src/api/openapi.yaml` and `repo:tools/export_schema.py`.

**Process**
1. Review the OpenAPI change and its callers.
2. Run `python tools/export_schema.py` from the repository root.

**Outputs**
Updated `src/api/schema.json`.

**Check**
Run `python -m unittest tests.test_schema` and inspect the schema diff.

**Stop conditions**
The generator fails, the source contract is ambiguous, or the generated diff
changes unrelated endpoints.
```

Use a workflow contract when the order, inputs, or failure conditions matter
for repeating a task safely. Keep one-off editing guidance in the relevant
context sections instead.
