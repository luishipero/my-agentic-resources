---
name: ship
description: Ship the current work. Use when the user runs /ship or asks to ship, release, or deploy. Runs npm audit fix, npm run test, git commit, and git push in sequence.
---

# Ship

Run the full shipping pipeline for the current project using the Haiku model:

## Steps

1. **Dependency audit** — Run `npm audit fix` to patch known vulnerabilities. Do not continue if there is any high or critical unsolved vulnerability.
2. **Tests** — Run `npm run test:unit` (unit + integration via vitest). If tests fail, stop and report — do not commit or push.
3. **Build** — Run `npm run build` to verify production build succeeds. If build fails, stop and report — do not commit or push.
4. **Git commit** — Stage all changes (`git add -A`, excluding files in .gitignore) and create a commit. Check `git diff`, write a meaningful message, include Co-Authored-By trailer.
5. Do a `git pull` and confirm you're up to date with remote. If not up to date, update local branch.
6. **Git push** — Push to the current branch's upstream (`git push`).

## Rules

- If `npm audit fix` produces breaking changes (changes to package.json that affect imports), report them and ask before continuing.
- If tests fail, stop immediately. Do not commit or push.
- Never use `--no-verify` or force push.
- Always show `git log --oneline -3` after a successful push so the user can confirm.
