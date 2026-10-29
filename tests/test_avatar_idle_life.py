import unittest
from avatar_idle_life import idle_expression


class IdleLifeTests(unittest.TestCase):
    def test_natural_gestures(self):
        self.assertEqual(idle_expression(160), "curious")
        self.assertEqual(idle_expression(340), "happy")
        self.assertEqual(idle_expression(530), "shy")
        self.assertIsNone(idle_expression(200))

    def test_speech_and_explicit_actions_take_priority(self):
        self.assertIsNone(idle_expression(160, speaking=True))
        self.assertIsNone(idle_expression(160, busy=True))

    def test_reduced_motion_disables_extra_gestures(self):
        self.assertIsNone(idle_expression(340, reduced_motion=True))

    def test_invalid_ticks(self):
        self.assertIsNone(idle_expression(None))
        self.assertIsNone(idle_expression(-1))
