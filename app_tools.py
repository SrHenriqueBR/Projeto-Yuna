"""Entradas internas da Central: processos explícitos e argumentos fechados."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

from model_config import load_selected_model, save_selected_model

TOOLS = {
    "terminal": ("Conversa no terminal", "yuna.py", ()),
    "mascote": ("Interface flutuante clássica", "yuna_overlay.py", ()),
    "web": ("Chat no navegador", "yuna_web.py", ()),
    "laboratorio": ("Laboratório de melhorias", "development_lab.py", ()),
    "revisar": ("Revisar ou restaurar melhorias", "lab_review.py", ()),
    "autoteste": ("Testar a base da Yuna", "development_lab.py", ("--autoteste",)),
    "gestao": ("Configurar gestão local", "yuna_governance.py", ("--configurar-proprietario",)),
    "3d": ("Abrir avatar 3D", "app_tools.py", ("--serve-3d",)),
}
RELEASE_URL = "https://github.com/SrHenriqueBR/Projeto-Yuna/releases/latest"


def tool_command(root, tool, executable=None):
    if tool not in TOOLS:
        raise ValueError("Ferramenta desconhecida.")
    root = Path(root).resolve()
    python = Path(executable or sys.executable)
    if python.name.casefold() == "pythonw.exe":
        python = python.with_name("python.exe")
    script, args = TOOLS[tool][1:]
    return [str(python), "-X", "utf8", str(root / script), *args]


def launch_tool(root, tool):
    root = Path(root).resolve()
    # Runner mantém a mensagem de erro/resultado visível antes de fechar o console.
    command = tool_command(root, tool)
    args = [command[0], "-X", "utf8", str(root / "app_tools.py"), "--run", tool]
    return subprocess.Popen(args, cwd=str(root), shell=False,
                            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))


def local_api(path, payload=None, timeout=5):
    # Endereço fixo de loopback, sem proxy ou redirecionamentos.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request("http://127.0.0.1:11434" + path, data=data,
                                     headers={"Content-Type": "application/json"})
    return opener.open(request, timeout=timeout)


def installation_status(root):
    root = Path(root)
    lines = ["Yuna instalada: " + str(root), "Modelo selecionado: " + load_selected_model(root)]
    voice = all(importlib.util.find_spec(name) for name in ("sounddevice", "faster_whisper"))
    lines.append("Voz local: " + ("pronta" if voice else "bibliotecas ausentes; prepare pelo Yuna.bat ou reinstale o app"))
    lines.append("Avatar 3D: " + ("pronto" if (root / "avatar3d/dist/index.html").is_file()
                                 else "disponível no instalador; no código-fonte requer compilação"))
    try:
        with local_api("/api/tags") as response:
            models = json.loads(response.read(1024 * 1024)).get("models", [])
        names = [str(model.get("name", "")) for model in models]
        lines.append("Ollama: respondendo no computador.")
        lines.append("Modelos: " + (", ".join(names[:20]) or "nenhum; escolha um abaixo"))
    except (OSError, ValueError):
        lines.append("Ollama: sem resposta. Instale/abra o Ollama antes de baixar um modelo ou conversar livremente.")
    return "\n".join(lines)


def prepare_model(root, model, progress=lambda text: None):
    if model not in ("qwen2.5:1.5b", "qwen2.5:3b"):
        raise ValueError("Modelo não suportado pela Central.")
    progress("Preparando " + model + " pelo Ollama local…")
    done = False
    with local_api("/api/pull", {"model": model, "stream": True}, timeout=300) as response:
        for raw in response:
            if len(raw) > 65536:
                raise ValueError("Resposta inesperada do Ollama.")
            item = json.loads(raw)
            if item.get("error"):
                raise RuntimeError(str(item["error"])[:250])
            status = str(item.get("status", ""))[:100]
            total, completed = item.get("total", 0), item.get("completed", 0)
            if isinstance(total, int) and isinstance(completed, int) and total > 0:
                status += f" · {min(100, max(0, completed * 100 // total))}%"
            progress(status)
            if item.get("status") == "success":
                done = True
    if not done:
        raise RuntimeError("O download não foi concluído; mantive o modelo anterior.")
    save_selected_model(root, model)
    return "Modelo pronto: " + model + ". Feche a Yuna pelo menu Sair e abra novamente para usar a escolha."


def configure_shortcuts(root, startup=None):
    if sys.platform != "win32":
        raise RuntimeError("Atalhos exigem Windows.")
    script = Path(root) / "scripts/atalhos.ps1"
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    args = [str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-Python", sys.executable]
    if startup is not None:
        args += ["-Inicializacao", "Ativar" if startup else "Desativar"]
    result = subprocess.run(args, shell=False, capture_output=True, timeout=20,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("Não consegui configurar os atalhos desta conta do Windows.")
    return "Atalhos atualizados." if startup is None else "Inicialização com o Windows " + ("ativada." if startup else "desativada.")


def serve_3d(root):
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    import webbrowser
    folder = Path(root) / "avatar3d/dist"
    if not (folder / "index.html").is_file():
        raise RuntimeError("O 3D não foi compilado nesta cópia. Use o instalador da Yuna ou compile avatar3d com npm install e npm run build.")
    class Handler(SimpleHTTPRequestHandler):
        def list_directory(self, path):
            self.send_error(404)
            return None
    with ThreadingHTTPServer(("127.0.0.1", 5173), partial(Handler, directory=str(folder))) as server:
        print("Avatar 3D local. Feche esta janela para encerrar. Use Conectar Yuna 3D na janela completa.")
        webbrowser.open("http://127.0.0.1:5173")
        server.serve_forever()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", choices=sorted(TOOLS))
    parser.add_argument("--serve-3d", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.serve_3d:
        serve_3d(root)
        return 0
    if args.run:
        try:
            result = subprocess.run(tool_command(root, args.run), cwd=str(root), shell=False)
            print("\nFerramenta encerrada. Código:", result.returncode)
            return result.returncode
        except (OSError, RuntimeError) as exc:
            print("Não consegui abrir:", exc)
            return 1
        finally:
            try:
                input("Pressione Enter para fechar esta janela…")
            except EOFError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
