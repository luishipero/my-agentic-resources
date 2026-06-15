# My Agentic Resources

Personal collection of reusable agent skills, design references, workflow helpers, and development utilities. The repository is organized as self-contained skill folders; each folder has a `SKILL.md` plus any supporting scripts, data, references, or assets.

## Resource Catalog

| Resource | Best for | Includes |
| --- | --- | --- |
| [react-best-practices](./react-best-practices) | React and Next.js performance work | Optimization rules for waterfalls, bundles, rendering, caching, and JavaScript performance. |
| [ui-ux-pro-max](./ui-ux-pro-max) | UI/UX research and design-system direction | Searchable CSV data for products, styles, colors, typography, charts, UX guidance, and stack-specific patterns. |
| [frontend-design](./frontend-design) | High-quality frontend visual design | A focused design skill for creating distinctive pages, components, dashboards, and application UI. |
| [impeccable](./impeccable) | UI shaping, critique, polish, and live iteration | Command references and scripts for design review, browser iteration, typography, layout, motion, and hardening. |
| [senior-frontend](./senior-frontend) | Frontend implementation support | Component generation, bundle analysis, scaffolding, and reference docs for React and Next.js workflows. |
| [ui-design-system](./ui-design-system) | Design-system setup and maintenance | Design token generation plus guidance for scalable component and handoff systems. |
| [canvas-design](./canvas-design) | Static visual design and typography-heavy assets | Canvas design guidance, bundled fonts, and font license files. |
| [senior-security](./senior-security) | Security engineering and review | Threat modeling, security auditing, pentest automation, and security architecture references. |
| [skill-installer](./skill-installer) | Finding and installing external skills | Marketplace catalog search and install scripts for Claude Code and Codex skill folders. |
| [ship](./ship) | Shipping npm project work | A guarded release checklist covering audit, test, build, commit, pull, and push. |

## Common Workflows

- Frontend performance review: start with `react-best-practices`, then use `senior-frontend` when implementation or tooling support is needed.
- New UI or redesign work: use `ui-ux-pro-max` for direction, then `frontend-design` or `impeccable` for craft and iteration.
- Design systems: use `ui-design-system` for token and system structure, with `canvas-design` when the output is visual or typography-heavy.
- Security work: use `senior-security` for threat modeling, audits, or penetration-testing workflows.
- Skill management: use `skill-installer` when searching for or installing skills from the aitmpl.com marketplace.
- Release flow: use `ship` when the current npm project is ready for audit, tests, build, commit, and push.

## Usage

Open the relevant folder and read its `SKILL.md` first. Supporting files are kept next to the skill:

- `scripts/` for runnable helpers.
- `references/` or `reference/` for detailed guidance.
- `data/` for searchable datasets.
- asset folders such as `canvas-fonts/` for bundled resources.

Example helper commands:

```bash
python senior-frontend/scripts/bundle_analyzer.py <target-path>
python senior-security/scripts/security_auditor.py <target-path>
python ui-design-system/scripts/design_token_generator.py <brand_color> <style> <format>
python ui-ux-pro-max/scripts/search.py "saas dashboard analytics" --design-system
```

## License

Some resources include their own license files, especially `frontend-design` and `canvas-design`. Check each folder before redistributing.

**Last updated:** 2026-06-16
