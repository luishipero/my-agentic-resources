# Validation, fresh navigation, and context quality

## Structural and basic content checks

Use Python 3.10 or newer; the package uses only the standard library. First
follow the installation check in SKILL.md: if a complete package is not
available in a persistent client-recognized location, ask the user to select
user-level or project-level installation. A loaded instruction alone does not
guarantee that its scripts are available. Use the actual directory of the
verified matching package for `<skill-dir>`:

```text
python "<skill-dir>/scripts/setup.py" "<PROJECT_ROOT>"
python "<skill-dir>/scripts/validate.py" "<PROJECT_ROOT>"
python -B -m unittest discover -s "<skill-dir>/tests" -v
```

Setup creates an `AGENTS.md` pointer and `.context-routing/index.md` containing
the folder table. After selection, `--claude-md` creates a missing `CLAUDE.md`
containing only `@AGENTS.md`. Without `CLAUDECODE`, it leaves an existing file
with that import unchanged; otherwise it adds the index pointer and import.
`--copilot-instructions` creates or updates `.github/copilot-instructions.md`.
When `CLAUDECODE` is set, setup adds a Markdown index pointer to an existing
`CLAUDE.md` if missing, without adding an index import. For compatibility,
`CLAUDECODE` without the flag creates a missing `CLAUDE.md` with both imports
and a pointer. The validator accepts a direct index link or `@AGENTS.md`
backed by a valid root pointer. Its matching flags require selected entry
points; otherwise unselected files without a pointer are notes.
When a selected `CLAUDE.md` is a direct symlink to the regular root
`AGENTS.md`, setup leaves the symlink untouched and updates the shared file
through `AGENTS.md` only. Other selected symlinks remain unsupported.
This only concerns setup; test whether the intended agent client follows
symlinked instruction files before relying on them.
Setup does not create `agents.md`. After user selection, `--include-skills`
and `--include-specialists` create optional maps. The helper does not prompt or
overwrite existing files. Existing indexes may need an authorized maintenance
edit to link newly selected maps.

Setup validates the proposed file contents against the project before writing.
Validation errors leave files unchanged and distinguish matching pre-existing
errors from errors introduced by the proposal. Setup checks observed paths again before
publication and reports detected changes; concurrent edits can still race with
filesystem operations. If a write or the final validation fails, setup reports
any files it may have changed. It does not automatically roll back file writes,
because an independent editor may have changed them; review those files manually.
New empty directories are removed where possible. A crash can also leave partial
changes.

GitHub.com Copilot Chat needs the repository attached to use repository-wide
instructions. A Markdown pointer requests navigation but does not guarantee
that the surface will load the linked index. Verify this in the intended
surface; `AGENTS.md` remains the shared entry point for supported agents.

Legacy indexes linked to an `agents.md` folder map remain supported with an
extra-hop note. Nothing is migrated or deleted automatically.

## Legacy migration

Only when migration is explicitly requested, preserve unrelated index content,
transfer the verified folder table and maintenance contract to the index, update
known links, and keep one authoritative folder table. Verify every former route
and inspect references before removing the old map; keep it until external
consumers and unresolved references are accounted for.

The validator checks entry points, table shape, route identities, containment,
supported relative links and optional maps. A linked context cannot be empty
or heading-only. Recognizable unfinished markers such as `<folder path>`,
`<what...>`, `<fill this in>`, `{TODO}`, `[TODO]` and `[TODO: ...]` are errors
outside fenced examples. Generic type parameters, comparisons and ordinary
prose mentioning TODO are not template markers. Standalone markers in inline
code are checked; markers embedded in inline command or route examples are not.

Declared backticked paths in bullet lists under `Key files`, `Inputs`, or
Reference/Required/Working/Per-run/Future-output inputs headings are checked;
standalone bold headings also work. Prefix a path with `./` to resolve it from
the context file's directory, or `repo:` to resolve it from the project root.
For example, `./Makefile` and `repo:src/file with spaces.py` are explicit paths;
`Invoice.total` is not. Declarations must remain inside the project after
resolving symlinks. Key files and reference/required inputs must exist.
Working/per-run/future-output inputs may be absent if their parent exists.
Marked globs, absolute paths and backslashes are invalid; commands and fenced
examples are not executed. Use separate bullets for required/reference and
future working inputs; mixed declarations are conservatively checked as required.

Existing unmarked entries are preserved and reported as unverified notes, not
validated paths. This includes extensionless names such as `Makefile`; it may
also include identifiers. Prefix actual paths when maintaining a context.
URLs, external paths, unmarked globs and command-like examples are skipped.

Inline Markdown links support angle-bracket destinations with spaces. The
parser ignores fenced examples and remote links. Reference-style/HTML/wiki
links, nested destination parentheses and fragment targets are outside its
scope. External capability paths are checked only for local availability;
their definitions are not executed. Cycles are visited once, not rejected.

Size notes are advisory: entry files over about 60 lines or contexts over about
8,000 estimated tokens deserve inspection. Estimates use characters divided
by four, not a model tokenizer. The validator does not measure the complete task
load, prove source claims, run documented commands, detect semantic duplication
or discover all unmapped source folders.

## Fresh navigation walkthrough

For a genuinely small maintenance edit with no consequential behavior or route
change, check affected links and claims against their sources, run the validator,
and report if an independent walk was not performed. Initial setup, routing
redesigns, and consequential changes require the independent walks below.

After structural validation, give a fresh isolated agent the project entry
point, a representative task and acceptance criteria. Supply no chosen route,
project history, author's narrative or earlier verdict. Use the established
delegation policy; context evaluation does not authorize application edits.
For consequential maintenance, walk affected routes and necessary boundaries.
For initial setup or a routing redesign, cover these applicable cases:

1. **Local task:** Start at root `AGENTS.md` or `CLAUDE.md` as appropriate, select a folder directly from
   `index.md`, open its context, identify source evidence and find a concrete
   verification step. Target entry plus at most two additional reads to reach
   the first relevant context; source inspection follows afterward.
2. **Cross-folder task:** Select both contexts, identify the real integration
   boundary, explain what changes affect and do not affect, and find checks
   for both sides.
3. **Workflow-dependent task:** Follow a relevant selected skill or specialist
   map, verify its entry point and explain the check and stop conditions.
   Do not create a route merely to test it; mark this case not applicable when
   no such workflow is needed.

Record actual paths opened in order, the reason for each read, discovered
verification steps and pass/fail evidence in the task report or a requested
artifact. Keep review evidence out of maintained context files. Fail a walk
that scans all contexts to choose a route, opens unrelated contexts, cannot
find required inputs/checks or needs undocumented prior knowledge. Necessary
dependencies are permitted; document justified extra hops for large or legacy
layouts. If isolation is unavailable, report the independent walk as pending.

## Context-quality review

Have the fresh evaluator check the contexts used in the walks:

- **Scope:** Explain the folder's job and useful non-obvious details. Thin
  contexts need no artificial pipeline schema; contracts are for repeatable work.
- **One maintained home:** Shared facts have an owner and links. Routers carry
  short descriptions and destinations, rather than copied domain explanations.
- **Accuracy:** Spot-check important rules, interfaces and commands against
  owning source/tests. Distinguish live behavior from plans/stubs. Cite evidence
  and record material contradictions; a date alone does not establish freshness.
- **Impact:** Verify affected callers/integrations and important boundaries
  against source before claiming something is unaffected.
- **Size:** Estimate the project material actually loaded by each walk, excluding
  system/tool overhead. Investigate loads around 8,000 estimated tokens as a
  starting guideline, not a universal failure threshold. Improve routing or
  shorten owned context before adding navigation documents.

Fix failures and rerun affected checks and walks. Do not call context verified
while an applicable walk or source check is missing. Report unresolved limits,
skipped checks and deferred migration explicitly. A link-validator pass alone
does not establish factual quality.
