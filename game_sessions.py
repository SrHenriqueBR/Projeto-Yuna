"""Sessões de jogo opt-in: contrato de segurança antes de ligar controles.

Este módulo NÃO lê a tela, não gera teclas, não usa gamepad virtual e não
executa jogos. Somente autoriza propostas validadas de movimentos curtos.
Um adaptador de controle futuro deverá verificar o processo em foco novamente
na hora de executar cada ação, além das checagens abaixo.
"""
from dataclasses import dataclass
from pathlib import PureWindowsPath
import math
import time

from emergency_stop import is_stop_request


ACTIONS = frozenset({
    "move_forward", "move_backward", "move_left", "move_right",
    "look_left", "look_right", "jump", "interact", "crouch",
    "pause",
})
MAX_ACTION_DURATION = 0.5
MAX_SESSION_SECONDS = 600
MAX_ACTIONS_PER_SESSION = 120


def normalize_executable(path):
    """Somente .exe local absoluto; jamais executar caminhos nem strings shell."""
    if not isinstance(path, str) or len(path) > 512:
        raise ValueError("Executável inválido")
    value = path.strip().strip('"')
    if not value or any(ord(ch) < 32 for ch in value) or any(
            ch in value for ch in ("|", "<", ">", "*", "?")):
        raise ValueError("Executável inválido")
    exe = PureWindowsPath(value)
    if (exe.drive.startswith("\\\\") or not exe.drive or not exe.root
            or exe.suffix.casefold() != ".exe"
            or len(exe.parts) < 3 or ".." in exe.parts):
        raise ValueError("Selecione o executável local completo de um jogo")
    return str(exe).casefold()


@dataclass(frozen=True)
class GameAction:
    game_executable: str
    action: str
    seconds: float


class GameSession:
    """Concessão temporária e por jogo, sempre desligada no início."""

    def __init__(self):
        self._executable = None
        self._expires_at = 0.0
        self._proposed = 0

    @property
    def active(self):
        return self._executable is not None

    def authorize(self, game_executable, *, approved, single_player,
                  duration_seconds=300, now=None):
        if approved is not True or single_player is not True:
            raise PermissionError(
                "Jogar exige autorização explícita e sessão individual/offline"
            )
        if (type(duration_seconds) not in (float, int) or
                not math.isfinite(duration_seconds) or
                not 0 < duration_seconds <= MAX_SESSION_SECONDS):
            raise ValueError("Duração de sessão inválida")
        executable = normalize_executable(game_executable)
        moment = time.monotonic() if now is None else float(now)
        self._executable = executable
        self._expires_at = moment + duration_seconds
        self._proposed = 0
        return True

    def propose(self, action, *, foreground_executable, seconds=0.15, now=None):
        """Produz proposta curta, NÃO a executa; execução requer outro controle."""
        moment = time.monotonic() if now is None else float(now)
        if not self.active or moment >= self._expires_at:
            self.stop()
            raise PermissionError("Sessão de jogo não está autorizada ou expirou")
        # O caminho informado pelo modelo ou usuário NÃO autentica o processo:
        # um futuro adaptador deverá confirmar PID, HWND e executável via Windows.
        if normalize_executable(foreground_executable) != self._executable:
            self.stop()
            raise PermissionError("Outro aplicativo está em foco; sessão encerrada")
        if action not in ACTIONS:
            raise ValueError("Comando de jogo desconhecido")
        if type(seconds) not in (float, int) or not math.isfinite(seconds) or (
                not 0 < seconds <= MAX_ACTION_DURATION):
            raise ValueError("Comando longo demais para controle seguro")
        if self._proposed >= MAX_ACTIONS_PER_SESSION:
            self.stop()
            raise PermissionError("Limite de ações atingido")
        self._proposed += 1
        return GameAction(self._executable, action, float(seconds))

    def request_stop(self, text):
        """Aceita Break080111 e frases de parada já padronizadas pela Yuna."""
        if is_stop_request(text):
            self.stop()
            return True
        return False

    def stop(self):
        """Revoga a sessão e impede qualquer nova proposta sem autorização."""
        self._executable = None
        self._expires_at = 0.0
        self._proposed = 0
