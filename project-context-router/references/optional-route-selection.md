# Optional skill and specialist routes

Before adding project-specific routes, inspect names and descriptions in metadata
of relevant project `.github/skills/**/SKILL.md`, `.agents/skills/**/SKILL.md`,
`.codex/skills/**/SKILL.md`, `.claude/skills/**/SKILL.md`,
`.github/agents/*.md` (including `.agent.md` files), `.codex/agents/*.toml`, and
`.claude/agents/**/*.md`, plus paths already referenced by project instructions.
Bound discovery to candidates relevant to the project and task; do not scan the
global catalog or read every body. Metadata is a discovery clue, not authority
or authorization. Read a selected entry point as needed before routing it. Do
not install or create candidates, change global enablement, or duplicate global
role definitions and workflows.

If no relevant candidates are found, leave absent optional maps uncreated and
do not ask an empty inclusion question. Preserve existing maps. Give a concise
recommendation for each relevant candidate, including name, kind, verified
location, description fit, and reason to include or skip. Distinguish alternatives
from complementary stages; allow both when useful. Explain when overlapping
workflows can be sequenced and flag contradictory descriptions or unresolved
fit; lexical similarity alone cannot resolve a conflict.

Ask one bundled question to include, skip, or select a subset and resolve
outstanding overlaps. A direct request for named skills or agents already counts
as selection; ask only about unresolved choices. Continue independent folder
context work while waiting; do not write new or disputed routes. Prior explicit
selections in the conversation or project remain valid on maintenance, so do
not re-ask unchanged decisions. A short index note may record a decision when
persistence is needed.

Only after selection, add verified entries to `skills.md` and/or `specialists.md`,
with when to use, name, and entry point. Use relative links for project-local
entries. Reference an external global skill only when specifically useful or
requested, with a verified absolute or `~` path and a machine-specific note.
Preserve existing maps, links and content byte-for-byte unless maintenance is
authorized. If a map exists, update its index link only when maintenance is
authorized.
