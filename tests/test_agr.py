import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agr", ROOT / "bin" / "agr.py")
agr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agr)


class AgrTests(unittest.TestCase):
    def test_devin_is_supported(self):
        self.assertIn("devin", agr.TOOLS)

    def test_deferred_start_for_devin_author(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mailbox = root / ".agrevloop"
            mailbox.mkdir()
            (mailbox / "pair.json").write_text('{"reviewer": "codex"}', encoding="utf-8")
            env = {"AI_HUB": str(mailbox)}
            filed = Mock(returncode=0, stderr="")
            with patch.object(agr, "tool_of", side_effect=["devin", None]), \
                    patch.object(agr, "load"), \
                    patch.object(agr, "peer_pane", return_value=("peer", False)), \
                    patch.object(agr, "wait_shell", return_value="bash"), \
                    patch.object(agr.subprocess, "run", return_value=filed) as run, \
                    patch.object(agr, "start_reviewer") as start:
                self.assertEqual(agr.send("author", ["--to", "reviewer"], root, env), 0)
                self.assertIn("--force", run.call_args.args[0])
                start.assert_called_once()
                self.assertEqual(start.call_args.args[4], "codex")

    def test_send_matrix(self):
        for sender in ("claude", "codex", "devin"):
            for recipient in ("claude", "codex", "devin"):
                with self.subTest(sender=sender, recipient=recipient), \
                        patch.object(agr, "tool_of", side_effect=[sender, recipient]), \
                        patch.object(agr, "read_pair", return_value={}), \
                        patch.object(agr, "run", return_value=0) as run:
                    if sender == recipient == "codex":
                        with self.assertRaises(SystemExit):
                            agr.send("reviewer", ["--to", "author"], ROOT, {"AI_HUB": str(ROOT)})
                        run.assert_not_called()
                    else:
                        self.assertEqual(agr.send("reviewer", ["--to", "author"],
                                                  ROOT, {"AI_HUB": str(ROOT)}), 0)
                        self.assertEqual("--nudge" in run.call_args.args[1], recipient == "codex")

    def test_init_registers_devin_without_agmsg_choice_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = Mock()
            hub.lookup.return_value = {}
            agw = Mock()
            with patch.object(agr.subprocess, "run", side_effect=[
                    Mock(returncode=0, stdout=str(root)),
                    Mock(returncode=0, stdout=".git/info/exclude")]), \
                    patch.object(agr, "load", side_effect=lambda lib, name, env: hub if name == "hub" else agw), \
                    patch.object(agr, "own_session", return_value=("mine", {})), \
                    patch.object(agr, "peer_pane", return_value=("peer", False)), \
                    patch.object(agr, "wait_shell", return_value="bash"), \
                    patch.object(agr, "start_reviewer") as start:
                self.assertEqual(agr.init("author", ["--tool", "devin", "--with", "devin"], ROOT), 0)
                hub.register.assert_called_once_with("author", tool="devin", role="author", cwd=str(root))
                start.assert_not_called()
                self.assertEqual(json.loads((root / ".agrevloop/pair.json").read_text()), {"reviewer": "devin"})

    def test_codex_can_start_devin_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = Mock()
            hub.lookup.return_value = {}
            with patch.object(agr.subprocess, "run", side_effect=[
                    Mock(returncode=0, stdout=str(root)),
                    Mock(returncode=0, stdout=".git/info/exclude")]), \
                    patch.object(agr, "run", return_value=0), \
                    patch.object(agr, "load", return_value=hub), \
                    patch.object(agr, "own_session", return_value=("mine", {})), \
                    patch.object(agr, "peer_pane", return_value=("peer", False)), \
                    patch.object(agr, "wait_shell", return_value="bash"), \
                    patch.object(agr, "start_reviewer") as start:
                self.assertEqual(agr.init("author", ["--tool", "codex", "--with", "devin"], ROOT), 0)
                self.assertEqual(start.call_args.args[4], "devin")

    def test_codex_pair_rejected(self):
        with patch.object(agr.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                agr.init("author", ["--tool", "codex", "--with", "codex"], ROOT)
            run.assert_not_called()

    def test_devin_status(self):
        agw = Mock()
        with patch.object(agr, "workbench_lib", return_value=ROOT), \
                patch.object(agr, "hub_dir", return_value=ROOT), \
                patch.object(agr, "tool_of", return_value="devin"), \
                patch.object(agr, "load", return_value=agw):
            self.assertEqual(agr.main(["--as", "reviewer", "status", "blocked", "--sound"]), 0)
            agw.set_status.assert_called_once_with("blocked", sound=True)

    def test_devin_reviewer_command(self):
        command = agr.start_command("devin", ROOT, "bash")
        self.assertIn("agrevloop-devin", command)
        self.assertTrue(command.endswith(" reviewer"))


if __name__ == "__main__":
    unittest.main()
