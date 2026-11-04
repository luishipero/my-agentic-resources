import os
import sys
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import setup as setup_module
import validate as validate_module


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("CLAUDECODE", None)
    def test_default_creates_core_only(self):
        errors, _ = setup_module.setup(self.root)
        self.assertEqual(errors, [])
        self.assertEqual({p.name for p in (self.root / ".context-routing").iterdir()}, {"index.md"})

    def test_setup_runs_with_isolated_python(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPTS / "setup.py"), str(self.root), "--claude-md"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / ".context-routing" / "index.md").is_file())
        self.assertTrue((self.root / "CLAUDE.md").is_file())

    def test_cli_selected_entry_points_and_validator(self):
        setup = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPTS / "setup.py"), str(self.root),
             "--claude-md", "--copilot-instructions"],
            capture_output=True, text=True,
        )
        self.assertEqual(setup.returncode, 0, setup.stderr)
        validate = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPTS / "validate.py"), str(self.root),
             "--claude-md", "--copilot-instructions"],
            capture_output=True, text=True,
        )
        self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

    def test_missing_claude_not_created_by_default(self):
        errors, _ = setup_module.setup(self.root)
        self.assertEqual(errors, [])
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertTrue((self.root / "AGENTS.md").is_file())

    def test_claudecode_env_creates_claude(self):
        os.environ["CLAUDECODE"] = "1"
        self.assertEqual(setup_module.setup(self.root)[0], [])
        text = (self.root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@.context-routing/index.md", text)
        self.assertIn("[context routing index](.context-routing/index.md)", text)

    def test_explicit_false_overrides_env(self):
        os.environ["CLAUDECODE"] = "1"
        self.assertEqual(setup_module.setup(self.root, claude_md=False)[0], [])
        self.assertFalse((self.root / "CLAUDE.md").exists())

    def test_existing_claude_preserved_without_flag(self):
        target = self.root / "CLAUDE.md"
        target.write_text("# Claude\n", encoding="utf-8")
        self.assertEqual(setup_module.setup(self.root)[0], [])
        self.assertEqual(target.read_text(encoding="utf-8"), "# Claude\n")

    def test_existing_claude_gets_pointer_with_environment_detection(self):
        os.environ["CLAUDECODE"] = "1"
        target = self.root / "CLAUDE.md"
        original = b"\xef\xbb\xbf# Claude\r\nExisting instructions.\r\n"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root)[0], [])
        result = target.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertIn(b"[context routing index](.context-routing/index.md)\r\n", result)
        self.assertNotIn(b"@.context-routing/index.md", result)
        self.assertEqual(setup_module.setup(self.root)[0], [])
        self.assertEqual(target.read_bytes(), result)

    def test_claudecode_adds_pointer_even_with_agents_import_and_flag(self):
        os.environ["CLAUDECODE"] = "1"
        target = self.root / "CLAUDE.md"
        original = b"@AGENTS.md\n# Existing\n"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        result = target.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertIn(b"[context routing index](.context-routing/index.md)", result)
        self.assertNotIn(b"@.context-routing/index.md", result)
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        self.assertEqual(target.read_bytes(), result)

    def test_claudecode_existing_pointer_is_not_duplicated(self):
        os.environ["CLAUDECODE"] = "1"
        target = self.root / "CLAUDE.md"
        original = b"Read [routing](.context-routing/index.md).\n"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root)[0], [])
        self.assertEqual(target.read_bytes(), original)

    def test_explicit_false_preserves_existing_claude_with_environment(self):
        os.environ["CLAUDECODE"] = "1"
        target = self.root / "CLAUDE.md"
        target.write_bytes(b"# Claude\n")
        self.assertEqual(setup_module.setup(self.root, claude_md=False)[0], [])
        self.assertEqual(target.read_bytes(), b"# Claude\n")

    def test_claudecode_existing_unclosed_fence_prevents_writes(self):
        os.environ["CLAUDECODE"] = "1"
        target = self.root / "CLAUDE.md"
        target.write_bytes(b"```\n# Existing\n")
        errors, _ = setup_module.setup(self.root)
        self.assertTrue(any("unclosed fence" in error for error in errors), errors)
        self.assertEqual(target.read_bytes(), b"```\n# Existing\n")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_unselected_invalid_claude_does_not_block_setup(self):
        target = self.root / "CLAUDE.md"
        target.write_bytes(b"\xff\xfe")
        errors, notes = setup_module.setup(self.root)
        self.assertEqual(errors, [])
        self.assertTrue(any("Cannot read CLAUDE.md" in note for note in notes), notes)
        self.assertEqual(target.read_bytes(), b"\xff\xfe")

    def test_copilot_entry_is_optional_and_idempotent(self):
        self.assertEqual(setup_module.setup(self.root)[0], [])
        target = self.root / ".github" / "copilot-instructions.md"
        self.assertFalse(target.exists())
        self.assertEqual(setup_module.setup(self.root, copilot_instructions=True)[0], [])
        first = target.read_bytes()
        self.assertIn(b"](../.context-routing/index.md)", first)
        self.assertEqual(setup_module.setup(self.root, copilot_instructions=True)[0], [])
        self.assertEqual(target.read_bytes(), first)

    def test_existing_copilot_entry_is_preserved_and_opt_in(self):
        target = self.root / ".github" / "copilot-instructions.md"
        target.parent.mkdir()
        original = b"\xef\xbb\xbf# Existing\r\nKeep instructions.\r\n"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root)[0], [])
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(setup_module.setup(self.root, copilot_instructions=True)[0], [])
        result = target.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertIn(b"](../.context-routing/index.md)\r\n", result)
        self.assertEqual(setup_module.setup(self.root, copilot_instructions=True)[0], [])
        self.assertEqual(target.read_bytes(), result)

    def test_copilot_existing_unclosed_fence_prevents_writes(self):
        target = self.root / ".github" / "copilot-instructions.md"
        target.parent.mkdir()
        target.write_text("# Existing\n```\n", encoding="utf-8")
        errors, _ = setup_module.setup(self.root, copilot_instructions=True)
        self.assertTrue(any("unclosed fence" in error for error in errors), errors)
        self.assertEqual(target.read_text(encoding="utf-8"), "# Existing\n```\n")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_selected_copilot_invalid_utf8_fails_before_writes(self):
        target = self.root / ".github" / "copilot-instructions.md"
        target.parent.mkdir()
        target.write_bytes(b"\xff\xfe")
        errors, _ = setup_module.setup(self.root, copilot_instructions=True)
        self.assertTrue(any("not UTF-8" in error for error in errors), errors)
        self.assertEqual(target.read_bytes(), b"\xff\xfe")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_claude_created_with_agents_import_only(self):
        (self.root / "AGENTS.md").write_text("# Existing guidance\n", encoding="utf-8")
        errors, _ = setup_module.setup(self.root, claude_md=True)
        self.assertEqual(errors, [])
        claude = (self.root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(claude, "@AGENTS.md\n")
        self.assertTrue((self.root / "AGENTS.md").read_text(encoding="utf-8").startswith("# Existing guidance\n"))
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8"), claude)

    def test_existing_claude_preserved_and_pointer_added_once(self):
        original = b"\xef\xbb\xbf# Claude\r\nExisting instructions.\r\n"
        target = self.root / "CLAUDE.md"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        result = target.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertNotIn(b"@AGENTS.md", result)
        self.assertIn(b"[context routing index](.context-routing/index.md)", result)
        self.assertIn(b"@.context-routing/index.md\r\n", result)
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        self.assertEqual(target.read_bytes(), result)

    def test_existing_claude_link_gets_import_once(self):
        target = self.root / "CLAUDE.md"
        original = b"Read [routing](.context-routing/index.md).\n"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        result = target.read_bytes()
        self.assertEqual(result, original + b"@.context-routing/index.md\n")
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        self.assertEqual(target.read_bytes(), result)

    def test_existing_import_is_not_duplicated_and_examples_do_not_count(self):
        target = self.root / "CLAUDE.md"
        original = b"```\n@.context-routing/index.md\n```\n"
        target.write_bytes(original)
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        result = target.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertTrue(result.endswith(b"@.context-routing/index.md\n"))
        self.assertEqual(setup_module.setup(self.root, claude_md=True)[0], [])
        self.assertEqual(target.read_bytes(), result)

    def test_unclosed_fence_or_comment_prevents_writes(self):
        target = self.root / "CLAUDE.md"
        for original in (b"```\n@.context-routing/index.md\n", b"<!--\n@.context-routing/index.md\n"):
            with self.subTest(original=original):
                target.write_bytes(original)
                errors, _ = setup_module.setup(self.root, claude_md=True)
                self.assertTrue(any("unclosed fence or HTML comment" in error for error in errors), errors)
                self.assertEqual(target.read_bytes(), original)
                self.assertEqual(list(self.root.iterdir()), [target])

    def test_invalid_claude_utf8_fails_before_writes(self):
        (self.root / "CLAUDE.md").write_bytes(b"\xff\xfe")
        errors, _ = setup_module.setup(self.root, claude_md=True)
        self.assertTrue(any("CLAUDE.md" in error for error in errors), errors)
        self.assertEqual([p.name for p in self.root.iterdir()], ["CLAUDE.md"])

    def test_opt_in_maps_are_linked_on_new_index(self):
        errors, _ = setup_module.setup(self.root, include_skills=True, include_specialists=True)
        self.assertEqual(errors, [])
        index = (self.root / ".context-routing" / "index.md").read_text(encoding="utf-8")
        for name in ("skills.md", "specialists.md"):
            self.assertTrue((self.root / ".context-routing" / name).is_file())
            self.assertIn(f"]({name})", index)

    def test_each_opt_in_is_independent(self):
        for option, expected in (("include_skills", "skills.md"), ("include_specialists", "specialists.md")):
            with self.subTest(option=option), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                errors, _ = setup_module.setup(root, **{option: True})
                self.assertEqual(errors, [])
                names = {p.name for p in (root / ".context-routing").iterdir()}
                self.assertEqual(names, {"index.md", expected})

    def test_opt_in_preserves_existing_index_and_map(self):
        setup_module.setup(self.root)
        routing = self.root / ".context-routing"
        index = (routing / "index.md").read_bytes()
        original = b"existing map\r\n"
        (routing / "skills.md").write_bytes(original)
        errors, _ = setup_module.setup(self.root, include_skills=True)
        self.assertTrue(errors)
        self.assertEqual((routing / "index.md").read_bytes(), index)
        self.assertEqual((routing / "skills.md").read_bytes(), original)

    def test_repeat_setup_preserves_created_files(self):
        errors, _ = setup_module.setup(self.root, claude_md=True)
        self.assertEqual(errors, [])
        paths = [self.root / "AGENTS.md", self.root / "CLAUDE.md", *sorted((self.root / ".context-routing").glob("*.md"))]
        first = {path: path.read_bytes() for path in paths}
        errors, _ = setup_module.setup(self.root, claude_md=True)
        self.assertEqual(errors, [])
        self.assertEqual(first, {path: path.read_bytes() for path in paths})

    def test_existing_root_bytes_and_routing_files_are_preserved(self):
        original = b"\xef\xbb\xbf# Local\r\nKeep this.\r\n<!-- BEGIN MANAGED -->\r\nowned\r\n<!-- END MANAGED -->\r\n"
        self.root.joinpath("AGENTS.md").write_bytes(original)
        route_dir = self.root / ".context-routing"
        route_dir.mkdir()
        preserved = {
            "index.md": b"existing index\r\n",
            "agents.md": b"existing agents\n",
        }
        for name, contents in preserved.items():
            (route_dir / name).write_bytes(contents)

        errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)

        result = (self.root / "AGENTS.md").read_bytes()
        self.assertEqual(result, original)
        for name, contents in preserved.items():
            self.assertEqual((route_dir / name).read_bytes(), contents)

    def test_valid_existing_pointer_is_not_duplicated(self):
        original = b"# Project\n\nSee [routing](./.context-routing/index.md#top).\n"
        (self.root / "AGENTS.md").write_bytes(original)
        errors, _ = setup_module.setup(self.root)
        self.assertEqual(errors, [])
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), original)

    def test_pointer_mentioned_in_fenced_example_is_not_treated_as_valid(self):
        original = b"# Project\n```markdown\n[example](.context-routing/index.md)\n```\n"
        (self.root / "AGENTS.md").write_bytes(original)
        setup_module.setup(self.root)
        result = (self.root / "AGENTS.md").read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertEqual(result.count(b".context-routing/index.md"), 2)

    def test_existing_directory_at_file_target_fails_without_overwriting(self):
        (self.root / "AGENTS.md").mkdir()
        errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertTrue((self.root / "AGENTS.md").is_dir())
        self.assertFalse((self.root / ".context-routing").exists())

    def test_case_collision_fails_before_writing(self):
        (self.root / "agents.md").write_text("keep", encoding="utf-8")
        errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertEqual((self.root / "agents.md").read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_claude_symlink_to_agents_updates_shared_file_once(self):
        for selected, target in (("flag", "AGENTS.md"), ("environment", "./AGENTS.md")):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                agents = root / "AGENTS.md"
                claude = root / "CLAUDE.md"
                original = b"\xef\xbb\xbf# Existing\r\nKeep instructions.\r\n"
                agents.write_bytes(original)
                try:
                    claude.symlink_to(target)
                except (OSError, NotImplementedError):
                    self.skipTest("File symlinks are unavailable in this environment")
                with patch.dict(os.environ, {"CLAUDECODE": "1"} if selected == "environment" else {}, clear=False):
                    result = setup_module.setup(root, claude_md=True if selected == "flag" else None)
                    self.assertEqual(result[0], [], result)
                    content = agents.read_bytes()
                    self.assertTrue(content.startswith(original))
                    self.assertEqual(content.count(b"[context routing index](.context-routing/index.md)"), 1)
                    self.assertNotIn(b"@AGENTS.md", content)
                    self.assertNotIn(b"@.context-routing/index.md", content)
                    self.assertTrue(claude.is_symlink())
                    self.assertEqual(os.readlink(claude), target)
                    self.assertEqual(claude.read_bytes(), content)
                    self.assertEqual(setup_module.setup(root, claude_md=True if selected == "flag" else None)[0], [])
                    self.assertEqual(agents.read_bytes(), content)

    def test_claude_symlink_to_other_target_is_rejected(self):
        for target in ("other.md", "missing.md", ".context-routing/../AGENTS.md"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
                (root / "other.md").write_text("# Other\n", encoding="utf-8")
                claude = root / "CLAUDE.md"
                try:
                    claude.symlink_to(target)
                except (OSError, NotImplementedError):
                    self.skipTest("File symlinks are unavailable in this environment")
                errors, _ = setup_module.setup(root, claude_md=True)
                self.assertTrue(any("Refusing to write through symlink" in error for error in errors), errors)
                self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), "# Agents\n")
                self.assertEqual((root / "other.md").read_text(encoding="utf-8"), "# Other\n")
                self.assertTrue(claude.is_symlink())
                self.assertFalse((root / ".context-routing").exists())

    def test_claude_alias_to_symlinked_agents_is_rejected(self):
        agents = self.root / "AGENTS.md"
        claude = self.root / "CLAUDE.md"
        (self.root / "other.md").write_text("# Other\n", encoding="utf-8")
        try:
            agents.symlink_to("other.md")
            claude.symlink_to("AGENTS.md")
        except (OSError, NotImplementedError):
            self.skipTest("File symlinks are unavailable in this environment")
        errors, _ = setup_module.setup(self.root, claude_md=True)
        self.assertTrue(any("Refusing to write through symlink" in error for error in errors), errors)
        self.assertEqual((self.root / "other.md").read_text(encoding="utf-8"), "# Other\n")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_symlink_target_fails_before_writing(self):
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        self.addCleanup(lambda: outside.rmdir() if outside.exists() else None)
        try:
            (self.root / ".context-routing").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlinks are unavailable in this environment")
        errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertFalse((outside / "index.md").exists())

    def test_junction_target_fails_before_writing(self):
        route_dir = self.root.resolve() / ".context-routing"
        route_dir.mkdir()
        original_lstat = Path.lstat
        reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if not reparse_point:
            self.skipTest("This platform does not expose Windows reparse-point attributes")

        def fake_lstat(path):
            if path == route_dir:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=reparse_point)
            return original_lstat(path)

        # Simulate Python 3.10/3.11, where Path.is_junction is unavailable.
        with patch.object(Path, "is_junction", None, create=True), patch.object(
            Path, "lstat", autospec=True, side_effect=fake_lstat
        ):
            errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertEqual(list(route_dir.iterdir()), [])

    def test_invalid_utf8_root_fails_before_writing(self):
        (self.root / "AGENTS.md").write_bytes(b"\xff\xfe")
        errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertEqual(list(self.root.iterdir()), [self.root / "AGENTS.md"])

    def test_missing_validator_fails_before_writing(self):
        with patch.dict("sys.modules", {"validate": None}):
            errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_malformed_templates_fail_before_writing(self):
        template = self.root / "bad-template.md"
        template.write_text("## Root AGENTS.md\nno fenced block\n", encoding="utf-8")
        with patch.object(setup_module, "TEMPLATE", template):
            errors, _ = setup_module.setup(self.root)
        self.assertTrue(errors)
        self.assertEqual(list(self.root.iterdir()), [template])

    def test_missing_or_non_directory_project_root_fails(self):
        errors, _ = setup_module.setup(self.root / "missing")
        self.assertTrue(errors)
        file_path = self.root / "project-file"
        file_path.write_text("x", encoding="utf-8")
        errors, _ = setup_module.setup(file_path)
        self.assertTrue(errors)

    def test_broken_existing_link_prevents_all_writes(self):
        agents = self.root / "AGENTS.md"
        original = b"# Existing\n[Broken](missing.md)\n"
        agents.write_bytes(original)
        errors, _ = setup_module.setup(self.root, claude_md=True, copilot_instructions=True)
        self.assertTrue(any("Pre-existing:" in e and "missing link destination" in e for e in errors), errors)
        self.assertEqual(agents.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [agents])

    def test_missing_optional_map_link_prevents_creation(self):
        self.assertEqual(setup_module.setup(self.root)[0], [])
        agents = self.root / "AGENTS.md"
        index = self.root / ".context-routing" / "index.md"
        original = {path: path.read_bytes() for path in (agents, index)}
        errors, _ = setup_module.setup(self.root, include_skills=True)
        self.assertTrue(any("Proposed setup:" in e and "must link to skills.md" in e for e in errors), errors)
        self.assertEqual({path: path.read_bytes() for path in original}, original)
        self.assertFalse((index.parent / "skills.md").exists())

    def test_changed_observed_file_prevents_publication(self):
        agents = self.root / "AGENTS.md"
        agents.write_text("# Existing\n", encoding="utf-8")
        real_validate = validate_module.validate

        def mutate_after_validation(*args, **kwargs):
            result = real_validate(*args, **kwargs)
            agents.write_text("# User edit\n", encoding="utf-8")
            return result

        with patch.object(validate_module, "validate", side_effect=mutate_after_validation):
            errors, _ = setup_module.setup(self.root)
        self.assertTrue(any("changed after validation" in e for e in errors), errors)
        self.assertEqual(agents.read_text(encoding="utf-8"), "# User edit\n")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_file_created_after_preflight_prevents_publication(self):
        agents = self.root / "AGENTS.md"
        real_preflight = setup_module._preflight

        def mutate_after_preflight(*args):
            result = real_preflight(*args)
            agents.write_text("# User file\n", encoding="utf-8")
            return result

        with patch.object(setup_module, "_preflight", side_effect=mutate_after_preflight):
            errors, _ = setup_module.setup(self.root)
        self.assertTrue(any("changed during setup preflight" in e for e in errors), errors)
        self.assertEqual(agents.read_text(encoding="utf-8"), "# User file\n")
        self.assertFalse((self.root / ".context-routing").exists())

    def test_changed_linked_context_prevents_publication(self):
        self.assertEqual(setup_module.setup(self.root)[0], [])
        folder = self.root / "src"
        folder.mkdir()
        context = folder / "CONTEXT.md"
        context.write_text("# Context\nSource details.\n", encoding="utf-8")
        index = self.root / ".context-routing" / "index.md"
        index.write_text(
            "| Folder | What's there | Context file |\n|---|---|---|\n"
            "| `src` | Source | [Context](../src/CONTEXT.md) |\n",
            encoding="utf-8",
        )
        real_validate = validate_module.validate

        def mutate_after_validation(*args, **kwargs):
            result = real_validate(*args, **kwargs)
            context.write_text("# Context\nUser edit.\n", encoding="utf-8")
            return result

        with patch.object(validate_module, "validate", side_effect=mutate_after_validation):
            errors, _ = setup_module.setup(self.root, claude_md=True)
        self.assertTrue(any("changed after validation" in e and "CONTEXT.md" in e for e in errors), errors)
        self.assertEqual(context.read_text(encoding="utf-8"), "# Context\nUser edit.\n")
        self.assertFalse((self.root / "CLAUDE.md").exists())

    def test_write_failure_reports_partial_files_without_undoing_user_edits(self):
        agents = self.root / "AGENTS.md"
        real_open = Path.open

        def fail_index(path, *args, **kwargs):
            if path.name == "index.md" and args and args[0] == "xb":
                agents.write_text("# Concurrent user edit\n", encoding="utf-8")
                raise OSError("simulated write failure")
            return real_open(path, *args, **kwargs)

        with patch.object(Path, "open", autospec=True, side_effect=fail_index):
            errors, _ = setup_module.setup(self.root)
        self.assertTrue(any("simulated write failure" in e and "AGENTS.md" in e for e in errors), errors)
        self.assertTrue(any("no automatic file rollback" in e for e in errors), errors)
        self.assertEqual(agents.read_text(encoding="utf-8"), "# Concurrent user edit\n")


if __name__ == "__main__":
    unittest.main()
