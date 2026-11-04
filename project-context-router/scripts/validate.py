"""Read-only checks for the project-context-router files.

This intentionally supports inline Markdown links and simple pipe tables only;
reference links, nested parentheses in destinations, and full Markdown semantics
are outside the parser. Fenced code blocks are ignored.
"""
from __future__ import annotations

import argparse
import re
import sys
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_RE = re.compile(r"\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+['\"][^)]*['\"])?\)")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
ABSOLUTE_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/|~(?:[\\/]|$))")


def _active_text(text: str) -> str:
    """Drop fenced examples; preserve line numbers for diagnostics."""
    lines = text.splitlines()
    active: list[str] = []
    fence_char, fence_size = "", 0
    for line in lines:
        match = FENCE_RE.match(line)
        if not fence_char and match:
            fence_char, fence_size = match.group(1)[0], len(match.group(1))
            active.append("")
        elif fence_char:
            close = re.match(r"^\s{0,3}" + re.escape(fence_char) + r"{" + str(fence_size) + r",}\s*$", line)
            if close:
                fence_char = ""
            active.append("")
        else:
            active.append(line)
    return "\n".join(active)


def _destination(raw: str) -> str:
    return unquote(raw.strip().split("#", 1)[0].split("?", 1)[0])


def _links(text: str):
    for line_number, line in enumerate(_active_text(text).splitlines(), 1):
        # Remove inline code spans so examples are not treated as active links.
        line = re.sub(r"(`+).*?\1", "", line)
        for match in LINK_RE.finditer(line):
            raw = match.group(1) or match.group(2) or ""
            dest = _destination(raw)
            if not dest or dest.startswith("//") or re.match(r"^[a-z][a-z0-9+.-]*:", dest, re.I):
                continue
            yield line_number, dest


def _table_cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _table_rows(lines: list[str], expected: list[str], source: str, errors: list[str]):
    normalized = [x.casefold() for x in expected]
    matches = [i for i, line in enumerate(lines[:-1])
               if [re.sub(r"\\?\*", "", c).strip().casefold() for c in _table_cells(line)] == normalized]
    if len(matches) > 1:
        errors.append(f"{source}: found {len(matches)} tables with the same route columns; keep one catalog table")
    for i, line in enumerate(lines[:-1]):
        cells = _table_cells(line)
        if [re.sub(r"\\?\*", "", c).strip().casefold() for c in cells] != normalized:
            continue
        separator = _table_cells(lines[i + 1])
        if len(separator) != len(expected) or not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in separator):
            errors.append(f"{source}:{i + 2}: expected a Markdown table separator after {' | '.join(expected)}")
            return [], i + 2
        rows = []
        j = i + 2
        while j < len(lines) and lines[j].strip() and not lines[j].lstrip().startswith("#"):
            if "|" not in lines[j]:
                errors.append(f"{source}:{j + 1}: malformed table row; expected pipe-separated cells")
                j += 1
                continue
            row = _table_cells(lines[j])
            if len(row) != len(expected):
                errors.append(f"{source}:{j + 1}: expected {len(expected)} table cells, found {len(row)}")
            else:
                rows.append((j + 1, row))
            j += 1
        return rows, i + 2
    errors.append(f"{source}: missing table with columns {' | '.join(expected)}")
    return [], None


def _cell_link(cell: str) -> str | None:
    match = LINK_RE.search(cell)
    if not match:
        return None
    return match.group(1) or match.group(2)


def _local_path(root: Path, source: Path, dest: str) -> Path | None:
    if ABSOLUTE_RE.match(dest):
        return None
    return (source.parent / dest).resolve()


def has_link(text: str, source: Path, target: Path) -> bool:
    """Return whether active inline Markdown links resolve to target."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*\Z", "", text, flags=re.DOTALL)
    return any(_relative_target(source, dest, target) for _, dest in _links(text))


def has_agents_import(text: str) -> bool:
    active = _active_text(text)
    active = re.sub(r"<!--.*?-->", "", active, flags=re.DOTALL)
    active = re.sub(r"<!--.*\Z", "", active, flags=re.DOTALL)
    return bool(re.search(r"(?m)^@AGENTS\.md[ \t]*$", active))


def _relative_target(source: Path, dest: str, target: Path) -> bool:
    if ABSOLUTE_RE.match(dest) or dest.startswith("//"):
        return False
    return (source.parent / dest).resolve() == target.resolve()


# Deliberately recognize only explicit template instructions, not arbitrary angle-bracket values.
PLACEHOLDER_RE = re.compile(
    r"(?<![\w])<(?:folder path|fill this in|1-2 sentences\b[^>]*|what\s+[^>]+|role(?:, [^>]*)?|"
    r"why it exists\b[^>]*|product/business role\b[^>]*|how data or control\b[^>]*|"
    r"non-obvious decision\b[^>]*|tests, source locations\b[^>]*|who uses this area\b[^>]*|"
    r"behavior, data, or responsibilities\b[^>]*|command|contradiction between sources\b[^>]*|"
    r"traps, required ordering\b[^>]*|why it's related|name|result this procedure produces|"
    r"task-specific files or state\b[^>]*|read-only source material\b[^>]*|inspect current state|"
    r"make the smallest required change|files or state produced|command or observable condition\b[^>]*|"
    r"missing input, conflicting source\b[^>]*)>|\{TODO\}|\[TODO(?::[^\]]*)?\]", re.I | re.DOTALL
)


HEADING_RE = re.compile(r"^\s*(?:(#{1,6})\s+(.+?)\s*#*|\*\*(.+?)\*\*\s*:?)\s*$")


def _check_context(root: Path, source: Path, text: str, errors: list[str], notes: list[str], exists, is_dir) -> None:
    name = source.relative_to(root).as_posix()
    active = _active_text(text)
    if not any(line.strip() and not HEADING_RE.match(line) for line in active.splitlines()):
        errors.append(f"{name}: context is empty or heading-only")
    # Keep standalone template markers in code spans; ignore markers embedded in examples.
    marker_text = re.sub(
        r"(`+)(.+?)\1",
        lambda match: match.group(0) if PLACEHOLDER_RE.fullmatch(match.group(2).strip()) else " " * len(match.group(0)),
        active,
    )
    for match in PLACEHOLDER_RE.finditer(marker_text):
        line_no = active.count("\n", 0, match.start()) + 1
        errors.append(f"{name}:{line_no}: unfinished template marker")
    estimate = len(text) // 4
    if estimate >= 8000:
        notes.append(f"{name}: large context, approximately {estimate} tokens (characters / 4)")

    section = ""
    section_level = 0
    subsection = ""
    subsection_level = 0
    roots = ("key files", "inputs", "reference inputs", "required inputs", "working inputs", "per-run inputs", "future-output inputs")
    for line_no, line in enumerate(active.splitlines(), 1):
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1)) if heading.group(1) else 7
            title = (heading.group(2) or heading.group(3)).strip().rstrip(":").casefold()
            if title in roots:
                section, section_level, subsection, subsection_level = title, level, "", 0
            elif section == "inputs" and (level > section_level or not heading.group(1)) and title in ("reference", "required", "reference files", "required files", "working", "per-run", "future-output"):
                subsection, subsection_level = title, level
            elif level <= section_level or not heading.group(1):
                section, subsection, subsection_level = "", "", 0
            elif subsection and level <= subsection_level:
                subsection, subsection_level = "", 0
            continue
        if not (section in roots and re.match(r"^\s*[-*+]\s+", line)):
            continue
        prefix = line.split("`", 1)[0]
        explicit_working = bool(re.match(r"^\s*[-*+]\s*(?:(?:per-run|future-output|working)\s+)*(?:working|per-run|future-output)(?:\s+inputs?)?\s*:", prefix, re.I))
        required_label = bool(re.search(r"\b(?:reference|required)(?:\s+inputs?)?\s*:", line, re.I))
        optional = section not in ("key files", "reference inputs", "required inputs") and subsection not in ("reference", "required", "reference files", "required files") and not required_label and (
            section in ("working inputs", "per-run inputs", "future-output inputs")
            or subsection in ("working", "per-run", "future-output") or explicit_working
        )
        for value in re.findall(r"`([^`]+)`", line):
            value = value.strip()
            if value.startswith("./"):
                base, relative = source.parent, value[2:]
            elif value.startswith("repo:"):
                base, relative = root, value[5:]
            else:
                if (not ABSOLUTE_RE.match(value)
                        and not re.match(r"[a-z][a-z0-9+.-]*://", value, re.I)
                        and not any(c in value for c in "*?{}<>|;\n")
                        and not re.match(r"(?:python(?:3)?|node|npm|npx|git|pip|pytest|make|bash|sh|pwsh|powershell)\s", value, re.I)
                        and not re.search(r"\s+--?\w", value)):
                    notes.append(f"{name}:{line_no}: unverified unmarked entry: {value}; use ./ or repo: to declare a path")
                continue
            if (not relative or ABSOLUTE_RE.match(relative) or "\\" in relative
                    or any(c in relative for c in "*?{}<>|;\n")):
                errors.append(f"{name}:{line_no}: invalid declared path: {value}")
                continue
            path = (base / relative).resolve()
            if not path.is_relative_to(root):
                errors.append(f"{name}:{line_no}: declared path escapes project root: {value}")
            elif not exists(path) and not (optional and is_dir(path.parent)):
                errors.append(f"{name}:{line_no}: missing declared {'working input parent' if optional else 'path'}: {value}")


def validate(
    root: Path, *, require_claude: bool = False, require_copilot: bool = False,
    proposed: dict[Path, bytes] | None = None, observe=None,
) -> tuple[list[str], list[str]]:
    root = Path(root).resolve()
    proposed = {Path(path).resolve(): data for path, data in (proposed or {}).items()}
    def inspect(path):
        if observe:
            observe(path)
    def exists(path):
        inspect(path)
        return path.resolve() in proposed or path.exists()
    def is_file(path):
        inspect(path)
        return path.resolve() in proposed or path.is_file()
    def is_dir(path):
        inspect(path)
        return path.is_dir() or any(path.resolve() in target.parents for target in proposed)
    def read_text(path):
        inspect(path)
        data = proposed.get(path.resolve())
        return data.decode("utf-8-sig") if data is not None else path.read_text(encoding="utf-8-sig")
    errors: list[str] = []
    notes: list[str] = []
    if not root.is_dir():
        return [f"Project root is not a directory: {root}"], notes

    root_agents = root / "AGENTS.md"
    root_claude = root / "CLAUDE.md"
    root_copilot = root / ".github" / "copilot-instructions.md"
    root_entries = [root_agents]
    routing = root / ".context-routing"
    index = routing / "index.md"
    agents = routing / "agents.md"
    skills = routing / "skills.md"
    specialists = routing / "specialists.md"
    required = [index]
    if not exists(root_agents) and not exists(root_claude):
        errors.append("Missing root routing entry: AGENTS.md or CLAUDE.md")
    optional = [skills, specialists]
    legacy = [agents]
    texts: dict[Path, str] = {}
    for path in required:
        if not is_file(path):
            errors.append(f"Missing required routing file: {path.relative_to(root).as_posix()}")
        else:
            try:
                texts[path] = read_text(path)
            except (OSError, UnicodeError) as exc:
                errors.append(f"Cannot read {path.relative_to(root).as_posix()}: {exc}")

    for path in root_entries + optional + legacy:
        if exists(path):
            if not is_file(path):
                errors.append(f"Optional routing path is not a file: {path.relative_to(root).as_posix()}")
            else:
                try:
                    texts[path] = read_text(path)
                except (OSError, UnicodeError) as exc:
                    errors.append(f"Cannot read {path.relative_to(root).as_posix()}: {exc}")

    for entry, required_entry in (
        (root_claude, require_claude or (not exists(root_agents) and exists(root_claude))),
        (root_copilot, require_copilot),
    ):
        name = entry.relative_to(root).as_posix()
        if not is_file(entry):
            if required_entry:
                errors.append(f"Missing required routing entry: {name}")
            continue
        try:
            text = read_text(entry)
        except (OSError, UnicodeError) as exc:
            (errors if required_entry else notes).append(f"Cannot read {name}: {exc}")
            continue
        if required_entry or has_link(text, entry, index) or (entry == root_claude and has_agents_import(text)):
            root_entries.append(entry)
            texts[entry] = text
        else:
            notes.append(f"{name}: no routing pointer; entry not selected")

    for entry in root_entries:
        if entry == root_claude and entry in texts and has_agents_import(texts[entry]):
            if root_agents not in texts:
                errors.append("CLAUDE.md: @AGENTS.md requires a readable root AGENTS.md")
            elif not has_link(texts[root_agents], root_agents, index):
                errors.append("CLAUDE.md: imported AGENTS.md must link to .context-routing/index.md")
        elif entry in texts and not has_link(texts[entry], entry, index):
            errors.append(f"{entry.relative_to(root).as_posix()}: must link to .context-routing/index.md")
    if index in texts:
        for name, target in ((p.name, p) for p in optional if exists(p)):
            if not has_link(texts[index], index, target):
                errors.append(f".context-routing/index.md: must link to {name}")

    # Validate links in the routing entry files, then follow only linked CONTEXT.md files.
    queue = [p for p in required + root_entries + optional + legacy if p in texts and p != root_copilot and (p != agents or (index in texts and has_link(texts[index], index, agents)))]
    seen = set(queue)
    while queue:
        source = queue.pop(0)
        for line_no, dest in _links(texts[source]):
            parsed = urlsplit(dest)
            if parsed.scheme or dest.startswith("//"):
                continue
            target = _local_path(root, source, dest)
            if target is None:
                errors.append(f"{source.relative_to(root).as_posix()}:{line_no}: local Markdown links must be relative: {dest}")
                continue
            try:
                target.relative_to(root)
            except ValueError:
                errors.append(f"{source.relative_to(root).as_posix()}:{line_no}: link escapes project root: {dest}")
                continue
            if not exists(target):
                errors.append(f"{source.relative_to(root).as_posix()}:{line_no}: missing link destination: {dest}")
                continue
            if target.name.casefold() == "context.md" and is_file(target) and target not in seen:
                try:
                    texts[target] = read_text(target)
                    seen.add(target)
                    queue.append(target)
                except (OSError, UnicodeError) as exc:
                    errors.append(f"Cannot read {target.relative_to(root).as_posix()}: {exc}")

    for source, text in texts.items():
        if source.name.casefold() == "context.md":
            _check_context(root, source, text, errors, notes, exists, is_dir)
    for source in (*root_entries, index):
        if source in texts and len(texts[source].splitlines()) > 60:
            notes.append(f"{source.relative_to(root).as_posix()}: large entry ({len(texts[source].splitlines())} lines; guideline is about 60)")

    # The index owns the folder map; linked legacy maps are a fallback only.
    columns = ["Folder", "What's there", "Context file"]
    def has_folder_table(path):
        return path in texts and any(
            [re.sub(r"\\?\*", "", c).strip().casefold() for c in _table_cells(line)]
            == [c.casefold() for c in columns]
            for line in _active_text(texts[path]).splitlines()
        )

    index_map = has_folder_table(index)
    legacy_link = index in texts and has_link(texts[index], index, agents)
    if index_map and has_folder_table(agents):
        message = "Both index.md and agents.md contain folder maps; choose one and update routing manually"
        (errors if legacy_link else notes).append(message)
    route_map = index if index_map or not legacy_link else agents
    if route_map == agents:
        notes.append("Legacy folder map: index.md adds an extra hop through agents.md; migrate manually if desired")
    for map_path in dict.fromkeys((index, route_map)):
        if map_path not in texts:
            continue
        map_name = map_path.relative_to(root).as_posix()
        lines = _active_text(texts[map_path]).splitlines()
        in_table = False
        for i, line in enumerate(lines):
            if not line.strip() or line.lstrip().startswith("#"):
                in_table = False
                continue
            if in_table and "|" not in line:
                in_table = False
            if i + 1 < len(lines) and "|" in line:
                separator = _table_cells(lines[i + 1])
                if len(separator) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator):
                    in_table = True
            if not in_table and line.count("|") >= 2:
                if any(Path(dest).name.casefold() == "context.md" for _, dest in _links(line)):
                    errors.append(f"{map_name}:{i + 1}: folder route row is outside a table")
    if route_map in texts:
        map_name = route_map.relative_to(root).as_posix()
        lines = _active_text(texts[route_map]).splitlines()
        rows, _ = _table_rows(lines, columns, map_name, errors)
        folders: set[str] = set()
        if not rows:
            notes.append(f"{map_name}: empty folder route catalog")
        for line_no, row in rows:
            folder_label = row[0].strip().strip("`")
            route_path = re.sub(r"^`|`$", "", row[0]).replace("\\", "/").rstrip("/") or "."
            if not folder_label:
                errors.append(f"{map_name}:{line_no}: empty folder route")
            folder_path = (root / route_path).resolve()
            if not folder_path.is_relative_to(root):
                errors.append(f"{map_name}:{line_no}: folder route escapes project root: {row[0]}")
            elif not is_dir(folder_path):
                errors.append(f"{map_name}:{line_no}: missing routed folder: {row[0]}")
            else:
                folder_identity = os.path.normcase(str(folder_path))
                if folder_identity in folders:
                    errors.append(f"{map_name}:{line_no}: duplicate folder route: {row[0]}")
                folders.add(folder_identity)
            if not row[1].strip():
                errors.append(f"{map_name}:{line_no}: empty folder description")
            link = _cell_link(row[2])
            if not link:
                errors.append(f"{map_name}:{line_no}: Context file must be a relative Markdown link")
            elif ABSOLUTE_RE.match(link) or link.startswith("//") or re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I):
                errors.append(f"{map_name}:{line_no}: Context file link must be relative")
            else:
                path = (route_map.parent / _destination(link)).resolve()
                if not path.is_relative_to(root):
                    errors.append(f"{map_name}:{line_no}: context link escapes project root: {link}")
                elif path.name.casefold() != "context.md":
                    errors.append(f"{map_name}:{line_no}: route must point to CONTEXT.md: {link}")
                elif not is_file(path):
                    errors.append(f"{map_name}:{line_no}: context route must point to an existing file: {link}")
                elif is_dir(folder_path) and path.parent.resolve() != folder_path:
                    errors.append(f"{map_name}:{line_no}: context file must be inside its routed folder: {link}")

    for route_map, kind, column in ((skills, "skill", "Skill"), (specialists, "specialist", "Specialist")):
        if route_map not in texts:
            continue
        lines = _active_text(texts[route_map]).splitlines()
        rows, _ = _table_rows(lines, ["When to use", column, "Entry point"], f".context-routing/{route_map.name}", errors)
        identities: set[str] = set()
        if not rows:
            notes.append(f".context-routing/{route_map.name}: empty {kind} route catalog")
        for line_no, row in rows:
            identity = re.sub(r"^`|`$", "", row[1]).strip().casefold()
            if not identity:
                errors.append(f".context-routing/{route_map.name}:{line_no}: empty {kind} route identity")
            elif identity in identities:
                errors.append(f".context-routing/{route_map.name}:{line_no}: duplicate {kind} route: {row[1]}")
            identities.add(identity)
            if not row[0].strip():
                errors.append(f".context-routing/{route_map.name}:{line_no}: empty task description")
            link = _cell_link(row[2])
            if link:
                if ABSOLUTE_RE.match(link) or link.startswith("//") or re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I):
                    errors.append(f".context-routing/{route_map.name}:{line_no}: local {kind} links must be relative; use a backticked absolute path for external {kind} entries")
                    continue
                path = (route_map.parent / _destination(link)).resolve()
                if not path.is_relative_to(root):
                    errors.append(f".context-routing/{route_map.name}:{line_no}: local {kind} link escapes project root: {link}")
                elif not is_file(path):
                    errors.append(f".context-routing/{route_map.name}:{line_no}: missing local {kind}: {link}")
                continue

            external = re.search(r"`([^`]+)`", row[2])
            if not external or not ABSOLUTE_RE.match(external.group(1).strip()):
                errors.append(f".context-routing/{route_map.name}:{line_no}: Entry point must be a relative Markdown link or backticked absolute/~ path")
                continue
            location = external.group(1).strip()
            if not re.search(r"machine-specific|this machine|machine specific", row[2], re.I):
                errors.append(f".context-routing/{route_map.name}:{line_no}: external {kind} location needs a machine-specific note")
            if location.startswith("~"):
                try:
                    candidate = Path(location).expanduser()
                except (RuntimeError, OSError):
                    candidate = None
                note_label = f"external {kind} location {location}"
            elif location.startswith("/"):
                candidate = None if sys.platform == "win32" else Path(location)
                note_label = f"external {kind} location {location}"
            elif re.match(r"^[A-Za-z]:[\\/]", location) or location.startswith("\\\\"):
                if sys.platform == "win32":
                    candidate = Path(location)
                    note_label = f"external {kind} location {location}"
                else:
                    candidate = None
                    note_label = f"external {kind} location {location}"
            else:
                candidate = None
                note_label = f"external {kind} location {location}"
            if candidate is None:
                notes.append(f"{note_label}: unsupported on this machine; verification unavailable")
            elif candidate.exists():
                notes.append(f"{note_label}: exists")
            else:
                notes.append(f"{note_label}: missing")
    return errors, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate project context-routing files.")
    parser.add_argument("PROJECT_ROOT", type=Path)
    parser.add_argument("--claude-md", action="store_true", help="require a CLAUDE.md routing pointer")
    parser.add_argument("--copilot-instructions", action="store_true", help="require a Copilot instructions routing pointer")
    args = parser.parse_args(argv)
    errors, notes = validate(args.PROJECT_ROOT, require_claude=args.claude_md, require_copilot=args.copilot_instructions)
    for error in errors:
        print(f"ERROR: {error}")
    for note in notes:
        print(f"NOTE: {note}")
    if not errors:
        print("Validation passed" if not notes else "Validation passed with notes")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
