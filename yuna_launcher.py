"""Launcher gráfico de Yuna: mostra falhas reais em vez de fechar em silêncio."""
import sys
from pathlib import Path
import traceback


def show_startup_error(message):
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None, "Yuna não conseguiu iniciar",
            "Encontrei um problema ao abrir a interface:\n\n"
            + message[:1300] + "\n\n"
            "Detalhes locais: data/yuna_startup_error.txt"
        )
    except Exception:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    None, message[:1600], "Yuna — erro de inicialização", 0x10
                )
            except Exception:
                pass


def run():
    try:
        from app_maintenance import retire_legacy_launchers
        try:
            retire_legacy_launchers(Path(__file__).resolve().parent)
        except OSError:
            pass  # Pasta protegida: abrir continua possível; nenhum arquivo arbitrário é removido.
        if "--tool" in sys.argv:
            from app_tools import TOOLS, launch_tool
            index = sys.argv.index("--tool")
            if index + 1 >= len(sys.argv) or sys.argv[index + 1] not in TOOLS:
                raise ValueError("Ferramenta inválida. Abra a Central da Yuna.")
            launch_tool(Path(__file__).resolve().parent, sys.argv[index + 1])
            return 0
        from yuna_desktop import main
        return main()
    except Exception as exc:
        root = Path(__file__).resolve().parent
        folder = root / "data"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "yuna_startup_error.txt").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        except OSError:
            pass
        if "--smoke-test" not in sys.argv:
            show_startup_error(type(exc).__name__ + ": " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(run())

