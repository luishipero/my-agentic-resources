"""Create the project context-routing entry points without overwriting files."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "references" / "routing-table-template.md"
SECTIONS = {
    "Root AGENTS.md": Path("AGENTS.md"),
    "Root CLAUDE.md": Path("CLAUDE.md"),
    ".github/copilot-instructions.md": Path(".github/copilot-instructions.md"),
    ".context-routing/index.md": Path(".context-routing/index.md"),
    ".context-routing/skills.md": Path(".context-routing/skills.md"),
    ".context-routing/specialists.md": Path(".context-routing/specialists.md"),
}


class SetupError(Exception):
    pass


def _read_templates() -> dict[Path, bytes]:
    try:
        source = TEMPLATE.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError(f"Cannot read routing templates at {TEMPLATE}: {exc}") from exc

    result = {}
    for heading, destination in SECTIONS.items():
        matches = list(
            re.finditer(
                rf"^## {re.escape(heading)}\s*$\n```markdown\s*\n(.*?)^```\s*$",
                source,
                re.MULTILINE | re.DOTALL,
            )
        )
        if len(matches) != 1:
            raise SetupError(
                f"Expected exactly one fenced template under '## {heading}' in {TEMPLATE}; found {len(matches)}."
            )
        result[destination] = matches[0].group(1).encode("utf-8")
    return result


def _existing_case_path(root: Path, relative: Path) -> Path | None:
    """Return a case-insensitive existing path, detecting aliases on every component."""
    current = root
    for part in relative.parts:
        try:
            names = [entry.name for entry in current.iterdir()]
        except OSError as exc:
            raise SetupError(f"Cannot inspect target directory {current}: {exc}") from exc
        matches = [name for name in names if name.casefold() == part.casefold()]
        if len(matches) > 1:
            raise SetupError(f"Case-colliding paths in {current}: {', '.join(matches)}")
        if not matches:
            return None
        current = current / matches[0]
        if matches[0] != part:
            raise SetupError(
                f"Case-colliding target path: expected {root / relative}, found {current}."
            )
    return current


def _preflight(root: Path, targets: dict[Path, bytes]) -> dict[Path, Path | None]:
    existing = {}
    for relative in targets:
        found = _existing_case_path(root, relative)
        existing[relative] = found
        current = root
        for part in relative.parts:
            current = current / part
            if current.exists() or _is_link(current):
                if _is_link(current):
                    if relative == Path("CLAUDE.md") and current.is_symlink():
                        target = os.readlink(current)
                        if (
                            target in ("AGENTS.md", "./AGENTS.md")
                            and not _is_link(root / "AGENTS.md")
                            and (root / "AGENTS.md").is_file()
                        ):
                            continue
                    raise SetupError(f"Refusing to write through symlink or reparse point: {current}")
                if current != root / relative and not current.is_dir():
                    raise SetupError(f"Expected a directory at {current}, found a file.")
        if found is not None and not found.is_file():
            raise SetupError(f"Expected a file at {found}.")
    return existing


def _is_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(
        reparse_point and getattr(info, "st_file_attributes", 0) & reparse_point
    )


def _pointer_addition(existing: bytes, template: bytes, source: Path, target: Path, has_link) -> bytes:
    try:
        text = existing.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SetupError(f"Cannot inspect {source.name} for a routing pointer: it is not UTF-8.") from exc
    if has_link(text, source, target):
        return b""
    newline = b"\r\n" if b"\r\n" in existing else b"\n"
    addition = template.replace(b"\r\n", b"\n").replace(b"\n", newline)
    separator = b"" if not existing or existing.endswith((b"\n", b"\r")) else newline
    return separator + addition


def setup(
    project_root: Path,
    include_skills: bool = False,
    include_specialists: bool = False,
    claude_md: bool | None = None,
    copilot_instructions: bool = False,
) -> tuple[list[str], list[str]]:
    """Create missing routing files and return validation errors and notes.

    CLAUDECODE enables creation or updating of CLAUDE.md unless explicitly disabled.
    """
    create_claude = claude_md is True or (claude_md is None and bool(os.environ.get("CLAUDECODE")))
    try:
        root = Path(project_root).resolve()
    except (OSError, RuntimeError) as exc:
        return [f"Cannot resolve project root {project_root}: {exc}"], []
    if not root.is_dir():
        return [f"Project root must already be an existing directory: {root}"], []
    try:
        templates = _read_templates()
        claude = Path("CLAUDE.md")
        copilot = Path(".github/copilot-instructions.md")
        if not create_claude:
            templates.pop(claude)
        if not copilot_instructions:
            templates.pop(copilot)
        if not include_skills:
            templates.pop(Path(".context-routing/skills.md"))
        if not include_specialists:
            templates.pop(Path(".context-routing/specialists.md"))
        index = Path(".context-routing/index.md")
        for enabled, name, label in ((include_skills, "skills.md", "Skill routing"), (include_specialists, "specialists.md", "Specialist routing")):
            if enabled:
                templates[index] += f"\n- [{label}]({name}): select an agreed project-specific route.\n".encode()
        existing = _preflight(root, templates)
        if str(Path(__file__).resolve().parent) not in sys.path:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        from validate import _active_text, has_agents_import, has_link, validate

        snapshots = {}

        def observe(path):
            path = Path(path)
            if path not in snapshots:
                try:
                    info = path.lstat()
                    snapshots[path] = (info.st_mode, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                except FileNotFoundError:
                    snapshots[path] = None

        for relative in templates:
            path = root / relative
            observe(path)
            if (existing[relative] is None) != (snapshots[path] is None):
                raise SetupError(f"Project changed during setup preflight: {path}")
            if path.is_symlink():
                observe(path.resolve())

        originals = {}
        additions = {}
        for relative in (Path("AGENTS.md"), claude, copilot):
            if relative not in templates:
                continue
            name = relative.name
            root_file = root / relative
            if relative == claude and root_file.is_symlink():
                continue
            if existing[relative] is not None:
                contents = root_file.read_bytes()
                originals[root_file] = contents
                if relative == claude:
                    try:
                        text = contents.decode("utf-8-sig")
                    except UnicodeDecodeError as exc:
                        raise SetupError(f"Cannot inspect {name} for a routing pointer: it is not UTF-8.") from exc
                    if has_agents_import(text) and not os.environ.get("CLAUDECODE"):
                        continue
                # Do not introduce the AGENTS import into an existing CLAUDE.md.
                pointer = templates[copilot] if relative == copilot else templates[Path("AGENTS.md")]
                additions[root_file] = _pointer_addition(
                    contents, pointer, root_file, root / index, has_link
                )
                text = contents.decode("utf-8-sig")
                active = _active_text(text)
                uncommented = re.sub(r"<!--.*?-->", "", active, flags=re.DOTALL)
                unclosed = "<!--" in uncommented or not _active_text(text + "\nROUTING_SENTINEL").endswith("\nROUTING_SENTINEL")
                if additions[root_file] and unclosed:
                    raise SetupError(f"Cannot append routing pointer to {name}: unclosed fence or HTML comment.")
                if name == "CLAUDE.md" and not os.environ.get("CLAUDECODE"):
                    has_import = re.search(r"(?m)^@\.context-routing/index\.md[ \t]*$", re.sub(r"<!--.*\Z", "", uncommented, flags=re.DOTALL))
                    if additions[root_file] or not has_import:
                        if unclosed:
                            raise SetupError(f"Cannot append routing import to {name}: unclosed fence or HTML comment.")
                    if not has_import:
                        newline = b"\r\n" if b"\r\n" in contents else b"\n"
                        current = contents + additions[root_file]
                        separator = b"" if not current or current.endswith((b"\n", b"\r")) else newline
                        additions[root_file] += separator + b"@.context-routing/index.md" + newline
        proposed = {
            root / relative: (b"@AGENTS.md\n" if relative == claude and claude_md is True else contents)
            for relative, contents in templates.items() if existing[relative] is None
        }
        proposed.update({path: originals[path] + addition for path, addition in additions.items() if addition})
        errors, notes = validate(
            root, require_claude=claude in templates, require_copilot=copilot_instructions,
            proposed=proposed, observe=observe,
        )
        if errors:
            baseline_errors, _ = validate(root, require_claude=claude in templates, require_copilot=copilot_instructions)
            return [
                f"{'Pre-existing' if error in baseline_errors else 'Proposed setup'}: {error}"
                for error in errors
            ], notes

        def check_unchanged(published):
            for path, original in snapshots.items():
                if path in published or any(path == p.parent or path in p.parents for p in published):
                    continue
                try:
                    info = path.lstat()
                    current = (info.st_mode, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                except FileNotFoundError:
                    current = None
                if current != original:
                    raise SetupError(f"Project changed after validation: {path}")
            _preflight(root, templates)

        published = set()
        created_dirs = []
        try:
            check_unchanged(published)
            for target, contents in proposed.items():
                check_unchanged(published)
                missing = []
                parent = target.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    created_dirs.append(directory)
                if target not in originals:
                    with target.open("xb") as stream:
                        published.add(target)
                        stream.write(contents)
                else:
                    flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
                    fd = os.open(target, flags)
                    with os.fdopen(fd, "r+b") as stream:
                        info = os.fstat(stream.fileno())
                        identity = (info.st_mode, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                        if identity != snapshots[target] or stream.read() != originals[target]:
                            raise SetupError(f"Project changed after validation: {target}")
                        published.add(target)
                        stream.write(additions[target])
            check_unchanged(published)
            for path in published:
                if path.read_bytes() != proposed[path]:
                    raise SetupError(f"Published file changed during setup: {path}")
            errors, final_notes = validate(root, require_claude=claude in templates, require_copilot=copilot_instructions)
            if errors:
                raise SetupError("Validation after publication failed: " + "; ".join(errors))
            return [], final_notes
        except (OSError, SetupError) as exc:
            cleanup_errors = []
            for directory in reversed(created_dirs):
                try:
                    directory.rmdir()
                except OSError as cleanup:
                    cleanup_errors.append(f"Could not remove created directory {directory}: {cleanup}")
            if published:
                paths = ", ".join(sorted(path.relative_to(root).as_posix() for path in published))
                cleanup_errors.insert(0, f"{exc}; setup may have changed these files: {paths}. Review them manually; no automatic file rollback was attempted.")
            else:
                cleanup_errors.insert(0, str(exc))
            return cleanup_errors, notes
    except (OSError, SetupError) as exc:
        return [str(exc)], []
    except ImportError as exc:
        return [f"Could not import scripts/validate.py before setup: {exc}"], []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set up project context-routing files.")
    parser.add_argument("PROJECT_ROOT", type=Path, help="existing project directory")
    parser.add_argument("--include-skills", action="store_true", help="create the selected optional skill map")
    parser.add_argument("--include-specialists", action="store_true", help="create the selected optional specialist map")
    parser.add_argument("--claude-md", action="store_true", default=None, help="create or update CLAUDE.md (creation also enabled when CLAUDECODE is set)")
    parser.add_argument("--copilot-instructions", action="store_true", help="create or update .github/copilot-instructions.md")
    args = parser.parse_args(argv)
    errors, notes = setup(args.PROJECT_ROOT, args.include_skills, args.include_specialists, args.claude_md, args.copilot_instructions)
    for note in notes:
        print(f"NOTE: {note}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"Routing files passed structural and basic content validation in {args.PROJECT_ROOT}. Fresh navigation and quality review are separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
