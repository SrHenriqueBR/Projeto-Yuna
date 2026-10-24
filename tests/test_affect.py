"""Testes do núcleo afetivo (estados transparentes, memória explícita e privacidade)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import yuna
from affect import BASE, AffectiveCore, safe_preference, contains_phrase


class AffectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "yuna.db"
        self.memory = yuna.Memory(self.path)
        self.core = self.memory.affect

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_simulated_affect_is_bounded_and_persistent(self):
        self.assertIn("simulado", self.core.status_text())
        self.assertEqual(self.core.values(), BASE)
        self.assertEqual(self.core.observe("Consegui! Deu certo!"), "alegria")
        self.assertGreater(self.core.values()["energia"], BASE["energia"])
        self.memory.close()
        self.memory = yuna.Memory(self.path)
        self.core = self.memory.affect
        self.assertGreater(self.core.values()["energia"], BASE["energia"])
        for i in range(250):
            self.core.observe("Estou feliz")
        self.assertLessEqual(self.core.values()["energia"], 100)

    def test_explicit_preference_only_and_no_secret(self):
        self.assertIsNotNone(safe_preference("Prefiro respostas mais curtas."))
        self.assertIsNone(safe_preference("Talvez eu goste de algo."))
        self.assertIsNone(safe_preference("Minha senha é teste123"))
        self.assertIsNone(safe_preference("Gosto de enviar email usuario@example.org"))
        self.assertIsNone(safe_preference("Gosto de usar meu CPF 12345678901"))
        self.core.observe("Prefiro respostas mais curtas.")
        self.core.observe("Prefiro respostas mais curtas.")
        self.assertEqual(len(self.core.preferences()), 1)
        self.assertEqual(self.core.preferences()[0][1], "Prefiro respostas mais curtas.")
        self.assertIsNone(self.core.observe("Minha senha é algo secreto"))
        self.assertEqual(len(self.core.preferences()), 1)
        ident = self.core.preferences()[0][0]
        self.assertEqual(self.core.forget_preference(ident), 1)

    def test_boundaries_and_tones(self):
        self.assertFalse(contains_phrase("segurança", "rança"))
        self.assertTrue(contains_phrase("Estou cansada hoje", "cansada"))
        self.assertEqual(self.core.observe("Estou triste"), "dificuldade")
        self.assertGreater(self.core.values()["acolhimento"], BASE["acolhimento"])
        instructions = self.core.style_instructions()
        self.assertIn("não uma sensação", instructions)
        self.assertIn("Não faça cobranças", instructions)

    def test_disable_and_clear(self):
        self.core.enable(False)
        self.assertFalse(self.core.enabled)
        self.assertIsNone(self.core.observe("Estou feliz"))
        self.assertEqual(self.core.values(), BASE)
        self.assertIn("desativado", self.core.status_text())
        self.core.enable(True)
        self.core.observe("Gosto de aprender Python")
        self.core.save_reflection("Hipótese: prefere estudar de manhã; confirmar.")
        self.memory.clear()
        self.assertEqual(len(self.core.preferences()), 1)
        self.assertEqual(len(self.core.reflections()), 1)
        self.memory.clear(all_data=True)
        self.assertEqual(self.core.preferences(), [])
        self.assertEqual(self.core.reflections(), [])
        self.assertEqual(self.core.values(), BASE)

    def test_reflection_is_not_promoted_to_fact(self):
        self.memory.remember("Prefiro Windows.")
        self.core.observe("Gosto de estudar Python")
        with patch("yuna.ask_model", return_value="Você disse gostar de Python. Hipótese: estudar mais."):
            result = yuna.reflect(self.memory)
        self.assertIn("Hipótese", result)
        self.assertEqual(len(self.core.reflections()), 1)
        self.assertNotIn("estudar mais", [fact for _, fact in self.memory.facts()])
        ident = self.core.reflections()[0][0]
        self.assertEqual(self.core.forget_reflection(ident), 1)
        self.assertEqual(self.core.reflections(), [])

    def test_context_includes_style_and_preferences(self):
        self.core.observe("Prefiro explicações técnicas.")
        with patch("yuna.ask_model", return_value="Entendi, vou explicar tecnicamente.") as ask:
            result = yuna.respond(self.memory, "Quero entender SQL.")
        system = ask.call_args.args[0][0]["content"]
        self.assertIn("Prefiro explicações técnicas", system)
        self.assertIn("não uma sensação vivida", system)
        self.assertIn("Entendi", result)

    def test_export_knowledge_and_reopen(self):
        self.core.observe("Gosto de programar.")
        self.memory.export()
        exported = json.loads((self.path.parent / "conhecimentos.json").read_text(encoding="utf-8"))
        self.assertEqual(exported["preferencias"][0]["texto"], "Gosto de programar.")
        self.assertIn("estado_afetivo_simulado", exported)
        self.memory.close()
        self.memory = yuna.Memory(self.path)
        self.core = self.memory.affect
        self.assertEqual(len(self.core.preferences()), 1)


if __name__ == "__main__":
    unittest.main()
