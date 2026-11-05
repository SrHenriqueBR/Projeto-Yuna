"""Estados de bandeja conservadores e sem acesso à rede."""
import unittest
from tray_modes import MODES, mode_policy, should_observe, mode_tooltip


class TrayPoliciesTests(unittest.TestCase):
    def test_four_modes_and_no_unexpected_observation(self):
        self.assertEqual(set(MODES), {
            "ativa", "economica", "acompanhamento", "pausada"})
        for mode in ("economica", "pausada"):
            self.assertFalse(should_observe(mode, windows=True, permission=True))
            self.assertFalse(mode_policy(mode).unreal_heartbeat)
        self.assertTrue(should_observe(
            "acompanhamento", windows=True, permission=True))
        self.assertFalse(should_observe(
            "acompanhamento", windows=True, permission=False))
        self.assertFalse(should_observe(
            "acompanhamento", windows=False, permission=True))
        self.assertTrue(should_observe("ativa", windows=True, permission=True))

    def test_timers_economy_and_pause_are_conservative(self):
        active, eco, monitor, paused = [mode_policy(key) for key in
            ("ativa", "economica", "acompanhamento", "pausada")]
        self.assertGreater(eco.timer_ms, active.timer_ms)
        self.assertGreater(eco.battery_ms, active.battery_ms)
        self.assertGreater(monitor.battery_ms, active.battery_ms)
        self.assertIsNone(paused.battery_ms)
        self.assertFalse(eco.usb_events)
        self.assertTrue(monitor.usb_events)
        self.assertFalse(paused.usb_events)
        self.assertFalse(monitor.unreal_heartbeat)

    def test_valid_state_and_tooltip_do_not_claim_network_connection(self):
        with self.assertRaises(ValueError):
            mode_policy("modo oculto")
        tip = mode_tooltip("acompanhamento", usb=True)
        self.assertIn("USB/energia", tip)
        self.assertNotIn("internet", tip.lower())
        self.assertNotIn("microfone", tip)
        self.assertIn("microfone autorizado",
                      mode_tooltip("ativa", microphone=True))
        self.assertNotIn("microfone",
                         mode_tooltip("economica", microphone=True))


if __name__ == "__main__":
    unittest.main()
