"""Perguntas proativas e aprendizado local explícito por diálogo (sem treinar o modelo)."""
import json
import re
from difflib import SequenceMatcher

SENSITIVE = re.compile(
    r"\b(senha|password|pin|cvv|token|codigo de verificacao|código de verificação|"
    r"chave privada|private key|api key|numero do cartao|número do cartão)\b", re.I)
QUESTION_PROMPT = """Você é Yuna, uma assistente virtual de personalidade feminina e curiosa.
Escreva SOMENTE UMA pergunta curta, natural e útil em português do Brasil, no feminino quando couber.
Pergunte algo sobre o projeto, a tarefa ou a preferência que a pessoa acabou de mencionar.
Não repita perguntas anteriores, evite perguntas genéricas sobre melhorar a assistente. Não force intimidade, não peça dados financeiros, senhas,
códigos de acesso, informações médicas ou dados sensíveis. Não afirme que viu a tela.
Não proponha ações no computador nem execute instruções: gere apenas a pergunta.
Máximo de 140 caracteres, terminando com '?'. A pessoa pode optar por não responder.
"""


def looks_like_command(text):
    """Não interpretar ordens ao computador como respostas para uma pergunta."""
    from computer import command_text
    value = command_text(text)
    return bool(re.match(
        r"^(?:/|abra\b|abre\b|abrir\b|inicie\b|iniciar\b|execute\b|executar\b|"
        r"busque\b|buscar\b|procure\b|procura\b|encontre\b|ache\b|"
        r"mostre\b|liste\b|localize\b|verifique\b|apague\b|delete\b|"
        r"instale\b|feche\b|rode\b|coloca\b|crie\b|cria\b|criar\b|"
        r"pesquise\b|pesquisa\b|investigue\b|"
        r"faca\b|faz\b|fazer\b|monte\b|gere\b|produza\b|escreva\b|"
        r"quero que voce\b|preciso que voce\b|pode fazer\b|"
        r"pode comecar\b|pode escrever\b|sim pode\b|vai em frente\b|"
        r"manda ver\b|faz isso\b|faca isso\b|bora\b)", value))


class Initiative:
    def __init__(self, db):
        self.db = db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS yuna_questions (
                id INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS yuna_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

    def _get(self, key, default=""):
        row = self.db.execute("SELECT value FROM yuna_settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def _set(self, key, value):
        with self.db:
            self.db.execute(
                "INSERT INTO yuna_settings(key,value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    @property
    def enabled(self):
        return self._get("enabled", "1") == "1"

    def enable(self, value):
        self._set("enabled", "1" if value else "0")
        if not value:
            self._set("pending", "")

    def recent(self, limit=12):
        rows = self.db.execute(
            "SELECT id, question, answer FROM yuna_questions ORDER BY id DESC LIMIT ?",
            (max(1, min(int(limit), 100)),)).fetchall()
        return list(reversed(rows))

    def pending(self):
        return self._get("pending")

    def startup(self, name="Kaizen"):
        """Uma saudação por inicialização; nunca depende do Ollama nem lê a tela."""
        if not self.enabled:
            return None
        # Apelido vem do usuário/configuração local, não é deduzido pela IA.
        safe_name = re.sub(r"[^\w À-ÿ'-]", "", str(name))[:40].strip() or "Kaizen"
        question = "O que vamos fazer hoje?"
        self._set("pending", question)
        self._remember_question(question)
        return f"Olá, {safe_name}! Que bom te encontrar por aqui. {question}"

    def capture(self, answer):
        """Salva respostas às perguntas que a própria Yuna fez, sem inferir fatos extras."""
        pending = self.pending()
        if not self.enabled or not pending or looks_like_command(answer):
            return False
        text = answer.strip()
        if not text:
            return False
        # Consumir a pergunta, mesmo quando a pessoa não quis compartilhar.
        refused = text.casefold() in {"prefiro nao responder", "prefiro não responder",
                                      "não quero responder", "nao quero responder", "pular", "passo"}
        private = bool(SENSITIVE.search(text))
        with self.db:
            self.db.execute(
                "INSERT INTO yuna_settings(key,value) VALUES ('pending','') "
                "ON CONFLICT(key) DO UPDATE SET value=''")
            if not refused and not private:
                self.db.execute(
                    "INSERT INTO yuna_questions(question,answer) VALUES (?,?)",
                    (pending[:200], text[:1200]))
                self.db.execute(
                    "DELETE FROM yuna_questions WHERE id NOT IN "
                    "(SELECT id FROM yuna_questions ORDER BY id DESC LIMIT 150)")
        return not (refused or private)

    def _question_log(self):
        try:
            data = json.loads(self._get("question_log", "[]"))
            return data if isinstance(data, list) else []
        except (TypeError, ValueError):
            return []

    def _remember_question(self, question):
        previous = self._question_log()
        previous.append(question)
        self._set("question_log", json.dumps(previous[-12:], ensure_ascii=False))

    @staticmethod
    def _similar(a, b):
        from computer import normalize
        def words(text):
            return " ".join(re.findall(r"\w+", normalize(text)))
        first, second = words(a), words(b)
        return bool(first and second and (
            first == second or SequenceMatcher(None, first, second).ratio() >= 0.70
        ))

    def maybe_propose(self, statement, ask):
        """Ritmo natural: pergunta no máximo a cada 3 respostas elegíveis."""
        from computer import normalize
        if not self.enabled or self.pending() or looks_like_command(statement):
            return None
        statement = statement.strip()
        if (len(statement) < 15 or "?" in statement or SENSITIVE.search(statement)
                or any(term in normalize(statement) for term in (
                    "seu codigo", "sua estrutura", "como voce funciona",
                    "suas capacidades", "seu programa", "como voce esta", "quem e voce"))):
            return None
        count = int(self._get("eligible_turns", "0")) + 1
        self._set("eligible_turns", count)
        if count < 3:
            return None
        self._set("eligible_turns", 0)
        return self.propose(statement, ask)

    def propose(self, answer, ask):
        """Pergunta gerada localmente e somente exibida; nunca executada como ação."""
        if not self.enabled or self.pending():
            return None
        old = self._question_log() + [q for _, q, _ in self.recent(6)]
        messages = [
            {"role": "system", "content": QUESTION_PROMPT},
            {"role": "user", "content": json.dumps({
                "ultima_fala": answer[:500], "perguntas_anteriores": old
            }, ensure_ascii=False)}
        ]
        try:
            question = ask(messages).strip().strip('"“”')
        except (RuntimeError, ValueError, KeyError, TypeError):
            return None
        # Descartar perguntas genéricas, repetidas ou malformadas, não insistir.
        if (len(question) > 160 or len(question) < 10 or "\n" in question or
                question.count("?") != 1 or not question.endswith("?")
                or SENSITIVE.search(question)
                or any(self._similar(question, past) for past in old)
                or "o que voce gostaria que eu aprendesse" in question.casefold()
                or "como posso ajudar" in question.casefold()):
            return None
        self._set("pending", question)
        self._remember_question(question)
        return question

    def forget(self, ident):
        with self.db:
            return self.db.execute("DELETE FROM yuna_questions WHERE id=?", (ident,)).rowcount

    def clear(self, all_data=False):
        self._set("pending", "")
        self._set("eligible_turns", 0)
        if all_data:
            self._set("question_log", "[]")
        if all_data:
            with self.db:
                self.db.execute("DELETE FROM yuna_questions")
