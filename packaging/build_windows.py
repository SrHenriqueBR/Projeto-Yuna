"""Monta uma distribuição privada de Python + app para o Inno Setup, no CI Windows."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.14.10"
PYTHON_SHA256 = "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159"


def included(path):
    parts = Path(path).parts
    return (bool(parts) and parts[0] not in (".git", ".github", "data", ".venv", "build", "dist", "packaging")
            and not any(p in ("node_modules", "__pycache__") or p.startswith(".env") for p in parts)
            and Path(path).suffix.lower() not in (".bat", ".pyc", ".vrm"))


def safe_extract(archive, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination) or member.filename.startswith(("/", "\\")):
                raise ValueError("Caminho inválido no runtime.")
        bundle.extractall(destination)


def main():
    if sys.platform != "win32" or sys.version.split()[0] != PYTHON_VERSION:
        raise RuntimeError("Execute no Windows x64 com Python " + PYTHON_VERSION)
    version = subprocess.check_output(
        [sys.executable, "-c", "from self_model import VERSION; print(VERSION)"],
        cwd=ROOT, text=True).strip()
    if (not re.fullmatch(r"\d+\.\d+\.\d+", version)
            or any(int(part) > 65534 for part in version.split("."))):
        raise ValueError("A versão do aplicativo precisa ter três números válidos.")
    output = ROOT / "build/Yuna"
    output.mkdir(parents=True, exist_ok=False)
    app = output / "app"
    app.mkdir()
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    for name in tracked:
        if name and included(name) and (ROOT / name).is_file():
            target = app / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
    shutil.copytree(ROOT / "avatar3d/dist", app / "avatar3d/dist")
    (app / "installed-app.json").write_text(json.dumps({"runtime": PYTHON_VERSION, "entry": "../Yuna.exe", "version": version}), encoding="utf-8")
    runtime = output / "runtime"
    archive = ROOT / "build/python-embed.zip"
    url = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
    with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != PYTHON_SHA256:
        raise RuntimeError("O SHA-256 do runtime não corresponde ao publicado por python.org.")
    safe_extract(archive, runtime)
    pth = next(runtime.glob("python*._pth"))
    stdlib = next(runtime.glob("python*.zip")).name
    pth.write_text(stdlib + "\n.\nLib/site-packages\n../app\nimport site\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:",
                    "--target", str(runtime / "Lib/site-packages"),
                    "-r", str(ROOT / "requirements-mascote.txt"),
                    "-r", str(ROOT / "requirements-voz.txt"), "edge-tts>=7,<8"], check=True)
    # Bibliotecas nativas também precisam do CRT em uma máquina sem ferramentas de dev.
    # Usa somente o diretório redistribuível do Visual Studio, nunca DLLs do System32.
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    visual_studio = subprocess.check_output([str(vswhere), "-latest", "-property", "installationPath"], text=True).strip()
    candidates = sorted((Path(visual_studio) / "VC/Redist/MSVC").glob("*/x64/Microsoft.VC*.CRT"))
    if not candidates:
        raise RuntimeError("CRT redistribuível não encontrado no runner.")
    for dll in candidates[-1].glob("*.dll"):
        shutil.copy2(dll, runtime / dll.name)
    csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    version_info = ROOT / "build/VersionInfo.cs"
    version_info.write_text(
        'using System.Reflection;\n'
        f'[assembly: AssemblyVersion("{version}.0")]\n'
        f'[assembly: AssemblyFileVersion("{version}.0")]\n'
        f'[assembly: AssemblyInformationalVersion("{version}")]\n', encoding="utf-8")
    subprocess.run([str(csc), "/nologo", "/target:winexe", "/platform:x64", "/reference:System.Windows.Forms.dll",
                    "/out:" + str(output / "Yuna.exe"), str(ROOT / "packaging/Yuna.cs"), str(version_info)], check=True)
    # Imports reais no runtime distribuído, sem pip instalado na máquina do usuário.
    subprocess.run([str(runtime / "python.exe"), "-X", "utf8", "-c",
                    "import sqlite3, ssl, ctypes, PySide6, docx, openpyxl, pptx, pypdf, reportlab, sounddevice, faster_whisper, edge_tts; print('Runtime pronto')"], check=True)
    package_manifest = {}
    for path in output.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            package_manifest[path.relative_to(output).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / "package-manifest.json").write_text(json.dumps(package_manifest, indent=2), encoding="utf-8")
    print("Distribuição pronta:", output)


if __name__ == "__main__":
    main()
