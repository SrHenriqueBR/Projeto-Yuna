"""Yuna 0.14: iniciativa espontânea não intrusiva e controlável."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yuna
from proactive import (
    NudgeSchedule, MINUTES_BEFORE_FIRST, MINUTES_BETWEEN_NOTICES,
    MAX_NOTICES_PER_SESSION, spontaneous_enabled, set_spontaneous,
)
from own_initiative import pending_own_activity, propose_own_activity


class SpontaneousTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "yuna.db"
        self.memory = yuna.Memory(self.db)

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_does_not_interrupt_early_or_active_typing(self):
        state = NudgeSchedule.start(0)
        self.assertFalse(state.ready(11 * 60, 130))
        self.assertFalse(state.ready(MINUTES_BEFORE_FIRST * 60, 20))
        self.assertTrue(state.ready(MINUTES_BEFORE_FIRST * 60, 120))
        self.assertFalse(state.ready(5000, 120, busy=True))
        self.assertFalse(state.ready(5000, 120, enabled=False))
        self.assertFalse(state.ready(5000, 120, pending=True))

    def test_new_user_input_resets_quiet_window(self):
        state = NudgeSchedule.start(0)
        state.user_active(12 * 60)
        self.assertFalse(state.ready(14 * 60, 110))
        self.assertTrue(state.ready(25 * 60, 110))

    def test_cooldown_and_max_three_suggestions(self):
        state = NudgeSchedule.start(0)
        moment = 12 * 60
        for index in range(MAX_NOTICES_PER_SESSION):
            self.assertTrue(state.ready(moment, 120), index)
            state.mark_notice(moment)
            self.assertFalse(state.ready(moment + 60, 120))
            moment += MINUTES_BETWEEN_NOTICES * 60
        self.assertFalse(state.ready(moment + 5000, 120))

    def test_setting_persists_after_restart(self):
        self.assertTrue(spontaneous_enabled(self.memory.initiative))
        set_spontaneous(self.memory.initiative, False)
        self.assertFalse(spontaneous_enabled(self.memory.initiative))
        self.memory.close()
        self.memory = yuna.Memory(self.db)
        self.assertFalse(spontaneous_enabled(self.memory.initiative))
        set_spontaneous(self.memory.initiative, True)
        self.assertTrue(spontaneous_enabled(self.memory.initiative))

    def test_disabling_clears_pending_and_does_not_write(self):
        propose_own_activity(self.memory.initiative)
        self.assertIsNotNone(pending_own_activity(self.memory.initiative))
        set_spontaneous(self.memory.initiative, False)
        self.assertIsNone(pending_own_activity(self.memory.initiative))
        self.assertFalse((self.db.parent / "diario_yuna.md").exists())

    def test_text_commands_work_without_calling_model(self):
        with patch("yuna.ask_model", side_effect=AssertionError("No model call")):
            response = yuna.handle_message(self.memory, "/atividade desligar")
            self.assertIn("pausada", response)
            self.assertFalse(spontaneous_enabled(self.memory.initiative))
            response = yuna.handle_message(self.memory, "/atividade ligar")
            self.assertIn("ativa", response)
            self.assertTrue(spontaneous_enabled(self.memory.initiative))
            self.assertIn("ativa", yuna.handle_message(self.memory, "/atividade status"))

    def test_gui_only_timers_and_queue_actions_are_integrated(self):
        source = (Path(__file__).resolve().parents[1] / "yuna_overlay.py").read_text(encoding="utf-8")
        self.assertIn("self.spontaneous_timer.timeout.connect(self.check_spontaneous)", source)
        self.assertIn("self.spontaneous_timer.stop()", source)
        self.assertIn("self.spontaneous_schedule.user_active(time.monotonic())", source)
        self.assertIn("self.dialogue.request_spontaneous()", source)
        self.assertIn("self.signals.spontaneous_notice.connect(self.display_spontaneous)", source)
        self.assertIn("set_spontaneous(memory.initiative, message[1])", source)
        self.assertIn("not pending_own_activity(memory.initiative)", source)


if __name__ == "__main__":
    unittest.main()
