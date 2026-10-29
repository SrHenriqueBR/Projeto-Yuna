"""Magi1020 é comando de convite, jamais autorização para webcam remota."""
import unittest
from urllib.parse import urlsplit
from remote_camera_invite import (
    EXTERNAL_MEETING_SERVICE, ROOM_PREFIX,
    is_magi_camera_request, new_remote_camera_invite,
    validate_remote_camera_invite,
)


class MagiCameraInviteTests(unittest.TestCase):
    def test_standalone_command_only(self):
        for phrase in ("Magi1020", "magi1020", "Yuna, Magi1020",
                       "YUNA: MAGI1020!", "Yuna Magi1020"):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_magi_camera_request(phrase))
        for phrase in ("lembra Magi1020?", "não abra a câmera: Magi1020",
                       "Magi1020 senha", "Magi10200",
                       "Magi1020, abra sem avisar", "Break080111", "", None):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_magi_camera_request(phrase))

    def test_unique_high_entropy_meeting_links(self):
        links = {new_remote_camera_invite() for _ in range(24)}
        self.assertEqual(len(links), 24)
        for link in links:
            self.assertEqual(validate_remote_camera_invite(link), link)
            self.assertTrue(link.startswith(EXTERNAL_MEETING_SERVICE + "/" + ROOM_PREFIX))
            parts = urlsplit(link)
            self.assertEqual(parts.hostname, "meet.jit.si")
            self.assertFalse(parts.query)
            self.assertFalse(parts.fragment)
            self.assertEqual(len(parts.path.split("-")[-1]), 32)

    def test_only_expected_invite_host_and_random_room(self):
        valid = new_remote_camera_invite()
        invalid = (
            valid.replace("https:", "http:", 1),
            valid.replace("meet.jit.si", "evil.example", 1),
            valid.replace("meet.jit.si", "meet.jit.si.evil.example", 1),
            valid.replace("https://", "https://admin@", 1),
            valid.replace("https://meet.jit.si", "https://meet.jit.si:443", 1),
            valid + "#keep-camera-on",
            valid + "?autostart=1",
            valid.replace(ROOM_PREFIX, "Camera-"),
            valid + "/another-path",
            "https://meet.jit.si/YunaVisita-Magi1020",
            "javascript:alert(1)",
            "rtsp://192.168.1.20/stream",
            "https://meet.jit.si",
            valid + "\nmalicious",
            None,
            "",
        )
        for link in invalid:
            with self.subTest(link=link), self.assertRaises(ValueError):
                validate_remote_camera_invite(link)

    def test_token_is_not_code_and_cannot_grant_camera_permission(self):
        self.assertTrue(is_magi_camera_request("Magi1020"))
        self.assertNotIn("Magi1020", new_remote_camera_invite())
        # O convite só contém um endereço, não há funções de webcam no módulo.
        import remote_camera_invite
        self.assertFalse(hasattr(remote_camera_invite, "activate_remote_webcam"))
        self.assertFalse(hasattr(remote_camera_invite, "stream_camera"))


if __name__ == "__main__":
    unittest.main()
