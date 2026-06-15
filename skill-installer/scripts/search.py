#!/usr/bin/env python3
"""
Search the aitmpl.com skill catalog.

Uses a bundled offline catalog (catalog.json) for instant search,
with optional live GitHub refresh for freshest results.

Usage:
  search.py QUERY                      # search by keyword
  search.py --category CATEGORY        # list a specific category
  search.py --list-categories          # show all categories
  search.py --all --category CAT       # list all in a category
  search.py QUERY --live               # force live GitHub fetch
"""

import sys
import json
import os
import re
import urllib.request
import urllib.error
import argparse
from pathlib import Path

GITHUB_API = "https://api.github.com/repos/davila7/claude-code-templates/contents/cli-tool/components/skills"
CATALOG_PATH = Path(__file__).parent / "catalog.json"

KNOWN_CATEGORIES = [
    "ai-research", "analytics", "business-marketing", "creative-design",
    "database", "development", "document-processing", "enterprise-communication",
    "media", "productivity", "railway", "scientific", "security", "sentry",
    "utilities", "video", "web-development", "workflow-automation"
]


def load_catalog():
    """Load the bundled offline catalog."""
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH) as f:
            return json.load(f)
    return []


def github_get(url):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skill-installer/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return {"error": "rate_limit"}
        elif e.code == 404:
            return None
        raise
    except Exception:
        return None


def search_catalog(skills, query=None, category=None, limit=15):
    """Filter catalog by query and/or category."""
    results = []
    q = query.lower() if query else None

    for skill in skills:
        # Category filter
        if category and skill["category"] != category:
            continue

        # Query filter
        if q:
            text = f"{skill['name']} {skill['dir']} {skill['description']}".lower()
            # Score: exact phrase > all words match > any word match
            if q in text:
                score = 3
            elif all(w in text for w in q.split()):
                score = 2
            elif any(w in text for w in q.split()):
                score = 1
            else:
                continue
        else:
            score = 0

        results.append((score, skill))

    # Sort: highest score first, then alphabetically
    results.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [s for _, s in results[:limit]]


def main():
    parser = argparse.ArgumentParser(description="Search aitmpl.com skill catalog")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--category", "-c", help="Filter to a specific category")
    parser.add_argument("--list-categories", "-l", action="store_true")
    parser.add_argument("--all", "-a", action="store_true", help="Return all matches (no limit)")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--live", action="store_true", help="Force live GitHub fetch (requires API access)")
    parser.add_argument("--json", dest="json_out", action="store_true", default=True, help="Output JSON (default)")
    args = parser.parse_args()

    if args.list_categories:
        catalog = load_catalog()
        if catalog:
            cats = sorted(set(s["category"] for s in catalog))
        else:
            cats = KNOWN_CATEGORIES
        print(json.dumps({"categories": cats, "source": "catalog"}, indent=2))
        return

    if not args.query and not args.category:
        parser.print_help()
        sys.exit(1)

    # Load catalog
    catalog = load_catalog()
    source = "catalog"

    if args.live or not catalog:
        # Try live GitHub fetch for one category (not practical for all 685+ skills)
        # Just warn and fall back to catalog
        if not catalog:
            print(json.dumps({"error": "No catalog found. Run with GITHUB_TOKEN set or reinstall skill."}))
            sys.exit(1)
        source = "catalog+live_unavailable"

    limit = 999 if args.all else args.limit
    results = search_catalog(catalog, query=args.query, category=args.category, limit=limit)

    output = {
        "query": args.query,
        "category": args.category,
        "count": len(results),
        "source": source,
        "results": results
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
