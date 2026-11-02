"""Revisão local de propostas: testar, aprovar, aplicar um arquivo e restaurar.

Não é uma ferramenta do modelo nem um endpoint web. A confirmação é digitada
no programa de revisão, depois de mostrar código e testes e verificar Docker.
O código novo só será carregado quando a pessoa reiniciar a Yuna.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import unicodedata

import development_lab as lab

IDENT = re.compile(r"[0-9]{8}-[0-9]{6}-[a-f0-9]{8}")
REFERENCES = lab.TARGETS + (lab.CONTRACT,)
HISTORY = "data/laboratorio_aplicacoes"
MAX_REPORT = 200000


def digest(value):
    return hashlib.sha256(value).hexdigest()


def text_source(value):
    # Igual a Path.read_text(encoding='utf-8-sig'), inclusive arquivos Windows.
    return value.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def safe_path(root, relative):
    """Recusa links, junções/reparse points e caminhos fora desta instalação."""
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ValueError("Caminho fora da instalação.")
    path = root
    for part in relative.parts:
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or (stat.S_ISREG(info.st_mode) and info.st_nlink > 1)):
            raise ValueError("Links, junções e arquivos com múltiplos vínculos não são aceitos.")
    return path


def read_bytes(root, relative, limit=lab.MAX_SOURCE * 4):
    path = safe_path(root, relative)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Arquivo ausente ou maior que o limite: " + str(relative))
    with path.open("rb") as stream:
        result = stream.read(limit + 1)
    if len(result) > limit:
        raise ValueError("O arquivo ultrapassou o limite de leitura.")
    return result


def read_json(root, relative):
    try:
        value = json.loads(read_bytes(root, relative, MAX_REPORT))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Relatório inválido: " + str(relative)) from exc
    if not isinstance(value, dict):
        raise ValueError("Relatório precisa ser um objeto JSON.")
    return value


def check_ident(ident):
    if not isinstance(ident, str) or not IDENT.fullmatch(ident):
        raise ValueError("ID inválido. Use um dos IDs exibidos na lista.")
    return ident


def atomic_write(root, relative, value):
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.stat() if path.exists() else None
    mode = stat.S_IMODE(previous.st_mode) if previous else 0o600
    descriptor, temporary = tempfile.mkstemp(prefix=".yuna-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        # Um .pyc baseado em tamanho/segundo não pode sobreviver à troca de um
        # módulo por outro do mesmo tamanho durante o mesmo segundo.
        if previous and int(os.stat(temporary).st_mtime) == int(previous.st_mtime):
            os.utime(temporary, (previous.st_atime, int(previous.st_mtime) + 1))
        safe_path(root, relative)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_record(root, folder, record):
    atomic_write(root, folder / "registro.json",
                 json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8"))


@contextmanager
def update_lock(root):
    """Lock do SO: fecha e libera inclusive após falha/encerramento do processo."""
    path = safe_path(root, HISTORY + "/operacao.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("Outra revisão está aplicando ou restaurando uma mudança.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@dataclass(frozen=True)
class Review:
    ident: str
    target: str
    summary: str
    objective: str
    source: bytes
    tests: bytes
    references: tuple
    fingerprint: str

    @property
    def approval(self):
        return "APLICAR " + self.ident + " " + self.fingerprint[:12]


def inspect_proposal(root, ident):
    """Recria a comparação dos arquivos reais; não confia no diff salvo."""
    folder = Path("data/laboratorio") / check_ident(ident)
    raw_report = read_bytes(root, folder / "relatorio.json", MAX_REPORT)
    try:
        report = json.loads(raw_report)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Relatório da proposta inválido.") from exc
    if not isinstance(report, dict):
        raise ValueError("Relatório da proposta inválido.")
    target = report.get("target")
    if report.get("id") != ident or target not in lab.TARGETS:
        raise ValueError("Relatório não corresponde a uma proposta permitida.")
    candidate = report.get("candidate")
    if candidate not in ("tentativa_1", "tentativa_2"):
        raise ValueError("Esta proposta não tem um arquivo revisável.")
    if report.get("status") not in ("tests_passed", "not_run", "failed"):
        raise ValueError("Geração incompleta, inválida ou cancelada. Gere outra proposta.")
    references = tuple((path, read_bytes(root, path)) for path in REFERENCES)
    current = dict(references)
    original = text_source(current[target])
    if digest(original.encode("utf-8")) != report.get("source_sha256"):
        raise ValueError("A base mudou desde a proposta. Gere uma nova melhoria sobre a versão atual.")
    # Relatórios antigos só tinham o hash do alvo. Eles também são retestados
    # com TODAS as referências atuais antes de oferecer a aplicação.
    base_hashes = report.get("reference_sha256")
    if base_hashes is not None and base_hashes != {
            path: digest(text_source(value).encode("utf-8")) for path, value in references}:
        raise ValueError("As referências da base mudaram. Gere uma nova proposta.")
    # A base instalada usa o limite em bytes do laboratório. Caracteres
    # multibyte e CRLF não podem gerar um módulo que ela deixaria de ler.
    source = read_bytes(root, folder / candidate / target, lab.MAX_SOURCE)
    tests = read_bytes(root, folder / candidate / "test_generated.py", 48000)
    attempts = report.get("attempts")
    number = int(candidate[-1])
    if not isinstance(attempts, list):
        raise ValueError("Lista de tentativas inválida.")
    attempt = next((item for item in attempts if isinstance(item, dict)
                    and item.get("attempt") == number), {})
    data = lab._validate(json.dumps({"summary": attempt.get("summary"),
                                   "source": text_source(source), "tests": text_source(tests)}),
                         target, original)
    objective = report.get("objective")
    if not isinstance(objective, str) or not 10 <= len(objective) <= 600:
        raise ValueError("Objetivo inválido no relatório.")
    fingerprint = digest(json.dumps({
        "id": ident, "target": target, "report": digest(raw_report),
        "source": digest(source), "tests": digest(tests),
        "base": {path: digest(value) for path, value in references},
    }, sort_keys=True).encode("utf-8"))
    return Review(ident, target, data["summary"], objective, source, tests, references, fingerprint)


def review_text(review):
    original = text_source(dict(review.references)[review.target])
    patch = "".join(difflib.unified_diff(
        original.splitlines(True), text_source(review.source).splitlines(True),
        fromfile="instalado/" + review.target, tofile="proposto/" + review.target))
    return ("Proposta: " + review.ident + "\nArquivo: " + review.target
            + "\nObjetivo: " + review.objective + "\nResumo do modelo: " + review.summary
            + "\n\nALTERAÇÕES REAIS:\n" + patch
            + "\n\nTESTES ADICIONAIS COMPLETOS:\n" + text_source(review.tests)
            + "\nTestes aprovados não substituem a revisão do código. Ao reiniciar a Yuna,"
              " o módulo aplicado roda com as permissões normais da sua conta.")


@dataclass(frozen=True)
class VerifiedReview:
    review: Review
    baseline: lab.TestResult
    candidate: lab.TestResult


def verify(root, review, *, progress=None, cancelled=None, runner=None):
    """Sempre testa novamente, em pasta nova, somente através de Docker local."""
    progress = progress or (lambda value: None)
    fresh = inspect_proposal(root, review.ident)
    if fresh.fingerprint != review.fingerprint:
        raise ValueError("A proposta mudou durante a revisão. Abra a revisão novamente.")
    runner = runner or lab.DockerTests(cancelled)
    lab.check_cancel(cancelled)
    if not runner.prepare():
        raise ValueError("Não é possível aplicar sem testes em Docker local. " + runner.reason)
    with tempfile.TemporaryDirectory(prefix="yuna-revisao-") as directory:
        workspace = Path(directory)
        workspace.chmod(0o755)
        (workspace / "tests").mkdir(mode=0o755)
        for path, value in review.references:
            (workspace / path).write_bytes(value)
            (workspace / path).chmod(0o644)
        progress("Revisão · testando a base atual em contêiner sem rede")
        lab.check_cancel(cancelled)
        baseline = runner.run(workspace)
        if baseline.status != "passed" or baseline.tests < 1:
            raise ValueError("A base atual não passou nos testes.\n" + baseline.detail[-4000:])
        (workspace / review.target).write_bytes(review.source)
        (workspace / "tests/test_generated.py").write_bytes(review.tests)
        (workspace / "tests/test_generated.py").chmod(0o644)
        progress("Revisão · testando a melhoria e seus testes adicionais")
        lab.check_cancel(cancelled)
        candidate = runner.run(workspace)
        if candidate.status != "passed" or candidate.tests <= baseline.tests:
            raise ValueError("A melhoria não passou ou não executou testes adicionais.\n"
                             + candidate.detail[-4000:])
    lab.check_cancel(cancelled)
    if inspect_proposal(root, review.ident).fingerprint != review.fingerprint:
        raise ValueError("Arquivos mudaram durante os testes. Abra a revisão novamente.")
    return VerifiedReview(review, baseline, candidate)


def apply_verified(root, verified, approval):
    """Uma troca atômica, com backup exato e registro preparado antes da troca."""
    review = verified.review
    if approval != review.approval:
        raise ValueError("Confirmação diferente da exibida. Nenhum código foi aplicado.")
    if (verified.baseline.status != "passed" or verified.candidate.status != "passed"
            or verified.baseline.tests < 1 or verified.candidate.tests <= verified.baseline.tests):
        raise ValueError("Testes isolados completos são necessários antes de aplicar.")
    with update_lock(root):
        if inspect_proposal(root, review.ident).fingerprint != review.fingerprint:
            raise ValueError("Arquivos mudaram após os testes. Revise e teste novamente.")
        ident = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(4)
        folder = Path(HISTORY) / ident
        safe_path(root, folder).mkdir()
        before = dict(review.references)[review.target]
        atomic_write(root, folder / "antes.py", before)
        atomic_write(root, folder / "depois.py", review.source)
        atomic_write(root, folder / "test_generated.py", review.tests)
        record = {"id": ident, "proposal": review.ident, "target": review.target,
                  "status": "prepared", "before_sha256": digest(before),
                  "after_sha256": digest(review.source), "review_sha256": review.fingerprint,
                  "created_at": datetime.now(timezone.utc).isoformat(),
                  "baseline": asdict(verified.baseline), "candidate": asdict(verified.candidate)}
        write_record(root, folder, record)
        # Verificação final também cobre alterações enquanto o backup era salvo.
        if inspect_proposal(root, review.ident).fingerprint != review.fingerprint:
            raise ValueError("Arquivos mudaram antes da substituição. Nenhum código foi aplicado.")
        atomic_write(root, review.target, review.source)
        record["status"] = "applied"
        write_record(root, folder, record)
        return ident


def load_record(root, ident):
    folder = Path(HISTORY) / check_ident(ident)
    record = read_json(root, folder / "registro.json")
    if record.get("id") != ident or record.get("target") not in lab.TARGETS:
        raise ValueError("Registro não corresponde a uma aplicação permitida.")
    if record.get("status") not in ("prepared", "applied", "restoring", "restored"):
        raise ValueError("Estado de aplicação inválido.")
    before = read_bytes(root, folder / "antes.py")
    after = read_bytes(root, folder / "depois.py")
    if (digest(before) != record.get("before_sha256")
            or digest(after) != record.get("after_sha256") or before == after):
        raise ValueError("Backup alterado ou inválido. Não será usado para restauração.")
    current = read_bytes(root, record["target"])
    # Recuperar uma interrupção entre a troca atômica e a escrita do registro.
    if record["status"] == "prepared":
        effective = "applied" if current == after else "not_applied" if current == before else "conflict"
    elif record["status"] == "restoring":
        effective = "restored" if current == before else "applied" if current == after else "conflict"
    elif record["status"] == "applied":
        effective = "applied" if current == after else "conflict"
    else:
        effective = "restored"
    return record, before, after, effective


def restore(root, ident, approval):
    if approval != "RESTAURAR " + check_ident(ident):
        raise ValueError("Restauração não confirmada. Nenhum código foi alterado.")
    with update_lock(root):
        record, before, after, effective = load_record(root, ident)
        if effective != "applied":
            raise ValueError("Não é possível restaurar: o arquivo foi alterado depois, já foi"
                             " restaurado ou a aplicação não ocorreu. Veja o histórico.")
        folder = Path(HISTORY) / ident
        record["status"] = "restoring"
        write_record(root, folder, record)
        if read_bytes(root, record["target"]) != after:
            raise ValueError("O arquivo mudou antes da restauração. Nenhum código foi substituído.")
        atomic_write(root, record["target"], before)
        record["status"] = "restored"
        record["restored_at"] = datetime.now(timezone.utc).isoformat()
        write_record(root, folder, record)
        return record["target"]


def list_ids(root, directory):
    path = safe_path(root, directory)
    if not path.exists():
        return []
    # IDs têm segundos + aleatoriedade. mtime_ns preserva a ordem de alterações
    # inclusive quando duas operações terminam no mesmo segundo.
    entries = [(item.lstat().st_mtime_ns, item.name) for item in path.iterdir()
               if IDENT.fullmatch(item.name)]
    return [ident for _, ident in sorted(entries, reverse=True)]


def status_text(root):
    lines = ["Melhorias da Yuna:"]
    proposal_states = {"tests_passed": "testes passaram na geração", "not_run": "somente sintaxe verificada",
                       "failed": "falhou nos testes", "baseline_failed": "base falhou nos testes",
                       "invalid": "proposta inválida", "cancelled": "cancelada", "error": "erro na geração",
                       "preparing": "geração iniciada"}
    for ident in list_ids(root, "data/laboratorio")[:30]:
        try:
            report = read_json(root, Path("data/laboratorio") / ident / "relatorio.json")
            target = report.get("target")
            if target not in lab.TARGETS:
                raise ValueError("Alvo inválido")
            state = report.get("status")
            label = proposal_states.get(state, "estado desconhecido") if isinstance(state, str) else "estado inválido"
            lines.append(f"{ident} · {target} · {label}")
        except (OSError, ValueError):
            lines.append(ident + " · relatório indisponível")
    if len(lines) == 1:
        lines.append("Ainda não há propostas. Crie uma em laboratorio_yuna.bat.")
    lines.append("\nAplicações recentes (até 20):")
    states = {"applied": "aplicada", "restored": "restaurada", "conflict": "arquivo mudou depois",
              "not_applied": "não aplicada"}
    identifiers = list_ids(root, HISTORY)
    for ident in identifiers[:20]:
        try:
            record, _, _, effective = load_record(root, ident)
            lines.append(f"{ident} · {record['target']} · {states[effective]}")
        except (OSError, ValueError):
            lines.append(ident + " · registro ou backup indisponível")
    if not identifiers:
        lines.append("Nenhuma aplicação registrada.")
    lines.append("Abra revisar_melhorias_yuna.bat para revisar, testar, aplicar ou restaurar."
                 " Feche a Yuna antes de aplicar e abra novamente depois.")
    return "\n".join(lines)


def terminal_text(value):
    """Código e resumos são dados: não podem enviar controles ao terminal."""
    return "".join(char if char in "\n\t" or unicodedata.category(char)[0] != "C"
                   else "\\u%04x" % ord(char) for char in value)


def main(root=None):
    root = Path(root or Path(__file__).resolve().parent)
    try:
        print(terminal_text(status_text(root)))
        print("\n[R] Revisar proposta  [V] Voltar a uma versão anterior  [Enter] Sair")
        choice = input("Escolha: ").strip().casefold()
        if choice == "r":
            review = inspect_proposal(root, input("ID da proposta: ").strip())
            print(terminal_text(review_text(review)))
            print("\nConfira a comparação acima e feche a Yuna antes de aplicar.")
            if input("Digite TESTAR para verificar em Docker (Enter cancela): ").strip() != "TESTAR":
                return 0
            verified = verify(root, review, progress=print)
            print(f"\nBase: {verified.baseline.tests} testes. Melhoria: {verified.candidate.tests} testes.")
            print("Para aplicar exatamente esta revisão, digite: " + review.approval)
            answer = input("Confirmação (Enter cancela): ").strip()
            if not answer:
                return 0
            ident = apply_verified(root, verified, answer)
            print("Melhoria aplicada. Backup: " + ident + ". Reinicie a Yuna para carregar o módulo.")
        elif choice == "v":
            ident = check_ident(input("ID da aplicação no histórico: ").strip())
            record, _, _, effective = load_record(root, ident)
            if effective != "applied":
                raise ValueError("Esta aplicação não pode ser restaurada sobre o arquivo atual.")
            print("Será restaurado somente: " + record["target"])
            print("Feche a Yuna. Para voltar à cópia anterior, digite: RESTAURAR " + ident)
            answer = input("Confirmação (Enter cancela): ").strip()
            if not answer:
                return 0
            print("Restaurado: " + restore(root, ident, answer) + ". Reinicie a Yuna.")
        elif choice:
            raise ValueError("Opção inválida. Nenhuma alteração feita.")
        return 0
    except (KeyboardInterrupt, InterruptedError, EOFError):
        print("Revisão interrompida. Consulte o histórico se a troca já havia começado.")
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        print(terminal_text("Não concluí: " + str(exc)))
        print("Consulte o histórico; backups permitem verificar uma troca interrompida.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
