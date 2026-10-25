"""Protege a ligação entre sintetizador e reprodutor sem exigir PySide6 no CI."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


class ImmediateThread:
    def __init__(self, target, daemon):
        self.target = target

    def start(self):
        self.target()


def load_say():
    source = (ROOT / "yuna_overlay.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "YunaOverlay")
    function = next(node for node in cls.body
                    if isinstance(node, ast.FunctionDef) and node.name == "say")
    namespace = {
        "Thread": ImmediateThread,
        "speech_text": lambda text: text,
        "speak_windows": Mock(),
        "synthesize_edge": Mock(return_value=Path("test_yuna.mp3")),
        "synthesize_amanda": Mock(return_value=Path("test_amanda.mp3")),
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]),
                 str(ROOT / "yuna_overlay.py"), "exec"), namespace)
    return namespace


def stub(mode):
    return SimpleNamespace(
        voice_engine=mode,
        voice_busy=False,
        status=SimpleNamespace(setText=Mock()),
        signals=SimpleNamespace(
            edge_ready=SimpleNamespace(emit=Mock()),
            voice_finished=SimpleNamespace(emit=Mock()),
        ),
    )


class AudioRoutingTests(unittest.TestCase):
    def test_free_edge_audio_reaches_player_signal(self):
        ns = load_say()
        gui = stub("edge")
        ns["say"](gui, "Oi, Kaizen!")
        ns["synthesize_edge"].assert_called_once_with("Oi, Kaizen!")
        gui.signals.edge_ready.emit.assert_called_once_with("test_yuna.mp3")
        gui.signals.voice_finished.emit.assert_not_called()
        self.assertTrue(gui.voice_busy)

    def test_offline_speech_finishes_without_mp3(self):
        ns = load_say()
        gui = stub("windows")
        ns["say"](gui, "Oi")
        ns["speak_windows"].assert_called_once_with("Oi")
        gui.signals.voice_finished.emit.assert_called_once_with("")
        gui.signals.edge_ready.emit.assert_not_called()

    def test_other_online_voice_is_also_delivered(self):
        ns = load_say()
        gui = stub("amanda")
        ns["say"](gui, "Teste")
        ns["synthesize_amanda"].assert_called_once_with("Teste")
        gui.signals.edge_ready.emit.assert_called_once_with("test_amanda.mp3")

    def test_failure_reports_error_and_does_not_emit_mp3(self):
        ns = load_say()
        ns["synthesize_edge"].side_effect = RuntimeError("Falhou a sintetização")
        gui = stub("edge")
        ns["say"](gui, "Teste")
        gui.signals.edge_ready.emit.assert_not_called()
        gui.signals.voice_finished.emit.assert_called_once_with("Falhou a sintetização")

    def test_mute_never_synthesizes(self):
        ns = load_say()
        gui = stub("off")
        ns["say"](gui, "Teste")
        ns["synthesize_edge"].assert_not_called()
        ns["synthesize_amanda"].assert_not_called()
        gui.signals.edge_ready.emit.assert_not_called()
        self.assertFalse(gui.voice_busy)


if __name__ == "__main__":
    unittest.main()
