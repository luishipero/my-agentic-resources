#!/usr/bin/env python3
"""
Install a skill from the aitmpl.com marketplace into .claude/skills or .codex/skills.

Usage:
  install.py CATEGORY/SKILL-NAME               # local .claude/skills/ (default)
  install.py CATEGORY/SKILL-NAME --global       # global ~/.claude/skills/
  install.py CATEGORY/SKILL-NAME --target codex # local .codex/skills/
  install.py CATEGORY/SKILL-NAME --target codex --global
  install.py CATEGORY/SKILL-NAME --dry-run      # list files, no write
"""

import sys
import json
import os
import re
import urllib.request
import urllib.error
import subprocess
import argparse
from pathlib import Path

GITHUB_API = "https://api.github.com/repos/davila7/claude-code-templates/contents/cli-tool/components/skills"
CATALOG_PATH = Path(__file__).parent / "catalog.json"


# ─────────────────────────────────────────────
# GitHub API helpers
# ─────────────────────────────────────────────

def _headers():
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "skill-installer/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def github_get(url):
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return None, "rate_limit"
        if e.code == 404:
            return None, "not_found"
        return None, f"http_{e.code}"
    except Exception as e:
        return None, str(e)


def download_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "skill-installer/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def collect_files_from_github(category, skill_dir):
    """Recursively collect {rel_path: {download_url, executable}} from GitHub."""
    files = {}

    def recurse(api_url, rel=""):
        data, err = github_get(api_url)
        if err:
            return err
        if isinstance(data, dict):
            data = [data]
        for item in data:
            item_rel = f"{rel}/{item['name']}" if rel else item["name"]
            if item["type"] == "file":
                files[item_rel] = {
                    "download_url": item["download_url"],
                    "executable": item["name"].endswith((".py", ".sh")),
                }
            elif item["type"] == "dir":
                recurse(item["url"], item_rel)
        return None

    err = recurse(f"{GITHUB_API}/{category}/{skill_dir}")
    return files, err


# ─────────────────────────────────────────────
# npx fallback
# ─────────────────────────────────────────────

def try_npx_install(category, skill_dir, target_dir):
    """
    Try installing via the official CLI:
      npx claude-code-templates@latest --skill category/skill-dir --yes
    Then move result to target_dir if needed.
    """
    npx = subprocess.run(["which", "npx"], capture_output=True, text=True)
    if npx.returncode != 0:
        return False, "npx not available"

    skill_path = f"{category}/{skill_dir}"
    print(f"  Trying: npx claude-code-templates@latest --skill {skill_path} --yes")
    result = subprocess.run(
        ["npx", "claude-code-templates@latest", "--skill", skill_path, "--yes"],
        capture_output=True, text=True, cwd=str(target_dir.parent.parent)
    )
    if result.returncode == 0:
        return True, result.stdout
    return False, result.stderr or result.stdout


# ─────────────────────────────────────────────
# Catalog helpers
# ─────────────────────────────────────────────

def resolve_skill(skill_input):
    """Return (category, skill_dir). Checks catalog if no / given."""
    if "/" in skill_input:
        parts = skill_input.split("/", 1)
        return parts[0].strip(), parts[1].strip()

    # Search bundled catalog
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH) as f:
            catalog = json.load(f)
        matches = [s for s in catalog if s["dir"] == skill_input or s["name"].lower() == skill_input.lower()]
        if len(matches) == 1:
            return matches[0]["category"], matches[0]["dir"]
        elif len(matches) > 1:
            print(f"Multiple skills match '{skill_input}':")
            for m in matches:
                print(f"  {m['path']}  —  {m['name']}")
            print("Please specify as category/skill-name")
            sys.exit(1)

    print(f"ERROR: Could not find skill '{skill_input}'. Use format: category/skill-name")
    sys.exit(1)


def get_skill_name_from_catalog(category, skill_dir):
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH) as f:
            catalog = json.load(f)
        for s in catalog:
            if s["category"] == category and s["dir"] == skill_dir:
                return s["name"], s["description"]
    return skill_dir, ""


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Install a skill from aitmpl.com")
    parser.add_argument("skill", help='Skill path: "category/skill-name" or just "skill-name"')
    parser.add_argument("--target", choices=["claude", "codex"], default="claude")
    parser.add_argument("--global", "-g", dest="is_global", action="store_true",
                        help="Install to home dir (~/.claude or ~/.codex)")
    parser.add_argument("--dry-run", action="store_true", help="Show files without writing")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite without prompting")
    parser.add_argument("--cwd", default=os.getcwd())
    args = parser.parse_args()

    # Resolve skill
    category, skill_dir = resolve_skill(args.skill)
    skill_name, skill_desc = get_skill_name_from_catalog(category, skill_dir)

    # Resolve install dir
    base = Path.home() if args.is_global else Path(args.cwd)
    skills_dir = base / (f".{args.target}") / "skills"
    install_dir = skills_dir / skill_dir
    scope = "global" if args.is_global else "local"

    print(f"\n📦  {skill_name}")
    if skill_desc:
        print(f"    {skill_desc[:100]}")
    print(f"\n🔧  Target : {args.target} ({scope})")
    print(f"📁  Path   : {install_dir}")

    if args.dry_run:
        print("\n[Dry run] Would download from:")
        print(f"  https://github.com/davila7/claude-code-templates/tree/main/cli-tool/components/skills/{category}/{skill_dir}")
        print("\nFiles would be written to:", install_dir)
        return

    # Check existing
    if install_dir.exists() and list(install_dir.iterdir()) and not args.overwrite:
        print(f"\n⚠️  Already installed at {install_dir}")
        resp = input("Overwrite? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            sys.exit(0)

    # Download from GitHub API
    print(f"\n⬇️  Downloading from GitHub...")
    files, err = collect_files_from_github(category, skill_dir)

    if err == "rate_limit":
        print("⚠️  GitHub API rate limited. Trying npx fallback...")
        ok, msg = try_npx_install(category, skill_dir, install_dir)
        if ok:
            # npx installs to .claude/skills/ in cwd; move if target is codex or global
            npx_src = Path(args.cwd) / ".claude" / "skills" / skill_dir
            if args.target == "codex" or args.is_global:
                if npx_src.exists():
                    import shutil
                    install_dir.parent.mkdir(parents=True, exist_ok=True)
                    if install_dir.exists():
                        shutil.rmtree(install_dir)
                    shutil.copytree(str(npx_src), str(install_dir))
                    if args.target == "codex":
                        shutil.rmtree(str(npx_src))
            print(f"✅ Installed via npx to {install_dir}")
            print(f"\nTip: Set GITHUB_TOKEN env var for direct installs without npx.")
            return
        else:
            print(f"❌ npx fallback also failed: {msg}")
            print("\nFix: Set GITHUB_TOKEN env var:")
            print("  export GITHUB_TOKEN=ghp_yourtoken")
            sys.exit(1)

    if err == "not_found" or not files:
        print(f"❌ Skill '{category}/{skill_dir}' not found on GitHub.")
        print(f"   Browse skills at: https://www.aitmpl.com/skills/")
        sys.exit(1)

    if err:
        print(f"❌ GitHub error: {err}")
        sys.exit(1)

    if "SKILL.md" not in files:
        print(f"❌ SKILL.md missing in '{category}/{skill_dir}' — not a valid skill directory.")
        sys.exit(1)

    # Write files
    print(f"   {len(files)} file(s) found\n")
    install_dir.mkdir(parents=True, exist_ok=True)
    success, failed = 0, 0

    for rel_path, meta in sorted(files.items()):
        dest = install_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = download_text(meta["download_url"])
            dest.write_text(content, encoding="utf-8")
            if meta["executable"]:
                dest.chmod(0o755)
            print(f"  ✓ {rel_path}")
            success += 1
        except Exception as e:
            print(f"  ✗ {rel_path}: {e}", file=sys.stderr)
            failed += 1

    print(f"\n{'✅' if not failed else '⚠️ '} Installed {success}/{success+failed} files")
    print(f"📁 {install_dir}")

    tool_label = "Claude Code" if args.target == "claude" else "Codex"
    print(f"\n💡 '{skill_name}' is now available in {tool_label}.")
    if not args.is_global:
        print(f"   Active in this directory only. Use --global to install system-wide.")

    print(json.dumps({
        "status": "success" if not failed else "partial",
        "skill": skill_name,
        "path": f"{category}/{skill_dir}",
        "installed_to": str(install_dir),
        "files_ok": success,
        "files_failed": failed,
        "target": args.target,
        "scope": scope,
    }))


if __name__ == "__main__":
    main()
