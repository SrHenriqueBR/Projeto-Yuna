"""Bootstrap curto da tarefa de despertar; não mantém o timer de energia ativo."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != "win32":
        return 1
    root = Path(__file__).resolve().parent
    subprocess.Popen([sys.executable, str(root / "yuna_launcher.py"), "--background"],
        cwd=str(root), shell=False, close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
