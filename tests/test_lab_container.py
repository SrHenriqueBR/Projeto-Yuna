"""Teste real do contêiner. Ative após disponibilizar python:3.12-slim localmente.

O modelo é substituído por uma proposta fixa; Docker, testes, rede e montagem
são reais. Não requer Ollama, credenciais, Qt ou dados da instalação.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import development_lab as lab

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("YUNA_TEST_DOCKER") == "1", "Docker integration opt-in")
class RealContainerTests(unittest.TestCase):
    def test_real_baseline_candidate_readonly_mount_and_disabled_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            for path in lab.TARGETS + (lab.CONTRACT,):
                shutil.copyfile(ROOT / path, root / path)
            (root / "private.txt").write_text("MUST NOT BE MOUNTED")
            original = (root / lab.TARGETS[0]).read_text(encoding="utf-8")
            proposal = json.dumps({
                "summary": "Proposta fixa para comprovar o ciclo de testes isolados.",
                "source": original + '\n\ndef lab_fixture_value():\n    return "ready"\n',
                "tests": '''import os, socket, unittest
from pathlib import Path
from language_quality import lab_fixture_value
class ContainerContract(unittest.TestCase):
    def test_candidate_and_isolation(self):
        self.assertEqual(lab_fixture_value(), "ready")
        self.assertEqual(set(os.listdir("/work")), {"tests", "language_quality.py", "natural_interaction.py"})
        self.assertFalse(Path("/work/private.txt").exists())
        with self.assertRaises(OSError):
            Path("/work/language_quality.py").write_text("overwrite")
        with socket.socket() as client:
            client.settimeout(0.5)
            with self.assertRaises(OSError):
                client.connect(("1.1.1.1", 443))
''',
            })
            runner = lab.DockerTests()
            self.assertTrue(runner.prepare(), runner.reason)
            folder = lab.develop(root, lab.TARGETS[0], "Verificar execução real e isolamento do laboratório",
                                 lambda messages, schema=None: proposal, runner=runner)
            report = json.loads((folder / "relatorio.json").read_text(encoding="utf-8"))
            self.assertEqual(report["baseline"]["status"], "passed", report)
            self.assertEqual(report["baseline"]["tests"], 9)
            self.assertEqual(report["status"], "tests_passed", report)
            self.assertEqual(report["attempts"][-1]["tests"], 10)
            self.assertEqual((root / lab.TARGETS[0]).read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
