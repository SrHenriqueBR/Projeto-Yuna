"""Reações visuais discretas da Yuna a texto, sem inferir emoção real do usuário.

O classificador só escolhe um gesto de desenho; não acessa memória ou rede.
"""
import re

_RULES = (
    (re.compile(r"(?i)\b(?:haha|hahaha|kkkk+|rsrs+|hehe)\b"), "laugh", "happy"),
    (re.compile(r"(?i)\b(?:parab[eé]ns|conseguimos|deu certo|maravilha|excelente)\b"), "happy", "happy"),
    (re.compile(r"(?i)\b(?:opa|ol[aá]|oi|bom dia|boa noite|boa tarde)\b"), "wave", "happy"),
    (re.compile(r"(?i)\b(?:surpresa|incr[ií]vel|uau|nossa)\b"), "surprised", "surprised"),
    (re.compile(r"(?i)\b(?:desculp[ae]|sinto muito|infelizmente)\b"), "shy", "sad"),
    (re.compile(r"(?i)\b(?:como funciona|ser[aá] que|me conta|vamos descobrir|que interessante)\b"), "curious", "neutral"),
)


def reaction_for_text(text, *, private=False):
    """Retorna (pose, emotion) ou None; ignora texto privado ou muito curto."""
    if private or not isinstance(text, str) or len(text.strip()) < 4:
        return None
    # Não processar trechos grandes de documentos como gatilhos de expressão.
    sample = text[:500]
    for pattern, pose, emotion in _RULES:
        if pattern.search(sample):
            return pose, emotion
    return None
