"""Autorização de jogos sem qualquer envio de inputs reais."""
import unittest

from game_sessions import (
    ACTIONS, MAX_ACTIONS_PER_SESSION, GameSession,
    normalize_executable,
)

GAME = r"C:\Games\Demo\Game.exe"
OTHER = r"C:\Windows\System32\notepad.exe"


class GameSessionTests(unittest.TestCase):
    def test_no_actions_without_explicit_permission(self):
        session = GameSession()
        self.assertFalse(session.active)
        with self.assertRaises(PermissionError):
            session.propose("jump", foreground_executable=GAME, now=0)
        with self.assertRaises(PermissionError):
            session.authorize(GAME, approved=False, single_player=True, now=0)
        with self.assertRaises(PermissionError):
            session.authorize(GAME, approved=True, single_player=False, now=0)
        self.assertFalse(session.active)

    def test_game_executable_must_be_local_absolute_file(self):
        for name in ("game.exe", r"\\nas\shared\game.exe",
                     r"C:\Games\..\system.exe", r"C:\Games\demo.bat",
                     r"C:\Games\run.exe | calc", "", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                normalize_executable(name)
        self.assertEqual(normalize_executable(GAME), GAME.lower())

    def test_only_approved_foreground_game_can_be_proposed(self):
        session = GameSession()
        self.assertTrue(session.authorize(
            GAME, approved=True, single_player=True, now=100))
        action = session.propose("move_forward", foreground_executable=GAME,
                                 seconds=0.12, now=101)
        self.assertEqual(action.action, "move_forward")
        self.assertEqual(action.game_executable, GAME.lower())
        self.assertAlmostEqual(action.seconds, 0.12)
        with self.assertRaises(PermissionError):
            session.propose("jump", foreground_executable=OTHER, now=102)
        self.assertFalse(session.active)

    def test_short_actions_only_and_expiration(self):
        session = GameSession()
        session.authorize(GAME, approved=True, single_player=True,
                          duration_seconds=2, now=5)
        with self.assertRaises(ValueError):
            session.propose("launch_program", foreground_executable=GAME, now=5)
        for seconds in (0, -1, 1, float("nan"), True):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                session.propose("jump", foreground_executable=GAME,
                                seconds=seconds, now=5.5)
        self.assertEqual(session.propose(
            "jump", foreground_executable=GAME, seconds=0.5, now=6).seconds, .5)
        with self.assertRaises(PermissionError):
            session.propose("jump", foreground_executable=GAME, now=7)
        self.assertFalse(session.active)

    def test_all_actions_are_whitelisted_and_bounded(self):
        session = GameSession()
        session.authorize(GAME, approved=True, single_player=True, now=0)
        self.assertIn("pause", ACTIONS)
        self.assertNotIn("alt_f4", ACTIONS)
        for _ in range(MAX_ACTIONS_PER_SESSION):
            session.propose("move_left", foreground_executable=GAME, now=1)
        with self.assertRaises(PermissionError):
            session.propose("move_left", foreground_executable=GAME, now=1)
        self.assertFalse(session.active)

    def test_emergency_stop_break080111_revokes_access(self):
        session = GameSession()
        session.authorize(GAME, approved=True, single_player=True, now=0)
        self.assertFalse(session.request_stop("I might say break080111 later"))
        self.assertTrue(session.active)
        self.assertTrue(session.request_stop("Break080111"))
        self.assertFalse(session.active)
        with self.assertRaises(PermissionError):
            session.propose("jump", foreground_executable=GAME, now=1)

    def test_reauthorization_after_explicit_stop(self):
        session = GameSession()
        session.authorize(GAME, approved=True, single_player=True, now=0)
        session.stop()
        self.assertFalse(session.active)
        session.authorize(GAME, approved=True, single_player=True, now=10)
        self.assertTrue(session.active)


if __name__ == "__main__":
    unittest.main()
