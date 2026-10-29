"""Testes sem rede, microfone, câmera ou WhatsApp aberto."""
import struct
import unittest

from home_safety import (
    AlertPending, SafetySession, SoundLevelDetector, validate_contact
)
from home_safety_dialog import rms_pcm16le, whatsapp_draft_url
from camera_motion import BLOCK_SIZE, MotionChangeDetector


class SafetySessionTests(unittest.TestCase):
    def test_consent_and_expiration(self):
        session = SafetySession()
        self.assertFalse(session.active)
        with self.assertRaises(PermissionError):
            session.begin(approved=False, contact="5534999999999")
        self.assertFalse(session.active)
        session.begin(approved=True, contact="+55 (34) 99999-9999",
                      listen_to_loud_sounds=True, seconds=30, now=10)
        self.assertTrue(session.microphone_enabled)
        self.assertEqual(session.check(now=12), "5534999999999")
        with self.assertRaises(PermissionError):
            session.check(now=40)
        self.assertFalse(session.microphone_enabled)

    def test_contact_is_validated_and_never_saved(self):
        for value in (None, "", "abc", "123", "+0 1111 2222", "whatsapp:123",
                      "5511999999999?text=hello"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_contact(value)
        self.assertEqual(validate_contact("55 (34) 99999-9999"), "5534999999999")

    def test_safety_can_be_sos_only(self):
        session = SafetySession()
        session.begin(approved=True, contact="5534999999999",
                      listen_to_loud_sounds=False, now=3)
        self.assertTrue(session.active)
        self.assertFalse(session.microphone_enabled)
        session.stop()
        self.assertFalse(session.active)

    def test_loud_sound_multiple_blocks_and_quiet_rearm(self):
        detector = SoundLevelDetector(
            required=3, quiet_to_rearm=2, cooldown_seconds=5
        )
        self.assertFalse(detector.observe(.1, now=0))
        self.assertFalse(detector.observe(.7, now=1))
        self.assertFalse(detector.observe(.7, now=2))
        self.assertTrue(detector.observe(.7, now=3))
        self.assertFalse(detector.observe(.9, now=4))
        detector.observe(.0, now=5)
        detector.observe(.0, now=6)
        self.assertFalse(detector.observe(.9, now=7))
        self.assertFalse(detector.observe(.9, now=8))
        self.assertTrue(detector.observe(.9, now=9))
        self.assertFalse(detector.observe(float("nan"), now=12))

    def test_pending_alert_can_be_cancelled_before_draft(self):
        pending = AlertPending()
        self.assertTrue(pending.schedule(now=100))
        self.assertTrue(pending.pending)
        self.assertFalse(pending.ready(now=114))
        pending.cancel()
        self.assertFalse(pending.consume_if_ready(now=120))
        pending.schedule(now=140)
        self.assertTrue(pending.consume_if_ready(now=155))
        self.assertFalse(pending.pending)

    def test_rms_uses_only_magnitude_and_does_not_store_audio(self):
        self.assertEqual(rms_pcm16le(b""), 0.0)
        self.assertEqual(rms_pcm16le(struct.pack("<hhhh", 0, 0, 0, 0)), 0.0)
        maximum = rms_pcm16le(struct.pack("<hhhh", 32767, -32768, 32767, -32768))
        self.assertGreater(maximum, .99)
        self.assertLessEqual(maximum, 1)
        self.assertEqual(rms_pcm16le(b"\x00"), 0.0)

    def test_whatsapp_is_only_a_draft_not_a_message_send(self):
        url = whatsapp_draft_url("+55 34 99999-9999", "sos")
        self.assertTrue(url.startswith("https://wa.me/5534999999999?text="))
        from urllib.parse import unquote
        self.assertIn("SOS", unquote(url))
        with self.assertRaises(ValueError):
            whatsapp_draft_url("5534999999999", "unknown")


class MotionDetectorTests(unittest.TestCase):
    def test_dark_to_bright_sequence_triggers_without_frames_saved(self):
        detector = MotionChangeDetector(required=2, cooldown_seconds=20)
        dark, bright = bytes(BLOCK_SIZE), bytes([250]) * BLOCK_SIZE
        self.assertFalse(detector.observe(dark, now=0))
        self.assertFalse(detector.observe(bright, now=1))
        self.assertTrue(detector.observe(dark, now=2))
        self.assertFalse(detector.observe(bright, now=3))
        detector.reset()
        self.assertFalse(detector.observe(dark, now=20))

    def test_rejects_full_images_and_small_fluctuations(self):
        detector = MotionChangeDetector(required=2)
        with self.assertRaises(ValueError):
            detector.observe(b"HD full image")
        dark, slight = bytes(BLOCK_SIZE), bytes([15]) * BLOCK_SIZE
        self.assertFalse(detector.observe(dark, now=0))
        for i in range(5):
            self.assertFalse(detector.observe(slight if i % 2 else dark, now=1+i))
