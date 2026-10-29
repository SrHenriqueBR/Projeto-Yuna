import unittest
from avatar_state import parse_avatar_request


class CuriosityCommandTests(unittest.TestCase):
    def test_explicit_commands(self):
        for phrase in ("Yuna, fica curiosa!", "faz cara de curiosa",
                       "mostra curiosidade"):
            self.assertEqual(parse_avatar_request(phrase), ("pose", "curious"))

    def test_hypothetical_does_not_trigger(self):
        self.assertIsNone(parse_avatar_request("E se você fica curiosa?"))
