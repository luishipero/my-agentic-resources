import importlib.util
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate.py"
SPEC = importlib.util.spec_from_file_location("router_validate", MODULE_PATH)
validate_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_module)


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".context-routing").mkdir()
        (self.root / "src" / "has space").mkdir(parents=True)
        (self.root / "src" / "has space" / "CONTEXT.md").write_text("# Context\nThis module contains code.\n", encoding="utf-8")
        (self.root / ".context-routing" / "index.md").write_text(
            "# Routes\n[Agents](agents.md) [Skills](skills.md)\n", encoding="utf-8"
        )
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space/` | A module | [Context](../src/has%20space/CONTEXT.md) |\n",
            encoding="utf-8",
        )
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use local tool | local | [Skill](../tool/SKILL.md) |\n",
            encoding="utf-8",
        )
        (self.root / "AGENTS.md").write_text("Read [routing](.context-routing/index.md).\n", encoding="utf-8")
        (self.root / "tool").mkdir()
        (self.root / "tool" / "SKILL.md").write_text("skill", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def result(self):
        return validate_module.validate(self.root)

    def test_index_only_and_duplicate_legacy_maps(self):
        routing = self.root / ".context-routing"
        legacy = (routing / "agents.md").read_text(encoding="utf-8")
        (routing / "index.md").write_text(legacy + "\n[Skills](skills.md)\n", encoding="utf-8")
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertFalse(any("Legacy folder map" in n for n in notes))
        self.assertTrue(any("Both index.md" in n for n in notes), notes)
        with (routing / "index.md").open("a", encoding="utf-8") as stream:
            stream.write("[Legacy](agents.md)\n")
        errors, _ = self.result()
        self.assertTrue(any("Both index.md" in e for e in errors), errors)

    def test_stray_folder_rows_and_non_routes(self):
        routing = self.root / ".context-routing"
        index = routing / "index.md"
        legacy = routing / "agents.md"
        with index.open("a", encoding="utf-8") as stream:
            stream.write("\n| src/has space/ | module | [Context](../src/has%20space/CONTEXT.md) |\n")
        errors, _ = self.result()
        self.assertTrue(any("index.md" in e and "folder route row is outside a table" in e for e in errors), errors)
        index.write_text("# Routes\n[Agents](agents.md) [Skills](skills.md)\n", encoding="utf-8")
        for map_path in (legacy, index):
            with self.subTest(map_path=map_path.name):
                if map_path == index:
                    index.write_text(legacy.read_text(encoding="utf-8") + "\n[Skills](skills.md)\n", encoding="utf-8")
                original = map_path.read_text(encoding="utf-8")
                with map_path.open("a", encoding="utf-8") as stream:
                    stream.write("\n| src/has space/ | module | [Context](../src/has%20space/CONTEXT.md) |\n")
                errors, _ = self.result()
                self.assertTrue(any("folder route row is outside a table" in e for e in errors), errors)
                map_path.write_text(original + "\n```md\n| x | y | [Context](../src/has%20space/CONTEXT.md) |\n```\n\n| Topic | Detail | Link |\n|---|---|---|\n| A | B | [Context](../src/has%20space/CONTEXT.md) |\n", encoding="utf-8")
                errors, _ = self.result()
                self.assertFalse(any("folder route row is outside a table" in e for e in errors), errors)
                map_path.write_text(original, encoding="utf-8")

    def test_root_entry_compatibility_and_present_pointer_validation(self):
        claude = self.root / "CLAUDE.md"
        agents = self.root / "AGENTS.md"
        self.assertEqual(self.result()[0], [])  # Legacy AGENTS-only project.
        claude.write_text("Read [routing](.context-routing/index.md).\n", encoding="utf-8")
        self.assertEqual(self.result()[0], [])
        agents.unlink()
        self.assertEqual(self.result()[0], [])  # Claude-only project.
        claude.write_text("No route\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("CLAUDE.md: must link" in error for error in errors), errors)
        agents.write_text("Read [routing](.context-routing/index.md).\n", encoding="utf-8")
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any("CLAUDE.md: no routing pointer" in note for note in notes), notes)
        errors, _ = validate_module.validate(self.root, require_claude=True)
        self.assertTrue(any("CLAUDE.md: must link" in error for error in errors), errors)
        agents.unlink()
        claude.unlink()
        self.assertTrue(any("Missing root routing entry" in error for error in self.result()[0]))

    def test_optional_copilot_pointer_and_explicit_requirement(self):
        copilot = self.root / ".github" / "copilot-instructions.md"
        errors, _ = validate_module.validate(self.root, require_copilot=True)
        self.assertTrue(any("Missing required routing entry: .github/copilot-instructions.md" in e for e in errors), errors)
        copilot.parent.mkdir()
        copilot.write_text("# Existing guidance\n", encoding="utf-8")
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any(".github/copilot-instructions.md: no routing pointer" in n for n in notes), notes)
        errors, _ = validate_module.validate(self.root, require_copilot=True)
        self.assertTrue(any(".github/copilot-instructions.md: must link" in e for e in errors), errors)
        copilot.write_text("Read [routing](../.context-routing/index.md).\n", encoding="utf-8")
        self.assertEqual(validate_module.validate(self.root, require_copilot=True)[0], [])

    def test_claude_agents_import_requires_valid_root_entry(self):
        claude = self.root / "CLAUDE.md"
        agents = self.root / "AGENTS.md"
        claude.write_text("@AGENTS.md\n", encoding="utf-8")
        self.assertEqual(validate_module.validate(self.root, require_claude=True)[0], [])
        agents.write_text("No routing pointer\n", encoding="utf-8")
        errors, _ = validate_module.validate(self.root, require_claude=True)
        self.assertTrue(any("imported AGENTS.md must link" in e for e in errors), errors)
        agents.unlink()
        errors, _ = validate_module.validate(self.root, require_claude=True)
        self.assertTrue(any("@AGENTS.md requires a readable" in e for e in errors), errors)

    def test_claude_example_import_is_not_routing(self):
        claude = self.root / "CLAUDE.md"
        for text in ("```\n@AGENTS.md\n```\n", "<!--\n@AGENTS.md\n-->\n"):
            with self.subTest(text=text):
                claude.write_text(text, encoding="utf-8")
                errors, _ = validate_module.validate(self.root, require_claude=True)
                self.assertTrue(any("CLAUDE.md: must link" in e for e in errors), errors)

    def test_copilot_unrelated_links_do_not_break_route_validation(self):
        copilot = self.root / ".github" / "copilot-instructions.md"
        copilot.parent.mkdir()
        copilot.write_text(
            "Read [routing](../.context-routing/index.md).\n[Existing](missing.md)\n",
            encoding="utf-8",
        )
        self.assertEqual(validate_module.validate(self.root, require_copilot=True)[0], [])

    def test_commented_pointer_is_not_an_active_entry(self):
        copilot = self.root / ".github" / "copilot-instructions.md"
        copilot.parent.mkdir()
        copilot.write_text("<!-- [routing](../.context-routing/index.md) -->\n", encoding="utf-8")
        errors, _ = validate_module.validate(self.root, require_copilot=True)
        self.assertTrue(any("must link" in e for e in errors), errors)

    def test_context_quality_and_placeholders(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        for value in ("", "# Heading\n## More\n", "# Context\n**Purpose**\n**Key files:**\n", "Description <folder path>", "Text <what it does>", "Text <fill this in>", "Text {TODO}", "Text [TODO: add details]"):
            with self.subTest(value=value):
                context.write_text(value, encoding="utf-8")
                errors, _ = self.result()
                self.assertTrue(any("heading-only" in e or "template marker" in e for e in errors), errors)
        context.write_text("# Context\nGeneric <T>, x<y, <customer>, TODO fix tests.\n```md\n<folder path> [TODO: later]\n```\n", encoding="utf-8")
        self.assertEqual(self.result()[0], [])

    def test_inline_examples_and_standalone_template_markers(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        context.write_text("# Context\nUse `GET /users/<name>` and `tool <command>` for examples.\n", encoding="utf-8")
        self.assertEqual(self.result()[0], [])
        for marker in ("<command>", "<role>", "<name>", "{TODO}"):
            with self.subTest(marker=marker):
                context.write_text(f"# Context\n- `{marker}` — describe this.\n", encoding="utf-8")
                self.assertTrue(any("template marker" in error for error in self.result()[0]))

    def test_declared_paths_and_future_inputs(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        (context.parent / "existing file.py").write_text("ok", encoding="utf-8")
        context.write_text("# Context\n**Key files:**\n- `./existing file.py` - code\n- `./missing.py` - code\n**Inputs**\n- Stable reference inputs: `repo:src/missing.yaml`.\n- Per-run working input: `repo:src/new.json`.\n- Per-run working input: `repo:absent/new.json`.\n- Glob `src/*.py`; external `https://example.com/file`; command `python tools/run.py`; identifier `Model`.\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("missing.py" in e for e in errors), errors)
        self.assertTrue(any("missing.yaml" in e for e in errors), errors)
        self.assertTrue(any("absent/new.json" in e for e in errors), errors)
        self.assertFalse(any("src/new.json" in e or "existing file.py" in e or "python tools" in e for e in errors), errors)

    def test_template_markers_and_generic_values(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        for marker in ("<1-2 sentences - what this folder holds and why>", "<role>", "<role, and anything sharp-edged about it>", "<what this folder is for>", "<why it exists in product terms>"):
            with self.subTest(marker=marker):
                context.write_text("# Context\nPurpose " + marker, encoding="utf-8")
                self.assertTrue(any("template marker" in e for e in self.result()[0]))
        context.write_text("# Context\nResult<What> and Result<Role>, <customer>, <T>, x<y.\n```\n<role>\n```\n", encoding="utf-8")
        self.assertEqual(self.result()[0], [])

    def test_required_paths_and_nested_inputs(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        context.write_text(
            "# Context\n## Key files\n- `repo:src/required.py` - working implementation\n"
            "## Inputs\n### Reference\n- `repo:src/ref.json`\n- Working input: `repo:src/ref3.json`\n"
            "### Required files\n- `repo:src/required.json`\n"
            "### Working\n- `repo:src/new.json`\n"
            "- Working input: `repo:src/new2.json`; reference input: `repo:src/ref2.json`\n"
            "## Other\n- `repo:src/not_checked.json`\n", encoding="utf-8")
        errors, _ = self.result()
        for path in ("src/required.py", "src/ref.json", "src/ref2.json", "src/ref3.json", "src/required.json"):
            self.assertTrue(any(path in e for e in errors), errors)
        for path in ("src/new.json", "src/not_checked.json"):
            self.assertFalse(any(path in e for e in errors), errors)

    def test_nested_input_subsection_sibling_reset(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        context.write_text(
            "# Context\n## Inputs\n### Working\n- `repo:src/out.json`\n"
            "#### Generated\n- `repo:src/deeper.json`\n"
            "### Configuration\n- `repo:src/missing.yaml`\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("src/missing.yaml" in e for e in errors), errors)
        self.assertFalse(any("src/out.json" in e or "src/deeper.json" in e for e in errors), errors)

    def test_explicit_paths_legacy_identifiers_and_containment(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        (self.root / "Makefile").write_text("ok", encoding="utf-8")
        (context.parent / "local file").write_text("ok", encoding="utf-8")
        context.write_text(
            "# Context\n## Key files\n"
            "- `./local file`\n- `repo:Makefile`\n- `./Makefile`\n"
            "- `Invoice.total`\n- `Makefile`\n- `src/missing.py`\n"
            "- `repo:../outside`\n- `./../../../outside`\n"
            "- `repo:/absolute`\n- `repo:src/*.py`\n",
            encoding="utf-8",
        )
        errors, notes = self.result()
        self.assertTrue(any("missing declared path: ./Makefile" in e for e in errors), errors)
        self.assertFalse(any("repo:Makefile" in e or "./local file" in e or "Invoice.total" in e for e in errors), errors)
        for value in ("Invoice.total", "Makefile", "src/missing.py"):
            self.assertTrue(any("unverified unmarked entry" in n and value in n for n in notes), notes)
        for value in ("repo:../outside", "./../../../outside"):
            self.assertTrue(any("escapes project root" in e and value in e for e in errors), errors)
        for value in ("repo:/absolute", "repo:src/*.py"):
            self.assertTrue(any("invalid declared path" in e and value in e for e in errors), errors)

    def test_explicit_paths_reject_symlink_escape_and_use_one_base(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        (self.root / "shared.py").write_text("ok", encoding="utf-8")
        link = context.parent / "outside"
        try:
            link.symlink_to(self.root.parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlinks are unavailable")
        context.write_text(
            "# Context\n## Key files\n- `./shared.py`\n- `repo:shared.py`\n"
            "- `./outside/some-file`\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("missing declared path: ./shared.py" in e for e in errors), errors)
        self.assertFalse(any("repo:shared.py" in e for e in errors), errors)
        self.assertTrue(any("escapes project root" in e and "./outside/some-file" in e for e in errors), errors)

    def test_size_warnings_and_cycles(self):
        context = self.root / "src" / "has space" / "CONTEXT.md"
        context.write_text("Text " + "x" * 32000 + "\n[Self](CONTEXT.md)\n", encoding="utf-8")
        with (self.root / "AGENTS.md").open("a", encoding="utf-8") as stream:
            stream.write("line\n" * 61)
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any("approximately" in n and "tokens" in n for n in notes), notes)
        self.assertTrue(any("large entry" in n for n in notes), notes)

    def test_optional_map_missing_and_dangling_links(self):
        routing = self.root / ".context-routing"
        (routing / "skills.md").unlink()
        errors, _ = self.result()
        self.assertTrue(any("missing link destination: skills.md" in e for e in errors), errors)
        (routing / "index.md").write_text("[Agents](agents.md)\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertEqual(errors, [])
        (routing / "specialists.md").write_text("| When to use | Specialist | Entry point |\n|---|---|---|\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("must link to specialists.md" in e for e in errors), errors)

    def test_specialist_duplicate_and_invalid_paths(self):
        routing = self.root / ".context-routing"
        with (routing / "index.md").open("a", encoding="utf-8") as stream:
            stream.write("[Specialists](specialists.md)\n")
        (routing / "specialists.md").write_text(
            "| When to use | Specialist | Entry point |\n|---|---|---|\n"
            "| Review | Reader | [Agent](../missing.toml) |\n"
            "| Read | reader | [Agent](../../outside.toml) |\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("duplicate specialist route" in e for e in errors), errors)
        self.assertTrue(any("missing local specialist" in e for e in errors), errors)
        self.assertTrue(any("specialist link escapes project root" in e for e in errors), errors)

    def test_valid_dot_folder_and_encoded_space_links(self):
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any("Legacy folder map" in note for note in notes), notes)

    def test_canonical_pointer_links_and_encoded_fragment_filename(self):
        (self.root / "AGENTS.md").write_text("[routing](./.context-routing/../.context-routing/index.md#start)\n", encoding="utf-8")
        (self.root / ".context-routing" / "index.md").write_text(
            "[Agents](./agents.md#routes) [Skills](./skills.md?view=all)\n", encoding="utf-8"
        )
        (self.root / "src" / "has space" / "file#name.md").write_text("ok", encoding="utf-8")
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use | hash file | [File](../src/has%20space/file%23name.md) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertEqual(errors, [])

    def test_angle_bracket_links_and_linked_context_traversal(self):
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space/` | context | [Context](<../src/has space/CONTEXT.md>) |\n", encoding="utf-8"
        )
        (self.root / "src" / "has space" / "CONTEXT.md").write_text("[More](../missing/CONTEXT.md)\n", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("missing link destination" in e and "../missing/CONTEXT.md" in e for e in errors), errors)

    def test_broken_pointer_and_broken_link(self):
        (self.root / "AGENTS.md").write_text("No pointer\n", encoding="utf-8")
        (self.root / ".context-routing" / "index.md").write_text("[Agents](gone.md) [Skills](skills.md)", encoding="utf-8")
        errors, _ = self.result()
        self.assertTrue(any("AGENTS.md: must link" in e for e in errors), errors)
        self.assertTrue(any("missing link destination: gone.md" in e for e in errors), errors)

    def test_duplicate_folder_and_skill_routes(self):
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space/` | One | [Context](../src/has%20space/CONTEXT.md) |\n"
            "| `src/has space/../has space` | Two | [Context](../src/has%20space/CONTEXT.md) |\n", encoding="utf-8"
        )
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use | MySkill | [Skill](../tool/SKILL.md) |\n"
            "| Again | myskill | [Skill](../tool/SKILL.md) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("duplicate folder route" in e for e in errors), errors)
        self.assertTrue(any("duplicate skill route" in e for e in errors), errors)

    def test_missing_local_skill_is_error(self):
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use | absent | [Skill](../missing/SKILL.md) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("missing local skill" in e for e in errors), errors)

    def test_context_file_must_belong_to_declared_folder(self):
        (self.root / "src" / "other").mkdir()
        (self.root / "src" / "other" / "CONTEXT.md").write_text("# Other\n", encoding="utf-8")
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space/` | module | [Context](../src/other/CONTEXT.md) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("context file must be inside its routed folder" in e for e in errors), errors)

    def test_remote_context_and_directory_skill_entries_fail(self):
        (self.root / "tool" / "directory").mkdir()
        (self.root / "src" / "context-dir" / "CONTEXT.md").mkdir(parents=True)
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space/` | remote context | [Context](https://host/CONTEXT.md) |\n"
            "| `src/context-dir/` | directory context | [Context](../src/context-dir/CONTEXT.md) |\n", encoding="utf-8"
        )
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use | directory | [Skill](../tool/directory) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("Context file link must be relative" in e for e in errors), errors)
        self.assertTrue(any("context route must point to an existing file" in e for e in errors), errors)
        self.assertTrue(any("missing local skill" in e for e in errors), errors)

    def test_second_matching_route_table_is_rejected(self):
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space` | one | [Context](../src/has%20space/CONTEXT.md) |\n\n"
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space` | two | [Context](../src/has%20space/CONTEXT.md) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("same route columns" in e for e in errors), errors)

    def test_blank_required_descriptions_fail(self):
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src/has space` |   | [Context](../src/has%20space/CONTEXT.md) |\n", encoding="utf-8"
        )
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "|   | local | [Skill](../tool/SKILL.md) |\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("empty folder description" in e for e in errors), errors)
        self.assertTrue(any("empty task description" in e for e in errors), errors)

    def test_malformed_table_row_is_reported(self):
        (self.root / ".context-routing" / "agents.md").write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "this row has no cell separators\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertTrue(any("malformed table row" in e for e in errors), errors)

    def test_external_windows_path_is_a_machine_specific_note(self):
        winpath = r"C:\Tools\project-context\SKILL.md"
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            f"| Use | external | `{winpath}` (machine-specific) |\n", encoding="utf-8"
        )
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any(winpath in note and ("exists" in note or "missing" in note or "unsupported" in note) for note in notes), notes)

    @unittest.skipUnless(sys.platform == "win32", "POSIX absolute paths are native only on Windows host")
    def test_posix_external_path_is_unsupported_on_windows(self):
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use | external | `/opt/skills/example/SKILL.md` (machine-specific) |\n", encoding="utf-8"
        )
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any("/opt/skills/example/SKILL.md" in note and "unsupported" in note for note in notes), notes)

    def test_unexpandable_home_path_is_reported_as_unsupported(self):
        (self.root / ".context-routing" / "skills.md").write_text(
            "| When to use | Skill | Entry point |\n|---|---|---|\n"
            "| Use | external | `~/skill/SKILL.md` (machine-specific) |\n", encoding="utf-8"
        )
        with patch.object(Path, "expanduser", side_effect=RuntimeError("home unavailable")):
            errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any("~/skill/SKILL.md" in note and "unsupported" in note for note in notes), notes)

    def test_empty_catalogs_are_notes(self):
        for name, header in (("agents.md", "Folder | What's there | Context file"), ("skills.md", "When to use | Skill | Entry point")):
            (self.root / ".context-routing" / name).write_text(f"| {header} |\n|---|---|---|\n", encoding="utf-8")
        errors, notes = self.result()
        self.assertEqual(errors, [])
        self.assertTrue(any("empty folder route catalog" in note for note in notes), notes)
        self.assertTrue(any("empty skill route catalog" in note for note in notes), notes)

    def test_fenced_examples_and_remote_links_are_ignored(self):
        (self.root / ".context-routing" / "index.md").write_text(
            "[Agents](agents.md) [Skills](skills.md) [Remote](https://example.invalid/nope)\n"
            "```md\n[broken](missing.md)\n```\n", encoding="utf-8"
        )
        errors, _ = self.result()
        self.assertFalse(any("missing.md" in e or "example.invalid" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
