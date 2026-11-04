# Optional architecture overview

Ask once whether the user wants a root `ARCHITECTURE.md`, explaining that it
offers a concise, evidence-based picture of the system's major components,
boundaries, and data flow. A direct request to create or use it is selection.
An existing file alone does not establish a new decision: inspect it, preserve
its content, and ask whether to adopt it and update it when appropriate. Do not
create, rewrite, or link it for routing until selected. While a decision is
pending, continue independent context and routing work.

Record the user's decision in `.context-routing/index.md`: link the selected
overview as `[Architecture overview](../ARCHITECTURE.md)`; for a decline, add
`Architecture overview: declined`. Preserve prior decisions on maintenance and
do not ask again unless the user changes the choice. If an index already links
the selected overview or records a prior decline, that is the recorded decision.
Keep the overview outside the folder-to-context table; the table remains one
row per folder context.

When selected, tailor the overview to the project and verify important claims
against its sources. Use only relevant, supported items from this menu:

- A short orientation to major project areas and a simple diagram or text flow.
- Main components, their responsibilities, technologies, and boundaries.
- Important data stores, state ownership, integrations, and data movement.
- Deployment, infrastructure, operational and security boundaries, where known.
- Links to development, testing, and existing context or operating guidance.
- Clearly labeled planned work, architecture debt, project identification, or
  glossary entries when they help readers and have evidence.

Do not copy an exhaustive directory tree, repeat material already owned by
context files, invent services or future plans, or include credentials. Link to
the authoritative detail instead. Distinguish observed behavior from planned or
unverified information, record meaningful uncertainty, and avoid placeholders.
Maintain an adopted overview when an authorized change affects its meaning;
otherwise leave it untouched. Preserve unrelated existing guidance.
