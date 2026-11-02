import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import development_lab as lab
import lab_review as review

ROOT = Path(__file__).resolve().parents[1]


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        for path in review.REFERENCES:
            shutil.copyfile(ROOT / path, self.root / path)
        self.original = (self.root / lab.TARGETS[0]).read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self, extra=""):
        original = lab._read_source(self.root, lab.TARGETS[0])
        candidate = json.dumps({
            "summary": "Acrescentar um pequeno auxiliar para verificar a revisão local.",
            "source": original + "\n\ndef review_fixture():\n    return 42\n" + extra,
            "tests": "import unittest\nfrom language_quality import review_fixture\n"
                     "class NewTests(unittest.TestCase):\n"
                     "    def test_fixture(self):\n        self.assertEqual(review_fixture(), 42)\n",
        })
        runner = Mock()
        runner.prepare.return_value = False
        runner.run.return_value = lab.TestResult("not_run", "Docker ausente")
        return lab.develop(self.root, lab.TARGETS[0], "Verificar revisão e restauração local",
                           Mock(return_value=candidate), runner=runner)

    def runner(self, *results):
        runner = Mock()
        runner.prepare.return_value = True
        runner.run.side_effect = list(results) or [lab.TestResult("passed", "baseline", 9),
                                                 lab.TestResult("passed", "candidate", 10)]
        return runner

    def verified(self, extra=""):
        folder = self.proposal(extra)
        snapshot = review.inspect_proposal(self.root, folder.name)
        return review.verify(self.root, snapshot, runner=self.runner())

    def test_real_diff_no_saved_diff_trust_and_no_host_execution(self):
        marker = self.root / "DO_NOT_EXECUTE"
        folder = self.proposal("\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
        (folder / "tentativa_1/mudanca.diff").write_text("FALSO: nenhuma mudança", encoding="utf-8")
        snapshot = review.inspect_proposal(self.root, folder.name)
        detail = review.review_text(snapshot)
        self.assertIn("+def review_fixture", detail)
        self.assertIn("DO_NOT_EXECUTE", detail)
        self.assertIn("test_fixture", detail)
        self.assertNotIn("FALSO", detail)
        checked = review.verify(self.root, snapshot, runner=self.runner())
        ident = review.apply_verified(self.root, checked, snapshot.approval)
        self.assertFalse(marker.exists())
        self.assertEqual((self.root / snapshot.target).read_bytes(), snapshot.source)
        self.assertEqual(review.load_record(self.root, ident)[-1], "applied")
        review.restore(self.root, ident, "RESTAURAR " + ident)
        self.assertEqual((self.root / snapshot.target).read_bytes(), self.original)
        self.assertFalse(marker.exists())

    def test_fresh_workspace_excludes_data_and_tests_cannot_replace_contracts(self):
        folder = self.proposal()
        (self.root / "data/private.txt").write_text("PRIVATE", encoding="utf-8")
        # Não reutilizar workspace ou diff de uma proposta no disco.
        (folder / "workspace" / lab.CONTRACT).write_text("raise RuntimeError('TAMPERED')")
        snapshot = review.inspect_proposal(self.root, folder.name)
        seen = []

        def run(path):
            files = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
            expected = set(review.REFERENCES)
            if seen:
                expected.add("tests/test_generated.py")
                self.assertEqual((path / snapshot.target).read_bytes(), snapshot.source)
            self.assertEqual(files, expected)
            self.assertEqual((path / lab.CONTRACT).read_bytes(), (self.root / lab.CONTRACT).read_bytes())
            seen.append(path)
            return lab.TestResult("passed", "real workspace fixture", 8 + len(seen))

        runner = self.runner()
        runner.run.side_effect = run
        review.verify(self.root, snapshot, runner=runner)
        self.assertEqual(len(seen), 2)
        self.assertFalse(seen[0].exists())

    def test_no_docker_cannot_apply_even_when_report_says_passed(self):
        folder = self.proposal()
        path = folder / "relatorio.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "tests_passed"
        path.write_text(json.dumps(data), encoding="utf-8")
        snapshot = review.inspect_proposal(self.root, folder.name)
        runner = self.runner()
        runner.prepare.return_value = False
        runner.reason = "Docker ausente"
        with self.assertRaisesRegex(ValueError, "sem testes em Docker"):
            review.verify(self.root, snapshot, runner=runner)
        runner.run.assert_not_called()
        self.assertEqual((self.root / snapshot.target).read_bytes(), self.original)

    def test_failed_base_candidate_or_missing_additional_tests_block_verification(self):
        folder = self.proposal()
        snapshot = review.inspect_proposal(self.root, folder.name)
        for results in (
            (lab.TestResult("failed", "broken base", 9),),
            (lab.TestResult("passed", "base", 9), lab.TestResult("failed", "broken proposal", 10)),
            (lab.TestResult("passed", "base", 9), lab.TestResult("passed", "no new tests", 9)),
            (lab.TestResult("passed", "base", 9), lab.TestResult("not_run", "absent", 0)),
        ):
            with self.subTest(results=results), self.assertRaises(ValueError):
                review.verify(self.root, snapshot, runner=self.runner(*results))
        self.assertEqual((self.root / snapshot.target).read_bytes(), self.original)

    def test_exact_approval_required_and_no_file_changes_on_cancel(self):
        checked = self.verified()
        for answer in ("", "sim", "APLICAR", checked.review.approval + " extra"):
            with self.subTest(answer=answer), self.assertRaisesRegex(ValueError, "Confirmação"):
                review.apply_verified(self.root, checked, answer)
        self.assertFalse((self.root / review.HISTORY).exists())
        self.assertEqual((self.root / checked.review.target).read_bytes(), self.original)

    def test_proposal_tests_report_and_source_changes_invalidate_review(self):
        for relative in ("tentativa_1/language_quality.py", "tentativa_1/test_generated.py", "relatorio.json"):
            with self.subTest(relative=relative):
                checked = self.verified()
                path = self.root / "data/laboratorio" / checked.review.ident / relative
                original = path.read_bytes()
                if relative.endswith(".json"):
                    data = json.loads(original)
                    data["objective"] = "Objetivo modificado depois da revisão"
                    path.write_text(json.dumps(data), encoding="utf-8")
                else:
                    path.write_bytes(original + b"\n# edit after review\n")
                with self.assertRaises(ValueError):
                    review.apply_verified(self.root, checked, checked.review.approval)
                self.assertEqual((self.root / checked.review.target).read_bytes(), self.original)

    def test_reference_changes_before_and_during_tests_are_not_overwritten(self):
        for relative in review.REFERENCES:
            with self.subTest(relative=relative):
                checked = self.verified()
                path = self.root / relative
                before = path.read_bytes()
                path.write_bytes(before + b"\n# newer installed version\n")
                with self.assertRaises(ValueError):
                    review.apply_verified(self.root, checked, checked.review.approval)
                self.assertEqual(path.read_bytes(), before + b"\n# newer installed version\n")
                path.write_bytes(before)
        folder = self.proposal()
        snapshot = review.inspect_proposal(self.root, folder.name)
        runner = self.runner()
        def run(path):
            (self.root / snapshot.target).write_bytes(self.original + b"\n# edited during tests\n")
            return lab.TestResult("passed", "base", 9 if not (path / "tests/test_generated.py").exists() else 10)
        runner.run.side_effect = run
        with self.assertRaises(ValueError):
            review.verify(self.root, snapshot, runner=runner)

    def test_old_report_without_reference_hashes_is_retested(self):
        folder = self.proposal()
        path = folder / "relatorio.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("reference_sha256")
        path.write_text(json.dumps(data), encoding="utf-8")
        runner = self.runner()
        review.verify(self.root, review.inspect_proposal(self.root, folder.name), runner=runner)
        self.assertEqual(runner.run.call_count, 2)

    def test_exact_backup_including_bom_and_crlf_and_idempotent_restore_rejection(self):
        original = b"\xef\xbb\xbf" + self.original.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        (self.root / lab.TARGETS[0]).write_bytes(original)
        checked = self.verified()
        ident = review.apply_verified(self.root, checked, checked.review.approval)
        self.assertEqual(review.read_bytes(self.root, Path(review.HISTORY) / ident / "antes.py"), original)
        with self.assertRaises(ValueError):
            review.restore(self.root, ident, "sim")
        review.restore(self.root, ident, "RESTAURAR " + ident)
        self.assertEqual((self.root / checked.review.target).read_bytes(), original)
        self.assertEqual(review.load_record(self.root, ident)[-1], "restored")
        with self.assertRaises(ValueError):
            review.restore(self.root, ident, "RESTAURAR " + ident)

    def test_restore_never_overwrites_newer_changes_or_tampered_backup(self):
        checked = self.verified()
        ident = review.apply_verified(self.root, checked, checked.review.approval)
        target = self.root / checked.review.target
        target.write_bytes(checked.review.source + b"\n# manual edit\n")
        with self.assertRaises(ValueError):
            review.restore(self.root, ident, "RESTAURAR " + ident)
        self.assertTrue(target.read_bytes().endswith(b"# manual edit\n"))
        target.write_bytes(checked.review.source)
        backup = self.root / review.HISTORY / ident / "antes.py"
        backup.write_bytes(self.original + b"\n# damaged backup\n")
        with self.assertRaisesRegex(ValueError, "Backup alterado"):
            review.restore(self.root, ident, "RESTAURAR " + ident)
        self.assertEqual(target.read_bytes(), checked.review.source)

    def test_multiple_updates_restore_in_reverse_order(self):
        first = self.verified()
        id1 = review.apply_verified(self.root, first, first.review.approval)
        second = self.verified("\n# another small change\n")
        id2 = review.apply_verified(self.root, second, second.review.approval)
        with self.assertRaises(ValueError):
            review.restore(self.root, id1, "RESTAURAR " + id1)
        review.restore(self.root, id2, "RESTAURAR " + id2)
        self.assertEqual((self.root / first.review.target).read_bytes(), first.review.source)
        review.restore(self.root, id1, "RESTAURAR " + id1)
        self.assertEqual((self.root / first.review.target).read_bytes(), self.original)

    def test_interruption_after_source_swap_can_be_restored_from_prepared_record(self):
        checked = self.verified()
        original_writer = review.write_record
        def crash(root, folder, record):
            if record["status"] == "applied":
                raise OSError("simulated interruption")
            original_writer(root, folder, record)
        with patch("lab_review.write_record", side_effect=crash), self.assertRaises(OSError):
            review.apply_verified(self.root, checked, checked.review.approval)
        ident = review.list_ids(self.root, review.HISTORY)[0]
        record, _, _, state = review.load_record(self.root, ident)
        self.assertEqual(record["status"], "prepared")
        self.assertEqual(state, "applied")
        review.restore(self.root, ident, "RESTAURAR " + ident)
        self.assertEqual((self.root / checked.review.target).read_bytes(), self.original)

    def test_failure_before_swap_preserves_original_and_releases_lock(self):
        checked = self.verified()
        original_writer = review.atomic_write
        def failure(root, relative, value):
            if str(relative) == checked.review.target:
                raise PermissionError("simulated locked file")
            original_writer(root, relative, value)
        with patch("lab_review.atomic_write", side_effect=failure), self.assertRaises(PermissionError):
            review.apply_verified(self.root, checked, checked.review.approval)
        ident = review.list_ids(self.root, review.HISTORY)[0]
        self.assertEqual(review.load_record(self.root, ident)[-1], "not_applied")
        self.assertEqual((self.root / checked.review.target).read_bytes(), self.original)
        with review.update_lock(self.root):
            pass

    def test_interrupted_restore_detects_completed_swap(self):
        checked = self.verified()
        ident = review.apply_verified(self.root, checked, checked.review.approval)
        original_writer = review.write_record
        def crash(root, folder, record):
            if record["status"] == "restored":
                raise OSError("simulated interrupted journal")
            original_writer(root, folder, record)
        with patch("lab_review.write_record", side_effect=crash), self.assertRaises(OSError):
            review.restore(self.root, ident, "RESTAURAR " + ident)
        self.assertEqual(review.load_record(self.root, ident)[-1], "restored")
        self.assertEqual((self.root / checked.review.target).read_bytes(), self.original)

    def test_cancel_and_concurrent_update_lock(self):
        folder = self.proposal()
        snapshot = review.inspect_proposal(self.root, folder.name)
        runner = self.runner()
        with self.assertRaises(InterruptedError):
            review.verify(self.root, snapshot, runner=runner, cancelled=lambda: True)
        runner.prepare.assert_not_called()
        with review.update_lock(self.root):
            with self.assertRaisesRegex(ValueError, "Outra revisão"):
                with review.update_lock(self.root):
                    self.fail("concurrent lock")
        with review.update_lock(self.root):
            pass

    def test_path_traversal_candidate_escape_and_invalid_records_are_rejected(self):
        for value in ("../language_quality.py", "/tmp/escape", "x" * 400, "", "20261101-000000-abcdef00/.."):
            with self.subTest(value=value), self.assertRaises(ValueError):
                review.inspect_proposal(self.root, value)
        folder = self.proposal()
        path = folder / "relatorio.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["candidate"] = "../../escape"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            review.inspect_proposal(self.root, folder.name)

    def test_symlink_or_junction_parent_and_linked_source_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "data"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("Symlink unavailable")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        try:
            with self.assertRaises(ValueError):
                review.status_text(self.root)
        finally:
            if link.is_symlink():
                link.unlink()
            else:
                os.rmdir(link)
        alias = self.root / "source_alias.py"
        os.link(self.root / lab.TARGETS[0], alias)
        with self.assertRaises(ValueError):
            review.read_bytes(self.root, lab.TARGETS[0])

    def test_no_ansi_or_bidi_terminal_injection(self):
        self.assertEqual(review.terminal_text("a\x1b[2J\u202eb\n\t"), "a\\u001b[2J\\u202eb\n\t")

    def test_status_command_is_read_only_and_needs_no_model(self):
        ask = Mock(side_effect=AssertionError("No Ollama"))
        answer = lab.handle_development("Yuna, mostre suas melhorias", self.root, ask)
        self.assertTrue(answer.startswith("Melhorias da Yuna:"))
        self.assertIn("Ainda não há propostas", answer)
        self.assertFalse((self.root / "data").exists())
        ask.assert_not_called()
        self.assertIsNone(lab.handle_development("APLICAR 123", self.root, ask))

    def test_cli_cancellation_before_tests_does_not_apply_or_call_docker(self):
        folder = self.proposal()
        with patch("builtins.input", side_effect=["r", folder.name, ""]), patch("builtins.print"), \
                patch("lab_review.verify") as verify:
            self.assertEqual(review.main(self.root), 0)
        verify.assert_not_called()
        self.assertFalse((self.root / review.HISTORY).exists())

    def test_cli_review_apply_and_restore(self):
        folder = self.proposal()
        snapshot = review.inspect_proposal(self.root, folder.name)
        with patch("builtins.input", side_effect=["r", folder.name, "TESTAR", snapshot.approval]), \
                patch("builtins.print"), patch("lab_review.lab.DockerTests", return_value=self.runner()):
            self.assertEqual(review.main(self.root), 0)
        self.assertEqual((self.root / snapshot.target).read_bytes(), snapshot.source)
        ident = review.list_ids(self.root, review.HISTORY)[0]
        with patch("builtins.input", side_effect=["v", ident, "RESTAURAR " + ident]), \
                patch("builtins.print"), patch("lab_review.lab.DockerTests") as runner:
            self.assertEqual(review.main(self.root), 0)
        runner.assert_not_called()
        self.assertEqual((self.root / snapshot.target).read_bytes(), self.original)

    def test_same_size_same_second_replacement_invalidates_python_bytecode(self):
        file = self.root / "fixture.py"
        file.write_bytes(b"value = 10\n")
        py_compile.compile(str(file), doraise=True)
        timestamp = int(file.stat().st_mtime)
        review.atomic_write(self.root, "fixture.py", b"value = 20\n")
        self.assertNotEqual(int(file.stat().st_mtime), timestamp)
        result = subprocess.run([sys.executable, "-I", "-B", "-c",
                                 "import sys; sys.path.insert(0, sys.argv[1]); import fixture; print(fixture.value)",
                                 str(self.root)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "20")


if __name__ == "__main__":
    unittest.main()
