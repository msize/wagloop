import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wagloop", ROOT / "bin" / "wagloop.py")
wagloop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wagloop)


class WagloopTests(unittest.TestCase):
    def test_mailbox_name(self):
        self.assertEqual(wagloop.HUB_DIR, ".wagloop")
        self.assertEqual(wagloop.EXCLUDED, ("/.wagloop/", "/review-runs/"))

    def test_transport_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lib = root / "lib"
            lib.mkdir()
            (lib / "wagmsg.py").touch()
            with patch.dict(os.environ, {"WAGFLOW": str(root)}, clear=True):
                self.assertEqual(wagloop.flow_lib(), lib)

    def test_default_transport_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lib = root / "wagflow/lib"
            lib.mkdir(parents=True)
            (lib / "wagmsg.py").touch()
            with patch.dict(os.environ, {}, clear=True), \
                    patch.object(wagloop, "__file__", str(root / "wagloop/bin/wagloop.py")):
                self.assertEqual(wagloop.flow_lib(), lib.resolve())

    def test_transport_environment(self):
        env = wagloop.env_for("author", ROOT / ".wagloop", ROOT / "lib")
        self.assertEqual(env["WAGFLOW"], str(ROOT))
        self.assertEqual(env["AI_HUB"], str(ROOT / ".wagloop"))
        self.assertEqual(env["AI_BOX"], "author")

    def test_git_bash_override(self):
        with patch.dict(os.environ, {"WAGLOOP_BASH": "C:/Git/bin/bash.exe"}, clear=True), \
                patch.object(wagloop.subprocess, "run") as run:
            self.assertEqual(wagloop.git_bash(), "C:/Git/bin/bash.exe")
            run.assert_not_called()

    def test_mailbox_found_from_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".wagloop").mkdir()
            nested = root / "src"
            nested.mkdir()
            with patch.dict(os.environ, {}, clear=True), \
                    patch.object(wagloop.Path, "cwd", return_value=nested):
                self.assertEqual(wagloop.hub_dir(), root / ".wagloop")

    def test_wait_uses_flow_waiter(self):
        with patch.object(wagloop, "flow_lib", return_value=ROOT / "lib"), \
                patch.object(wagloop, "hub_dir", return_value=ROOT / ".wagloop"), \
                patch.object(wagloop, "run", return_value=3) as run:
            self.assertEqual(wagloop.main(["--as", "author", "wait", "--timeout", "4"]), 3)
            self.assertEqual(run.call_args.args[:2],
                             (ROOT / "lib/wb.py", ["wait-mail", "--box", "author", "--timeout", "4"]))
            self.assertEqual(run.call_args.args[2]["WAGFLOW"], str(ROOT))

    def test_mail_commands_use_wagmsg(self):
        with patch.object(wagloop, "flow_lib", return_value=ROOT / "lib"), \
                patch.object(wagloop, "hub_dir", return_value=ROOT / ".wagloop"), \
                patch.object(wagloop, "run", return_value=0) as run:
            self.assertEqual(wagloop.main(["--as", "reviewer", "list"]), 0)
            self.assertEqual(run.call_args.args[:2],
                             (ROOT / "lib/wagmsg.py", ["list", "--box", "reviewer"]))

    def test_devin_is_supported(self):
        self.assertIn("devin", wagloop.TOOLS)

    def test_deferred_start_for_devin_author(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mailbox = root / ".wagloop"
            mailbox.mkdir()
            (mailbox / "pair.json").write_text('{"reviewer": "codex"}', encoding="utf-8")
            env = {"AI_HUB": str(mailbox)}
            filed = Mock(returncode=0, stderr="")
            with patch.object(wagloop, "tool_of", side_effect=["devin", None]), \
                    patch.object(wagloop, "load"), \
                    patch.object(wagloop, "peer_pane", return_value=("peer", False)), \
                    patch.object(wagloop, "wait_shell", return_value="bash"), \
                    patch.object(wagloop.subprocess, "run", return_value=filed) as run, \
                    patch.object(wagloop, "start_reviewer") as start:
                self.assertEqual(wagloop.send("author", ["--to", "reviewer"], root, env), 0)
                self.assertEqual(run.call_args.args[0][1], str(root / "wagmsg.py"))
                self.assertIn("--force", run.call_args.args[0])
                start.assert_called_once()
                self.assertEqual(start.call_args.args[4], "codex")

    def test_send_matrix(self):
        for sender in ("claude", "codex", "devin"):
            for recipient in ("claude", "codex", "devin"):
                with self.subTest(sender=sender, recipient=recipient), \
                        patch.object(wagloop, "tool_of", side_effect=[sender, recipient]), \
                        patch.object(wagloop, "read_pair", return_value={}), \
                        patch.object(wagloop, "run", return_value=0) as run:
                    if sender == recipient == "codex":
                        with self.assertRaises(SystemExit):
                            wagloop.send("reviewer", ["--to", "author"], ROOT, {"AI_HUB": str(ROOT)})
                        run.assert_not_called()
                    else:
                        self.assertEqual(wagloop.send("reviewer", ["--to", "author"],
                                                      ROOT, {"AI_HUB": str(ROOT)}), 0)
                        self.assertEqual(run.call_args.args[0], ROOT / "wagmsg.py")
                        self.assertEqual("--nudge" in run.call_args.args[1], recipient == "codex")

    def test_init_registers_devin_without_wagmsg_choice_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = Mock()
            hub.lookup.return_value = {}
            wag = Mock()
            with patch.object(wagloop.subprocess, "run", side_effect=[
                    Mock(returncode=0, stdout=str(root)),
                    Mock(returncode=0, stdout=".git/info/exclude")]), \
                    patch.object(wagloop, "load", side_effect=lambda lib, name, env: hub if name == "hub" else wag), \
                    patch.object(wagloop, "own_session", return_value=("mine", {})), \
                    patch.object(wagloop, "peer_pane", return_value=("peer", False)), \
                    patch.object(wagloop, "wait_shell", return_value="bash"), \
                    patch.object(wagloop, "start_reviewer") as start:
                self.assertEqual(wagloop.init("author", ["--tool", "devin", "--with", "devin"], ROOT), 0)
                hub.register.assert_called_once_with("author", tool="devin", role="author", cwd=str(root))
                start.assert_not_called()
                self.assertEqual(json.loads((root / ".wagloop/pair.json").read_text()), {"reviewer": "devin"})
                self.assertEqual((root / ".git/info/exclude").read_text().splitlines(),
                                 ["/.wagloop/", "/review-runs/"])

    def test_codex_can_start_devin_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = Mock()
            hub.lookup.return_value = {}
            with patch.object(wagloop.subprocess, "run", side_effect=[
                    Mock(returncode=0, stdout=str(root)),
                    Mock(returncode=0, stdout=".git/info/exclude")]), \
                    patch.object(wagloop, "run", return_value=0), \
                    patch.object(wagloop, "load", return_value=hub), \
                    patch.object(wagloop, "own_session", return_value=("mine", {})), \
                    patch.object(wagloop, "peer_pane", return_value=("peer", False)), \
                    patch.object(wagloop, "wait_shell", return_value="bash"), \
                    patch.object(wagloop, "start_reviewer") as start:
                self.assertEqual(wagloop.init("author", ["--tool", "codex", "--with", "devin"], ROOT), 0)
                self.assertEqual(start.call_args.args[4], "devin")

    def test_codex_pair_rejected(self):
        with patch.object(wagloop.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                wagloop.init("author", ["--tool", "codex", "--with", "codex"], ROOT)
            run.assert_not_called()

    def test_devin_status(self):
        wag = Mock()
        with patch.object(wagloop, "flow_lib", return_value=ROOT), \
                patch.object(wagloop, "hub_dir", return_value=ROOT), \
                patch.object(wagloop, "tool_of", return_value="devin"), \
                patch.object(wagloop, "load", return_value=wag) as load:
            self.assertEqual(wagloop.main(["--as", "reviewer", "status", "blocked", "--sound"]), 0)
            wag.set_status.assert_called_once_with("blocked", sound=True)
            self.assertEqual(load.call_args.args[1], "wag")

    def test_devin_reviewer_command(self):
        command = wagloop.start_command("devin", ROOT, "bash")
        self.assertIn("wagloop-devin", command)
        self.assertTrue(command.endswith(" reviewer"))


if __name__ == "__main__":
    unittest.main()
