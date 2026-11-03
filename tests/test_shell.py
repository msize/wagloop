import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "Git Bash is required")
class ShellTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.checkout = self.root / "checkout space"
        self.checkout.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.workbench = self.root / "agworkbench"
        (self.workbench / "lib").mkdir(parents=True)
        (self.workbench / "lib/agmsg.py").touch()
        self.stubs = self.root / "stubs"
        self.stubs.mkdir()
        self.env = dict(os.environ, HOME=self.home.as_posix(), AGWORKBENCH=self.workbench.as_posix(),
                        TEST_BIN=self.stubs.as_posix(), TEST_ROOT=self.checkout.as_posix(),
                        TEST_LOG=self.root.as_posix(), CODEX_REVIEW_SKILL="$plugin:review",
                        CLAUDE_REVIEW_SKILL="/plugin:review", DEVIN_REVIEW_SKILL="review")
        self.stub("git", 'printf "%s\\n" "$TEST_ROOT"')
        self.stub("python", 'printf "%s\\0" "$@" > "$TEST_LOG/python.args"')
        for tool in ("claude", "codex", "devin"):
            self.stub(tool, f'printf "%s\\0" "$@" > "$TEST_LOG/{tool}.args"')

    def stub(self, name, body):
        target = self.stubs / name
        target.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8")
        target.chmod(0o755)

    def run_script(self, script, *args, stubs=True):
        prefix = 'export PATH="$(cygpath -u "$TEST_BIN"):$PATH"; ' if stubs else ""
        return subprocess.run([BASH, "-c", prefix + 'exec bash "$@"', "test", str(script), *args],
                              cwd=self.checkout, env=self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=30)

    def arguments(self, tool):
        return (self.root / f"{tool}.args").read_bytes().decode("utf-8").rstrip("\0").split("\0")

    def install_devin_skill(self, role):
        target = self.home / f".config/devin/skills/agrevloop-{role}/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("test skill", encoding="utf-8")

    def test_scripts_parse(self):
        for script in (ROOT / "install.sh", *sorted((ROOT / "bin").glob("agrevloop-*"))):
            with self.subTest(script=script.name):
                result = subprocess.run([BASH, "-n", str(script)], capture_output=True, text=True,
                                        encoding="utf-8", timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_devin_author_defaults_and_passthrough(self):
        self.install_devin_skill("author")
        result = self.run_script(ROOT / "bin/agrevloop-devin", "author", "add retry", "--",
                                 "--model", "test-model")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.arguments("python")[-7:],
                         ["--as", "author", "init", "--tool", "devin", "--with", "codex"])
        args = self.arguments("devin")
        self.assertEqual(args[:3], ["--model", "test-model", "--"])
        self.assertIn("add retry", args[-1])
        self.assertIn(".config/devin/skills/agrevloop-author/SKILL.md", args[-1])
        self.assertFalse(any("permission" in arg or "sandbox" in arg for arg in args[:-1]))

    def test_devin_reviewer(self):
        self.install_devin_skill("reviewer")
        result = self.run_script(ROOT / "bin/agrevloop-devin", "reviewer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.arguments("python")[-5:], ["--as", "reviewer", "init", "--tool", "devin"])
        self.assertIn("unread mail", self.arguments("devin")[-1])

    def test_devin_author_partners(self):
        self.install_devin_skill("author")
        for partner in ("claude", "codex", "devin"):
            with self.subTest(partner=partner):
                result = self.run_script(ROOT / "bin/agrevloop-devin", "author", f"with={partner}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.arguments("python")[-2:], ["--with", partner])

    def test_existing_launchers_accept_devin(self):
        for tool in ("claude", "codex"):
            with self.subTest(tool=tool):
                result = self.run_script(ROOT / f"bin/agrevloop-{tool}", "author", "with=devin")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.arguments("python")[-2:], ["--with", "devin"])
                if tool == "codex":
                    args = self.arguments("codex")
                    self.assertIn("workspace-write", args)
                    self.assertIn("never", args)
                    self.assertIn("sandbox_workspace_write.network_access=false", args)

    def test_invalid_arguments_do_not_initialize(self):
        self.install_devin_skill("author")
        self.install_devin_skill("reviewer")
        for args in ((), ("unknown",), ("author", "with=invalid"), ("reviewer", "extra")):
            with self.subTest(args=args):
                result = self.run_script(ROOT / "bin/agrevloop-devin", *args)
                self.assertEqual(result.returncode, 2)
                self.assertFalse((self.root / "python.args").exists())

    def test_missing_skill_does_not_initialize(self):
        result = self.run_script(ROOT / "bin/agrevloop-devin", "author")
        self.assertEqual(result.returncode, 2)
        self.assertIn("run install.sh first", result.stderr)
        self.assertFalse((self.root / "python.args").exists())

    def test_init_failure_does_not_launch_devin(self):
        self.install_devin_skill("author")
        self.stub("python", "exit 7")
        result = self.run_script(ROOT / "bin/agrevloop-devin", "author")
        self.assertEqual(result.returncode, 7)
        self.assertFalse((self.root / "devin.args").exists())

    def test_installer_renders_all_skills_and_can_repeat(self):
        shutil.copy2(ROOT / "install.sh", self.checkout)
        for folder in ("skills", "bin"):
            shutil.copytree(ROOT / folder, self.checkout / folder)
        for _ in range(2):
            result = self.run_script(self.checkout / "install.sh", stubs=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        for tool, folder, review in (("claude", ".claude", "/plugin:review"),
                                     ("codex", ".codex", "$plugin:review"),
                                     ("devin", ".config/devin", "review")):
            for role in ("author", "reviewer"):
                with self.subTest(tool=tool, role=role):
                    text = (self.home / folder / f"skills/agrevloop-{role}/SKILL.md").read_text(encoding="utf-8")
                    self.assertNotIn("@AGR@", text)
                    self.assertNotIn("@BIN@", text)
                    self.assertNotIn("@REVIEW_SKILL@", text)
                    if role == "reviewer":
                        self.assertIn(review, text)
        self.assertIn("agrevloop-devin", result.stdout)

    def test_installer_requires_devin_review_skill_before_writes(self):
        del self.env["DEVIN_REVIEW_SKILL"]
        result = self.run_script(ROOT / "install.sh", stubs=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEVIN_REVIEW_SKILL", result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
