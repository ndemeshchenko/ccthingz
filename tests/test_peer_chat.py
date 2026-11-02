"""Routing tests for plugins/peer-chat/bin/peer-chat. Run: python3 -m unittest discover tests"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/peer-chat/bin/peer-chat"
_loader = importlib.machinery.SourceFileLoader("peer_chat", str(SCRIPT))
_spec = importlib.util.spec_from_loader("peer_chat", _loader)
pc = importlib.util.module_from_spec(_spec)
sys.modules["peer_chat"] = pc  # @dataclass looks its module up here
_loader.exec_module(pc)

ME = pc.Agent("claude", None, "w2:p1", "w2:t1", "working")
LOCAL_CODEX = pc.Agent("codex", None, "w2:p2", "w2:t1", "idle")
REMOTE_CODEX_NAMED = pc.Agent("codex", "codex", "w1:p1", "w1:t1", "idle")
REMOTE_REVIEWER = pc.Agent("codex", "reviewer", "w1:p2", "w1:t1", "idle")


def resolve(population, spec, me=ME, tab=None):
    return pc.resolve_peer(population, spec, me, tab)


class ResolvePeer(unittest.TestCase):
    def test_kind_stays_in_tab_when_another_tab_has_that_name(self):
        peer = resolve([ME, LOCAL_CODEX, REMOTE_CODEX_NAMED], "codex")
        self.assertEqual(peer.pane_id, LOCAL_CODEX.pane_id)

    def test_name_only_in_another_tab_refuses_with_route_hint(self):
        with self.assertRaises(pc.Refused) as ctx:
            resolve([ME, LOCAL_CODEX, REMOTE_REVIEWER], "reviewer")
        message = str(ctx.exception)
        self.assertIn(REMOTE_REVIEWER.pane_id, message)
        self.assertIn(REMOTE_REVIEWER.tab_id, message)

    def test_tab_flag_scopes_name_to_that_tab(self):
        peer = resolve([ME, LOCAL_CODEX, REMOTE_REVIEWER], "reviewer", tab="w1:t1")
        self.assertEqual(peer.pane_id, REMOTE_REVIEWER.pane_id)

    def test_explicit_pane_id_reaches_another_tab(self):
        peer = resolve([ME, LOCAL_CODEX, REMOTE_REVIEWER], REMOTE_REVIEWER.pane_id)
        self.assertEqual(peer.pane_id, REMOTE_REVIEWER.pane_id)

    def test_name_in_tab_beats_kind_ambiguity(self):
        named = pc.Agent("codex", "codex", "w2:p3", "w2:t1", "idle")
        peer = resolve([ME, LOCAL_CODEX, named], "codex")
        self.assertEqual(peer.pane_id, named.pane_id)

    def test_ambiguous_local_kind_refuses_despite_remote_name(self):
        other = pc.Agent("codex", None, "w2:p3", "w2:t1", "idle")
        with self.assertRaises(pc.Refused) as ctx:
            resolve([ME, LOCAL_CODEX, other, REMOTE_CODEX_NAMED], "codex")
        self.assertIn("more than one", str(ctx.exception))

    def test_refuses_own_pane(self):
        with self.assertRaises(pc.Refused):
            resolve([ME, LOCAL_CODEX], ME.pane_id)

    def test_no_scope_refuses_kind_and_name(self):
        me = pc.Agent("claude", None, "", "", "unknown")
        for spec in ("codex", "reviewer"):
            with self.subTest(spec=spec), self.assertRaises(pc.Refused):
                resolve([LOCAL_CODEX, REMOTE_REVIEWER], spec, me=me)

    def test_no_scope_still_accepts_pane_id(self):
        me = pc.Agent("claude", None, "", "", "unknown")
        peer = resolve([LOCAL_CODEX, REMOTE_REVIEWER], REMOTE_REVIEWER.pane_id, me=me)
        self.assertEqual(peer.pane_id, REMOTE_REVIEWER.pane_id)


class Delivery(unittest.TestCase):
    def run_main(self, *argv):
        calls = []
        population = [ME, LOCAL_CODEX, REMOTE_CODEX_NAMED]

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("agent", "list"):
                return {"result": {"agents": [
                    {"agent": a.kind, "name": a.name, "pane_id": a.pane_id,
                     "tab_id": a.tab_id, "agent_status": a.status} for a in population]}}
            return {}

        out = io.StringIO()
        env = {"HERDR_ENV": "1", "HERDR_PANE_ID": ME.pane_id}
        with mock.patch.object(pc, "herdr", fake_herdr), \
                mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
            code = pc.main(list(argv))
        self.assertEqual(code, 0)
        return [json.loads(line) for line in out.getvalue().splitlines()], calls

    def test_prompt_targets_pane_id_and_output_names_pane_and_tab(self):
        (result,), calls = self.run_main("--to", "codex", "--message", "hi", "--no-confirm")
        prompt = [c for c in calls if c[:2] == ("agent", "prompt")]
        self.assertEqual(prompt[0][2], LOCAL_CODEX.pane_id)
        self.assertEqual(result["pane_id"], LOCAL_CODEX.pane_id)
        self.assertEqual(result["tab_id"], LOCAL_CODEX.tab_id)

    def test_dry_run_shows_pane_and_tab(self):
        (result, _), calls = self.run_main("--to", "codex", "--message", "hi", "--dry-run")
        self.assertFalse([c for c in calls if c[:2] == ("agent", "prompt")])
        self.assertEqual(result["target"], LOCAL_CODEX.pane_id)
        self.assertEqual(result["tab_id"], LOCAL_CODEX.tab_id)


if __name__ == "__main__":
    unittest.main()
