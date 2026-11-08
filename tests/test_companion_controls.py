"""Controles do residente sem desligar, acordar, gravar ou enviar teclas reais."""
from datetime import datetime, timedelta
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
from types import ModuleType

from companion_commands import banking_action, game_intent, power_intent, wake_command
from game_controls import Foreground, allowed_game, execute_action
from game_sessions import GameSession
from pc_controls import ShutdownCountdown, performance_report, shutdown_windows
from wake_schedule import wake_intent, run_wake_task

GAME = r"C:\Games\Example\Game.exe"


class CompanionControlsTests(unittest.TestCase):
    def test_cancelled_dictation_closes_capture_before_loading_model(self):
        import speech_input
        with patch("audio_capture.capture_phrase", side_effect=InterruptedError("Cancelado")) as capture, patch(
                "speech_input.transcribe_audio") as transcribe:
            with self.assertRaises(InterruptedError):
                speech_input.listen_once()
        capture.assert_called_once()
        transcribe.assert_not_called()

    def test_destructive_requests_are_exact_and_negations_never_shutdown(self):
        for text in ("Yuna desliga o computador", "Yuna, desligue o computador.", "/desligar"):
            self.assertEqual(power_intent(text), "shutdown")
        self.assertEqual(power_intent("Yuna, não desligue o computador"), "cancel")
        for text in ("Como desligar o computador?", 'Escreva "desliga o computador"',
                     "Não quero que desliga o computador", "desliga o computador e apague tudo",
                     "Se eu disser Yuna desliga o computador", "desliga o computador às 19:00"):
            self.assertIsNone(power_intent(text))

    def test_wake_only_accepts_addressed_calls(self):
        self.assertEqual(wake_command("Olá, Yuna!"), "Olá Yuna")
        self.assertEqual(wake_command("Yuna, abra Downloads"), "Yuna abra Downloads")
        for text in ("Eu disse olá Yuna", "Um filme com Yuna", "Yunara abra o banco", "a" * 400, None):
            self.assertIsNone(wake_command(text))

    def test_countdown_cancellation_expiry_and_no_double_shutdown(self):
        clock, execute = Mock(return_value=100), Mock()
        timer = ShutdownCountdown(execute, clock)
        timer.start()
        clock.return_value = 129
        self.assertFalse(timer.tick())
        self.assertEqual(timer.remaining(), 1)
        self.assertTrue(timer.cancel())
        clock.return_value = 200
        self.assertFalse(timer.tick())
        execute.assert_not_called()
        timer.start()
        timer.start()  # repetir o pedido não cria dois desligamentos
        clock.return_value = 230
        self.assertTrue(timer.tick())
        self.assertFalse(timer.tick())
        execute.assert_called_once_with()

    def test_shutdown_does_not_force_close_apps_or_interpolate_input(self):
        with patch("pc_controls.os") as system, patch("pc_controls.subprocess.run") as run:
            system.name = "nt"
            system.environ = {"SystemRoot": "/Windows"}
            run.return_value = Mock(returncode=0)
            shutdown_windows()
            self.assertEqual(run.call_args.args[0][1:], ["/s", "/t", "0"])
            self.assertFalse(run.call_args.kwargs["shell"])
            run.return_value.returncode = 5
            with self.assertRaises(RuntimeError):
                shutdown_windows()

    def test_wake_schedule_rollover_explicit_day_invalid_and_out_of_scope(self):
        now = datetime(2026, 11, 3, 22, 0)
        self.assertEqual(wake_intent("Yuna, acorde o computador às 07:00", now),
                         ("agendar", datetime(2026, 11, 4, 7)))
        self.assertEqual(wake_intent("/despertar 2026-11-05 09:15", now)[1], datetime(2026, 11, 5, 9, 15))
        for text in ("/despertar hoje 07:00", "/despertar 25:00", "/despertar 2026-12-30 08:00"):
            with self.assertRaises(ValueError):
                wake_intent(text, now)
        for text in ("não ligue o computador às 07:00", "como ligar o computador às 07:00", "/despertar 07:00; calc"):
            self.assertIsNone(wake_intent(text, now))

    def test_schedule_is_fixed_script_and_reports_failures(self):
        when = datetime.now() + timedelta(hours=2)
        with patch("wake_schedule.os") as system, patch("wake_schedule.subprocess.run") as run:
            system.name = "nt"
            system.environ = {"SystemRoot": "/Windows"}
            run.return_value = Mock(returncode=0, stdout='{"exists":true}')
            result = run_wake_task("agendar", when)
            self.assertIn("totalmente desligado", result)
            self.assertEqual(run.call_args.args[0][-2:], ["-Acao", "agendar"])
            self.assertEqual(run.call_args.kwargs["env"]["YUNA_WAKE_TIME"], when.isoformat(timespec="seconds"))
            self.assertFalse(run.call_args.kwargs["shell"])
            run.return_value.returncode = 1
            with self.assertRaises(RuntimeError):
                run_wake_task("agendar", when)

    def test_banking_routes_are_blocked_before_model_or_catalog_launch(self):
        import yuna
        from desktop import Desktop
        for text in ("Yuna abra o Nubank", "pague o boleto", "acesse minha conta bancária",
                     "transfira um pix", "abra o aplicativo Itaú"):
            self.assertTrue(banking_action(text), text)
            with patch("yuna.ask_model") as model:
                self.assertIn("desativadas", yuna.handle_message(None, text, Mock()))
                model.assert_not_called()
        pc = Desktop()
        pc.catalog = [{"name": "Nubank", "id": "Nubank.App"}]
        with patch("desktop.subprocess.Popen") as popen:
            self.assertIn("desativadas", pc.launch(pc.catalog[0]))
            popen.assert_not_called()
        self.assertFalse(banking_action("abrir Steam"))

    def test_greeting_is_offline_and_persisted(self):
        import yuna
        with tempfile.TemporaryDirectory() as temp:
            memory = yuna.Memory(Path(temp) / "yuna.db")
            try:
                with patch("yuna.ask_model") as model:
                    answer = yuna.handle_message(memory, "Olá Yuna")
                    self.assertIn("Olá, Kaizen!", answer)
                    model.assert_not_called()
                self.assertEqual(memory.history()[-1]["content"], answer)
            finally:
                memory.close()

    def test_diagnostic_handles_windows_single_disk_and_low_resources(self):
        report = performance_report({"RAM_total_GB": 8, "RAM_livre_GB": .5,
            "Discos": {"DeviceID": "C:", "Total_GB": 500, "Livre_GB": 10}})
        self.assertIn("Pouca RAM", report)
        self.assertIn("Pouco espaço", report)
        self.assertNotIn("Pouca RAM", performance_report({"RAM_total_GB": 0, "RAM_livre_GB": 0}))


class GameInputTests(unittest.TestCase):
    def setUp(self):
        self.session = GameSession()
        self.session.authorize(GAME, approved=True, single_player=True)
        self.snapshot = Foreground(12, 34, GAME.lower())
        self.backend = Mock()
        self.backend.foreground.return_value = self.snapshot
        self.backend.key_is_down.return_value = False

    def test_one_short_input_has_release_and_no_loop(self):
        execute_action(self.session, "jump", lambda: False, self.backend,
                       clock=Mock(side_effect=[0, .2]))
        self.assertEqual(self.backend.key.call_count, 2)
        self.assertEqual(self.backend.key.call_args_list[0].kwargs, {"release": False})
        self.assertEqual(self.backend.key.call_args_list[1].kwargs, {"release": True})

    def test_other_foreground_revokes_and_sends_nothing(self):
        self.backend.foreground.return_value = Foreground(9, 8, r"c:\games\other.exe")
        with self.assertRaises(PermissionError):
            execute_action(self.session, "jump", lambda: False, self.backend)
        self.backend.key.assert_not_called()
        self.assertFalse(self.session.active)

    def test_changed_pid_before_press_and_modifiers_send_nothing(self):
        self.backend.foreground.side_effect = [self.snapshot, Foreground(12, 99, GAME.lower())]
        with self.assertRaises(InterruptedError):
            execute_action(self.session, "jump", lambda: False, self.backend)
        self.backend.key.assert_not_called()
        self.setUp()
        self.backend.key_is_down.return_value = True
        with self.assertRaises(PermissionError):
            execute_action(self.session, "jump", lambda: False, self.backend)
        self.backend.key.assert_not_called()

    def test_focus_loss_and_cancel_during_press_always_release(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                self.setUp()
                self.backend.foreground.side_effect = [self.snapshot, self.snapshot,
                    Foreground(99, 88, r"c:\games\other.exe")]
                cancelled = Mock(side_effect=[False, False, cancel])
                with self.assertRaises(InterruptedError):
                    execute_action(self.session, "jump", cancelled, self.backend,
                        clock=Mock(side_effect=[0, .05]))
                self.assertEqual(self.backend.key.call_count, 2)
                self.assertTrue(self.backend.key.call_args.kwargs["release"])

    def test_denied_executables_and_non_commands(self):
        for path in (r"C:\Windows\system32\cmd.exe", r"C:\Apps\chrome.exe", r"C:\Apps\Nubank.exe"):
            with self.assertRaises(PermissionError):
                allowed_game(path)
        for text in ("Como pular no jogo?", "Não pule", "Yuna aperte Alt F4", "/jogo pule; calc"):
            self.assertIsNone(game_intent(text))
        self.assertEqual(game_intent("Yuna, no jogo pule"), "jump")


class CameraDescriptionTests(unittest.TestCase):
    def test_only_explicit_frame_goes_to_local_model(self):
        from camera_description import describe_frame
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps({"message": {"content": "Uma mesa."}}).encode()
        with patch.dict("os.environ", {"YUNA_VISION_MODEL": "modelo-local:1b"}), patch(
                "camera_description.urllib.request.build_opener") as build:
            build.return_value.open.return_value = response
            self.assertEqual(describe_frame(b"jpeg"), "Uma mesa.")
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(json.loads(request.data)["messages"][0]["images"], ["anBlZw=="])

    def test_missing_cloud_model_and_redirect_do_not_send_image_outside_localhost(self):
        from camera_description import describe_frame, NoRedirect
        for model in ("", "model:cloud", "not a model"):
            with patch.dict("os.environ", {"YUNA_VISION_MODEL": model}), patch(
                    "camera_description.urllib.request.build_opener") as build:
                self.assertIn("Configure", describe_frame(b"jpeg"))
                build.assert_not_called()
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None, None, 302, "found", {}, "https://external.test")


if __name__ == "__main__":
    unittest.main()
