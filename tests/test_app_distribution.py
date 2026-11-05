import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from app_maintenance import import_legacy_data, retire_legacy_launchers
from app_tools import launch_tool, prepare_model, tool_command


class DistributionTests(unittest.TestCase):
    def test_legacy_launchers_are_archived_only_by_known_name(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "iniciar_yuna.bat").write_text("customizacao antiga")
            (root / "meu_script.bat").write_text("preservar")
            (root / "Yuna.bat").write_text("entrada unica")
            self.assertEqual(retire_legacy_launchers(root), 1)
            self.assertFalse((root / "iniciar_yuna.bat").exists())
            backup = list(root.glob("data/inicializadores-antigos/*/iniciar_yuna.bat"))
            self.assertEqual(backup[0].read_text(), "customizacao antiga")
            self.assertTrue((root / "meu_script.bat").is_file())
            self.assertTrue((root / "Yuna.bat").is_file())
            self.assertEqual(retire_legacy_launchers(root), 0)

    def test_sqlite_wal_is_imported_as_consistent_copy_and_source_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new = root / "Pasta antiga", root / "Pasta nova"
            (old / "data").mkdir(parents=True)
            (old / "data/preferences.json").write_text('{"voz":"feminina"}')
            db = sqlite3.connect(old / "data/yuna.db")
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("CREATE TABLE facts(value TEXT)")
                db.execute("INSERT INTO facts VALUES ('Kaizen')")
                db.commit()
                import_legacy_data(old, new)
                copied = sqlite3.connect(new / "data/yuna.db")
                try:
                    self.assertEqual(copied.execute("SELECT value FROM facts").fetchone(), ("Kaizen",))
                finally:
                    copied.close()
                self.assertTrue((old / "data/yuna.db").is_file())
                self.assertFalse((new / "data/yuna.db-wal").exists())
                self.assertEqual((old / "data/preferences.json").read_text(), (new / "data/preferences.json").read_text())
            finally:
                db.close()

    def test_existing_destination_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("old", "new"):
                (root / name / "data").mkdir(parents=True)
                (root / name / "data/note.txt").write_text(name)
            with self.assertRaisesRegex(ValueError, "já tem dados"):
                import_legacy_data(root / "old", root / "new")
            self.assertEqual((root / "new/data/note.txt").read_text(), "new")

    def test_failed_copy_does_not_leave_partial_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "old/data").mkdir(parents=True)
            (root / "old/data/broken.db").write_bytes(b"not sqlite")
            with self.assertRaises(sqlite3.DatabaseError):
                import_legacy_data(root / "old", root / "new")
            self.assertFalse((root / "new/data").exists())
            self.assertEqual((root / "old/data/broken.db").read_bytes(), b"not sqlite")

    def test_same_or_nested_destination_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").mkdir()
            for target in (root, root / "data/nested"):
                with self.assertRaises(ValueError):
                    import_legacy_data(root, target)

    def test_tool_paths_with_spaces_no_shell_and_closed_allowlist(self):
        root = Path("Pasta com espaços").resolve()
        args = tool_command(root, "autoteste", executable=str(root / "pythonw.exe"))
        self.assertEqual(args, [str(root / "python.exe"), "-X", "utf8", str(root / "development_lab.py"), "--autoteste"])
        for tool in ("cmd", "web & shutdown", "../outro.py"):
            with self.assertRaises(ValueError):
                tool_command(root, tool)
        with patch("app_tools.subprocess.Popen") as process:
            launch_tool(root, "web")
            self.assertFalse(process.call_args.kwargs["shell"])
            self.assertEqual(process.call_args.args[0][-2:], ["--run", "web"])

    def test_model_choice_only_saved_after_successful_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stream = io.BytesIO(b'{"status":"pulling","total":100,"completed":50}\n{"status":"success"}\n')
            progress = []
            with patch("app_tools.local_api", return_value=stream) as api:
                prepare_model(root, "qwen2.5:1.5b", progress.append)
            self.assertEqual(api.call_args.args, ("/api/pull", {"model": "qwen2.5:1.5b", "stream": True}))
            self.assertIn("50%", progress[1])
            saved = root / "data/modelo_yuna.txt"
            self.assertEqual(saved.read_text().strip(), "qwen2.5:1.5b")
            with patch("app_tools.local_api", return_value=io.BytesIO(b'{"error":"sem espaco"}\n')):
                with self.assertRaisesRegex(RuntimeError, "sem espaco"):
                    prepare_model(root, "qwen2.5:3b")
            self.assertEqual(saved.read_text().strip(), "qwen2.5:1.5b")

    def test_model_incomplete_or_unknown_does_not_change_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("app_tools.local_api", return_value=io.BytesIO(b'{"status":"pulling"}\n')):
                with self.assertRaises(RuntimeError):
                    prepare_model(folder, "qwen2.5:3b")
            self.assertFalse((Path(folder) / "data/modelo_yuna.txt").exists())
            with patch("app_tools.local_api") as api:
                with self.assertRaises(ValueError):
                    prepare_model(folder, "untrusted-model")
                api.assert_not_called()

    def test_build_excludes_private_data_and_rejects_zip_traversal(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("yuna_build", root / "packaging/build_windows.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in ("data/yuna.db", ".env", ".venv/secret", "build/temp", "Yuna.bat", "avatar3d/meu.vrm"):
            self.assertFalse(module.included(name), name)
        self.assertTrue(module.included("yuna_desktop.py"))
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "runtime.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../escape.txt", "outside")
            with self.assertRaises(ValueError):
                module.safe_extract(archive, Path(folder) / "runtime")
            self.assertFalse((Path(folder) / "escape.txt").exists())


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class CenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"), patch(
                "compact_chat.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
            self.window = YunaDesktop()
        self.window.voice_index = 0
        self.controller = self.window.companion

    def tearDown(self):
        self.controller.closing = True
        self.window.close()
        if self.controller.center:
            self.controller.center.deleteLater()
        self.app.processEvents()

    def test_center_opening_enables_no_camera_microphone_or_download(self):
        with patch.object(self.window, "open_camera_viewer") as camera, patch.object(
                self.controller, "toggle_wake") as wake, patch("app_center.prepare_model") as download:
            self.controller.show_center()
            center = self.controller.center
            self.controller.show_center()
            self.assertIs(self.controller.center, center)
            camera.assert_not_called()
            wake.assert_not_called()
            download.assert_not_called()
            self.assertFalse(self.controller.wake_action.isChecked())

    def test_permission_controls_reuse_existing_actions_and_stop(self):
        self.controller.show_center()
        center = self.controller.center
        center.plug_voice.setChecked(True)
        self.assertTrue(self.controller.plug_voice.isChecked())
        self.controller.stop()
        center.sync_permissions()
        self.assertFalse(center.plug_voice.isChecked())

    def test_rejected_model_download_does_not_spawn_job(self):
        from PySide6.QtWidgets import QMessageBox
        self.controller.show_center()
        center = self.controller.center
        with patch("app_center.QMessageBox.question", return_value=QMessageBox.StandardButton.No), patch.object(
                center, "job") as job:
            center.download_model("qwen2.5:3b")
            job.assert_not_called()

    def test_advanced_button_routes_named_tool_and_preserves_main_chat(self):
        self.controller.show_center()
        with patch("app_center.launch_tool") as launch:
            self.controller.center.open_tool("revisar")
            self.assertEqual(launch.call_args.args[1], "revisar")
        self.assertFalse(self.controller.closing)


if __name__ == "__main__":
    unittest.main()
