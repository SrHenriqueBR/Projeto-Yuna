"""Diagnóstico transparente de falhas de ações da Yuna.

Não executa correções, downloads, atualizações ou comandos automaticamente.
Evita expor caminhos, senhas, tokens e mensagens internas ao usuário.
"""
from dataclasses import dataclass
import errno


@dataclass(frozen=True)
class FailureAdvice:
    category: str
    explanation: str
    next_step: str
    self_repair_possible: bool
    update_may_be_needed: bool

    def message(self):
        return (f"Não consegui concluir a tarefa. {self.explanation} "
                f"{self.next_step} "
                + ("Posso tentar novamente depois que você corrigir isso."
                   if self.self_repair_possible else
                   "Não vou modificar o sistema sem sua autorização."))


def diagnose_failure(error, *, capability_available=True):
    """Classifica causas conhecidas sem reproduzir detalhes sensíveis da exceção."""
    if not capability_available:
        return FailureAdvice(
            "unsupported", "Ainda não tenho um recurso implementado para essa ação.",
            "Posso registrar a necessidade de melhoria; será preciso atualizar meu código.",
            False, True)
    if isinstance(error, PermissionError) or (
            isinstance(error, OSError) and error.errno in (errno.EACCES, errno.EPERM)):
        return FailureAdvice(
            "permission", "O Windows negou permissão para a operação.",
            "Confira as permissões da pasta ou execute com a conta autorizada.",
            True, False)
    if isinstance(error, FileNotFoundError):
        return FailureAdvice(
            "not_found", "Não encontrei o arquivo ou programa solicitado.",
            "Confirme o nome ou informe o caminho correto.",
            True, False)
    if isinstance(error, (TimeoutError, ConnectionError)):
        return FailureAdvice(
            "unavailable", "O serviço ou programa não respondeu a tempo.",
            "Verifique se o serviço está aberto e tente novamente.",
            True, False)
    if isinstance(error, (ValueError, TypeError)):
        return FailureAdvice(
            "invalid_input", "Os dados fornecidos não são válidos para essa ação.",
            "Revise os parâmetros e tente novamente.",
            True, False)
    return FailureAdvice(
        "unexpected", "Encontrei um erro que ainda não sei diagnosticar com segurança.",
        "Posso registrar um relatório técnico local, sem dados sensíveis, para revisão.",
        False, True)
