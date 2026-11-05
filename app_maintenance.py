"""Migração local sem sobrescrever memória existente ou executar arquivos antigos."""
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import tempfile

LEGACY_LAUNCHERS = (
    "configurar_gestao_yuna.bat", "configurar_yuna_app.bat", "diagnosticar_yuna.bat",
    "iniciar_yuna.bat", "iniciar_yuna_3d.bat", "iniciar_yuna_mascote.bat",
    "iniciar_yuna_segundo_plano.bat", "iniciar_yuna_terminal.bat", "iniciar_yuna_web.bat",
    "instalar_voz_yuna.bat", "instalar_yuna.bat", "laboratorio_yuna.bat",
    "revisar_melhorias_yuna.bat", "testar_yuna.bat",
)


def retire_legacy_launchers(root):
    root = Path(root)
    found = [root / name for name in LEGACY_LAUNCHERS
             if (root / name).is_file() and not (root / name).is_symlink()]
    if not found:
        return 0
    folder = root / "data/inicializadores-antigos" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True, exist_ok=False)
    for path in found:
        shutil.move(str(path), str(folder / path.name))
    return len(found)


def import_legacy_data(source, target):
    source = Path(source).resolve() / "data"
    target = Path(target).resolve() / "data"
    if not source.is_dir() or source == target or source in target.parents or target in source.parents:
        raise ValueError("Escolha a pasta de outra instalação da Yuna, que contenha data.")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Esta instalação já tem dados. A memória existente foi preservada; não faço mescla automática.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="yuna-import-", dir=target.parent) as temporary:
        stage = Path(temporary) / "data"
        stage.mkdir()
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            if any((source / Path(*relative.parts[:n])).is_symlink()
                   for n in range(1, len(relative.parts) + 1)):
                continue
            if path.is_dir():
                (stage / relative).mkdir(parents=True, exist_ok=True)
                continue
            if not path.is_file() or path.name.endswith(("-wal", "-shm", "-journal")):
                continue
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.casefold() == ".db":
                # Snapshot SQLite inclui transações confirmadas que ainda estão no WAL.
                old = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
                new = sqlite3.connect(destination)
                try:
                    old.backup(new)
                finally:
                    new.close()
                    old.close()
            else:
                shutil.copy2(path, destination)
        if target.exists():
            target.rmdir()  # Só remove diretório vazio; recusa corrida com novos dados.
        stage.rename(target)
    return "Memórias copiadas. A pasta anterior não foi modificada."


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-data", required=True)
    args = parser.parse_args()
    try:
        print(import_legacy_data(args.import_data, Path(__file__).resolve().parent))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print("Importação não concluída:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
