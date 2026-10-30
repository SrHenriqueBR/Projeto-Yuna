import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import development_lab as lab
import yuna

ROOT = Path(__file__).resolve().parents[1]


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        for path in lab.TARGETS + (lab.CONTRACT,):
            shutil.copyfile(ROOT / path, self.root / path)
        self.original = (self.root / lab.TARGETS[0]).read_text(encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def candidate(self, extra=""):
        return json.dumps({
            "summary": "Acrescenta um pequeno auxiliar para testar o fluxo do laboratório.",
            "source": self.original + "\n\ndef lab_example():\n    return 42\n" + extra,
            "tests": "import unittest\nfrom language_quality import lab_example\n"
                     "class NewTests(unittest.TestCase):\n"
                     "    def test_value(self):\n        self.assertEqual(lab_example(), 42)\n",
        })

    def runner(self, *results, available=True):
        runner = Mock()
        runner.prepare.return_value = available
        runner.run.side_effect = list(results)
        return runner

    def test_real_installed_self_test_needs_no_model_or_docker(self):
        with patch("yuna.ask_model", side_effect=AssertionError("No model")):
            result = lab.self_test(self.root)
        self.assertEqual(result.status, "passed", result.detail)
        self.assertEqual(result.tests, 9)
        self.assertFalse((self.root / "data").exists())

    def test_draft_does_not_change_working_source_or_copy_private_files(self):
        (self.root / "data").mkdir()
        (self.root / "data/yuna.db").write_text("PRIVATE CONVERSATION")
        (self.root / ".env").write_text("SECRET_KEY=do_not_copy")
        runner = self.runner(lab.TestResult("passed", "baseline", 9), lab.TestResult("passed", "candidate", 10))
        folder = lab.develop(self.root, lab.TARGETS[0], "Melhorar concordância da fala", Mock(return_value=self.candidate()), runner=runner)
        self.assertEqual((self.root / lab.TARGETS[0]).read_text(encoding="utf-8"), self.original)
        report = json.loads((folder / "relatorio.json").read_text())
        self.assertEqual(report["status"], "tests_passed")
        self.assertIs(report["applied"], False)
        files = {str(path.relative_to(folder / "workspace")).replace("\\", "/")
                 for path in (folder / "workspace").rglob("*") if path.is_file()}
        self.assertEqual(files, set(lab.TARGETS + (lab.CONTRACT, "tests/test_generated.py")))
        self.assertEqual((folder / "workspace" / lab.CONTRACT).read_bytes(), (self.root / lab.CONTRACT).read_bytes())
        self.assertIn("+def lab_example", (folder / "tentativa_1/mudanca.diff").read_text())

    def test_no_docker_never_executes_generated_python_or_claims_test_pass(self):
        runner = self.runner(lab.TestResult("not_run", "Docker ausente"), lab.TestResult("not_run", "Docker ausente"), available=False)
        folder = lab.develop(self.root, lab.TARGETS[0], "Criar um auxiliar de exemplo", Mock(return_value=self.candidate("\nraise RuntimeError('NEVER EXECUTE ON HOST')\n")), runner=runner)
        report = json.loads((folder / "relatorio.json").read_text())
        self.assertEqual(report["status"], "not_run")
        self.assertEqual(report["attempts"][0]["syntax"], "passed")
        self.assertIn("NÃO realizados", lab.report_text(folder))

    def test_broken_baseline_prevents_code_generation(self):
        runner = self.runner(lab.TestResult("failed", "regression failed", 9))
        ask = Mock(side_effect=AssertionError("Do not draft"))
        folder = lab.develop(self.root, lab.TARGETS[0], "Melhorar concordância da fala", ask, runner=runner)
        self.assertEqual(json.loads((folder / "relatorio.json").read_text())["status"], "baseline_failed")
        ask.assert_not_called()

    def test_failed_draft_gets_one_revision_with_actual_code_and_feedback(self):
        runner = self.runner(lab.TestResult("passed", "baseline", 9),
                             lab.TestResult("failed", "AssertionError: expected 42", 10),
                             lab.TestResult("passed", "fixed", 10))
        ask = Mock(return_value=self.candidate())
        folder = lab.develop(self.root, lab.TARGETS[0], "Melhorar concordância da fala", ask, runner=runner)
        self.assertEqual(ask.call_count, 2)
        feedback = json.loads(ask.call_args.args[0][-1]["content"])["previous_attempt_feedback"]
        self.assertIn("AssertionError: expected 42", feedback)
        self.assertIn("lab_example", feedback)
        self.assertEqual(len(json.loads((folder / "relatorio.json").read_text())["attempts"]), 2)

    def test_invalid_model_output_is_bounded_and_not_executed(self):
        runner = self.runner(lab.TestResult("passed", "baseline", 9))
        ask = Mock(return_value='{"command":"delete everything"}')
        folder = lab.develop(self.root, lab.TARGETS[0], "Melhorar concordância da fala", ask, runner=runner)
        self.assertEqual(ask.call_count, 2)
        self.assertEqual(runner.run.call_count, 1)
        self.assertEqual(json.loads((folder / "relatorio.json").read_text())["status"], "invalid")

    def test_privileged_paths_and_removed_exports_are_rejected(self):
        for path in ("yuna.py", "yuna_governance.py", "../secret.py", "/etc/passwd", "camera_viewer.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                lab.develop(self.root, path, "Trocar o comportamento do módulo", Mock())
        data = json.loads(self.candidate())
        data["source"] = "def unrelated():\n    return 'changed public API'\n"
        with self.assertRaisesRegex(ValueError, "removeu"):
            lab._validate(json.dumps(data), lab.TARGETS[0], self.original)

    def test_cancel_never_generates_or_runs_another_step(self):
        ask = Mock()
        runner = self.runner()
        with self.assertRaises(InterruptedError):
            lab.develop(self.root, lab.TARGETS[0], "Melhorar concordância da fala", ask, runner=runner, cancelled=lambda: True)
        ask.assert_not_called()
        runner.prepare.assert_not_called()
        report = next((self.root / "data/laboratorio").glob("*/relatorio.json"))
        self.assertEqual(json.loads(report.read_text())["status"], "cancelled")

    def test_real_output_and_time_limits(self):
        code, output, problem = lab._bounded([sys.executable, "-c", "print('a' * 100000)"], timeout=5)
        self.assertLessEqual(len(output.encode()), lab.MAX_LOG)
        self.assertEqual(problem, "limite de saída")
        code, output, problem = lab._bounded([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.15)
        self.assertEqual(problem, "limite de tempo")

    def test_command_routes_to_real_selftest(self):
        with patch("yuna.ROOT", self.root), patch("yuna.ask_model", side_effect=AssertionError("No Ollama")):
            result = yuna.handle_message(None, "Yuna, teste sua base")
        self.assertIn("9 testes passaram", result)
        self.assertIn("Não testa voz", result)


class DockerBoundaryTests(unittest.TestCase):
    def test_missing_docker_has_no_host_fallback(self):
        with patch("development_lab.shutil.which", return_value=None), patch("development_lab._bounded") as run:
            runner = lab.DockerTests()
            self.assertFalse(runner.prepare())
            self.assertEqual(runner.run(".").status, "not_run")
            run.assert_not_called()

    def test_remote_daemon_rejected(self):
        with patch("development_lab.shutil.which", return_value="docker"), patch.dict(os.environ, {"DOCKER_HOST": "tcp://remote:2375"}), patch("development_lab._bounded") as run:
            runner = lab.DockerTests()
            self.assertFalse(runner.prepare())
            run.assert_not_called()

    def test_container_has_only_readonly_minimal_mount_no_network_and_limits(self):
        runner = lab.DockerTests()
        runner.command = ["docker", "--host", "unix:///var/run/docker.sock"]
        runner.image = "sha256:" + "a" * 64
        result = 'YUNA_TEST_RESULT={"tests":9,"ok":true,"skipped":0}\n'
        with patch("development_lab._bounded", side_effect=[(0, result, ""), (0, "", "")]) as run:
            self.assertEqual(runner.run(ROOT).status, "passed")
        args = run.call_args_list[0].args[0]
        for value in ("--network=none", "--read-only", "--pull=never", "--cap-drop=ALL",
                      "--user=65534:65534", "--memory=512m", "--cpus=1", "--pids-limit=64"):
            self.assertIn(value, args)
        self.assertEqual(args.count("--mount"), 1)
        self.assertTrue(args[args.index("--mount") + 1].endswith(",target=/work,readonly"))
        self.assertNotIn("DOCKER_CONTEXT", run.call_args_list[0].kwargs["env"])
        self.assertNotIn("DOCKER_HOST", run.call_args_list[0].kwargs["env"])
        self.assertEqual(run.call_args_list[-1].args[0][-3:-1], ["rm", "--force"])

    def test_cancelled_container_is_removed(self):
        runner = lab.DockerTests()
        runner.command, runner.image = ["docker"], "sha256:" + "a" * 64
        with patch("development_lab._bounded", side_effect=[InterruptedError(), (0, "", "")]) as run:
            with self.assertRaises(InterruptedError):
                runner.run(ROOT)
        self.assertIn("--force", run.call_args.args[0])

    def test_zero_tests_and_skipped_tests_cannot_pass(self):
        runner = lab.DockerTests()
        runner.command, runner.image = ["docker"], "sha256:" + "a" * 64
        for data in ({"tests": 0, "ok": True, "skipped": 0}, {"tests": 9, "ok": True, "skipped": 1}):
            with self.subTest(data=data), patch("development_lab._bounded", side_effect=[
                (0, "YUNA_TEST_RESULT=" + json.dumps(data), ""), (0, "", "")
            ]):
                self.assertEqual(runner.run(ROOT).status, "failed")


if __name__ == "__main__":
    unittest.main()
