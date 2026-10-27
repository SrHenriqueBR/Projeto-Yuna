"""Memórias úteis a partir de frases naturais do Kaizen, sem chamar outra IA.

Só fatos/preferências escritos pela própria pessoa podem ser memorizados.
Informações sensíveis, perguntas, citações e resultados de ferramentas nunca
viram fatos permanentes automaticamente. O histórico normal segue no SQLite.
"""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class MemoryIntent:
    action: str
    detail: str = ""
    automatic: bool = False


SENSITIVE = re.compile(
    r"\b(?:cpf|cnpj|rg|senha|password|pin|cvv|token|segredo|chave|"
    r"pix|banco|cartao|credito|emprestimo|renda|salario|divida|"
    r"endereco|rua|apartamento|numero\s+da\s+casa|"
    r"doenca|diagnostico|medicamento|remedio|gravidez|sexo|"
    r"sexualidade|religiao|partido|voto|politica|"
    r"conta|hospital|cirurgia|saude)\b|"
    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|"
    r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\b",
    re.I
)


def fold(text):
    text = unicodedata.normalize("NFKD", str(text).casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _strip_vocative(text):
    return re.sub(r"^\s*(?:(?:ei|oi|ola)\s+)?yuna[,!: ]+", "", str(text), flags=re.I).strip()


def parse_memory_intent(message):
    if not isinstance(message, str) or not message.strip() or len(message) > 700:
        return None
    text = _strip_vocative(message).strip()
    if text.startswith("/"):
        return None
    normalized = fold(text).strip(" .!?")
    if re.fullmatch(r"(?:o que voce lembra(?: de mim)?|"
                    r"quais (?:coisas|preferencias|lembrancas) voce (?:lembra|guardou)|"
                    r"mostre (?:suas )?memorias|me diga o que voce lembra de mim)", normalized):
        return MemoryIntent("list")
    recalled = re.fullmatch(
        r"(?:voce lembra|lembra|o que voce (?:lembra|sabe)|"
        r"o que eu (?:disse|falei|te contei))\s+(?:de|sobre|a respeito de)\s+(.+)",
        normalized
    )
    if recalled:
        return MemoryIntent("recall", recalled[1].strip())
    if re.match(r"^(?:esquece|esqueca|apague|apaga)\s+tud", normalized):
        return MemoryIntent("refuse_all")
    forget = re.match(
        r"^(?:esquece|esqueca|apague|apaga)\s+(?:da sua memoria\s+)?"
        r"(?:que\s+|a informacao\s+(?:de\s+)?que\s+)(.{3,400})$",
        normalized
    )
    if forget:
        return MemoryIntent("forget", forget[1].strip())

    explicit = re.match(
        r"^(?:lembre(?:-se)?|lembra|guarde|guarda|anote|anota|"
        r"memorize|memoriza|aprenda|aprende|registre|registra)\s+"
        r"(?:na sua memoria\s+|para depois\s+)?(?:de\s+)?que\s+(.+)$",
        text, re.I
    )
    if explicit:
        return MemoryIntent("store", explicit[1].strip(" .!?"), automatic=False)

    # Preferências simples, declaradas diretamente pelo usuário.
    # Não deduzir fatos de uma pergunta ou de opinião da própria IA.
    pref = re.fullmatch(
        r"(?:eu\s+)?(?:prefiro|gosto de|adoro)\s+(.{3,260})", text, re.I
    )
    if pref and "?" not in text and not re.search(r'["“”]', text):
        return MemoryIntent("store", text.strip(" .!"), automatic=True)
    return None


def memory_response(memory, intent):
    if intent.action == "list":
        facts = memory.facts()
        if not facts:
            return "Ainda não guardei preferências ou fatos permanentes seus. Podemos começar conversando. 🖤"
        return "Estas são as lembranças que você compartilhou comigo:\n" + "\n".join(
            f"• {value}" for _, value in facts
        )
    if intent.action == "recall":
        matches = []
        query = set(re.findall(r"[a-z0-9]{3,}", fold(intent.detail))) - {
            "sobre", "isso", "meu", "minha", "com", "que", "voce"
        }
        for _, fact in memory.facts():
            words = set(re.findall(r"[a-z0-9]{3,}", fold(fact)))
            if query and query & words:
                matches.append(fact)
        if not matches:
            return ("Não encontrei uma lembrança permanente sobre esse assunto. "
                    "Posso guardar uma informação se você me contar.")
        return "Lembro que você me contou:\n" + "\n".join("• " + t for t in matches[:5])
    if intent.action == "refuse_all":
        return ("Para apagar todas as minhas memórias de uma vez, use o controle "
                "de exclusão com confirmação. Não vou apagar tudo por uma frase ambígua.")
    if intent.action == "forget":
        matches = [(i, t) for i, t in memory.facts()
                   if fold(intent.detail) in fold(t)]
        if len(matches) == 1:
            memory.forget(matches[0][0])
            return "Entendi, Kaizen. Apaguei essa lembrança permanente."
        if not matches:
            return "Não encontrei essa lembrança nas memórias permanentes."
        return "Encontrei mais de uma lembrança parecida; seja mais específico sobre qual devo apagar."
    if intent.action != "store":
        return None
    fact = intent.detail.strip()
    if not 4 <= len(fact) <= 400 or SENSITIVE.search(fold(fact)):
        if intent.automatic:
            return None
        return ("Essa informação pode ser sensível ou longa demais. "
                "Não vou guardá-la como memória permanente. "
                "Ainda posso conversar sobre ela sem armazená-la como lembrança.")
    if "?" in fact or re.search(r"https?://|\b(?:http|www)\b", fact, re.I):
        return None if intent.automatic else "Não vou guardar perguntas nem endereços da internet como lembranças suas."
    if any(fold(t) == fold(fact) for _, t in memory.facts()):
        return None if intent.automatic else "Essa informação já está guardada. 🖤"
    if len(memory.facts()) >= 20:
        return None if intent.automatic else (
            "Minhas 20 memórias permanentes estão ocupadas. "
            "Peça para eu esquecer uma lembrança antes de guardar outra."
        )
    memory.remember(fact)
    return None if intent.automatic else "Guardei essa informação na minha memória, Kaizen. 🖤"
