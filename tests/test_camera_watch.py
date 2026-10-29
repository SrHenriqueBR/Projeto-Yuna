import unittest

from camera_commands import is_camera_view_request
from camera_watch import (
    CameraPermission, MAX_CAMERA_SESSION_SECONDS,
    parse_camera_source,
)


class CameraWatchTests(unittest.TestCase):
    def test_explicit_webcam_numbers(self):
        for text, expected in (("0", 0), ("webcam 1", 1),
                               ("camera 2", 2), ("câmera 9", 9)):
            with self.subTest(text=text):
                source = parse_camera_source(text)
                self.assertEqual(source.kind, "webcam")
                self.assertEqual(source.index, expected)
                self.assertIsNone(source.url)

    def test_rtsp_private_ip_with_optional_credentials(self):
        for url in (
            "rtsp://192.168.1.50:554/stream1",
            "rtsp://admin:secret@10.0.0.15/live",
            "rtsp://172.16.0.25:8554/profile",
        ):
            self.assertEqual(parse_camera_source(url).kind, "rtsp")
            self.assertEqual(parse_camera_source(url).url, url)

    def test_public_non_rtsp_and_remote_sources_rejected(self):
        sources = [
            "https://example.com/cam", "http://192.168.1.50/live",
            "rtsp://8.8.8.8/live", "rtsp://127.0.0.1/live",
            "rtsp://example.com/live", "rtsp://169.254.10.20/live",
            "rtsp://192.168.1.50", "rtsp://192.168.1.50:99999/live",
            "rtsp://192.168.1.50/live#fragment",
            "rtsp://admin:secret@www.example.com/stream",
            "webcam -1", "webcam 12", "", None, "rtsp://192.168.1.5/stream\nleak"
        ]
        for text in sources:
            with self.subTest(text=text), self.assertRaises(ValueError) as caught:
                parse_camera_source(text)
            self.assertNotIn("secret", str(caught.exception))

    def test_requires_per_session_approval_and_expires(self):
        permit = CameraPermission()
        with self.assertRaises(PermissionError):
            permit.check(now=10)
        with self.assertRaises(PermissionError):
            permit.authorize("0", approved=False, now=10)
        source = permit.authorize("0", approved=True, now=10, duration_seconds=4)
        self.assertEqual(source.index, 0)
        self.assertEqual(permit.check(now=12), source)
        self.assertEqual(permit.remaining(now=12), 2)
        with self.assertRaises(PermissionError):
            permit.check(now=14)
        with self.assertRaises(PermissionError):
            permit.check(now=15)
        self.assertEqual(permit.remaining(now=16), 0)

    def test_time_cap_and_stop_code(self):
        permit = CameraPermission()
        for duration in (-1, 0, MAX_CAMERA_SESSION_SECONDS + 1, "10", float("nan"), True):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                permit.authorize("0", approved=True, duration_seconds=duration)
        permit.authorize("0", approved=True)
        self.assertFalse(permit.request_stop("I typed Break080111 in a note"))
        self.assertTrue(permit.request_stop("Break080111"))
        with self.assertRaises(PermissionError):
            permit.check()

    def test_user_command_opens_selector_only(self):
        positive = [
            "Yuna, mostre a câmera da garagem",
            "Abra a webcam",
            "Quero ver a camera",
            "Yuna, consegue mostrar a camera",
            "Mostre as câmeras",
        ]
        for phrase in positive:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_camera_view_request(phrase))
        for phrase in (
            "O que você acha das câmeras?",
            "não abra a câmera",
            "As câmeras podem ser perigosas",
            "Yuna, leia um documento sobre câmeras",
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_camera_view_request(phrase))


if __name__ == "__main__":
    unittest.main()
