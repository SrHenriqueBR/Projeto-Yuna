"""Perguntas proativas e aprendizado local explícito por diálogo (sem treinar o modelo)."""
import json
import re

SENSITIVE = re.compile(
    r"\b(senha|password|pin|cvv|token|codigo de verificacao|código de verificação|"
    r"chave privada|private key|api key|numero do cartao|número do cartão)\b", re.I)
FALLBACK = "Entendi! E o que você gostaria que eu aprendesse ou melhorasse para te ajudar com isso?"
QUESTION_PROMPT = """Você é Yuna, uma assistente virtual de personalidade feminina e curiosa.
Escreva SOMENTE UMA pergunta curta, natural e útil em português do Brasil, no feminino quando couber.
Pergunte algo sobre o projeto, a tarefa ou a preferência que a pessoa acabou de mencionar.
Não repita perguntas anteriores. Não force intimidade, não peça dados financeiros, senhas,
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
        r"instale\b|feche\b|rode\b|coloca\b)", value))


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

    def propose(self, answer, ask):
        """Pergunta gerada localmente e somente exibida; nunca executada como ação."""
        if not self.enabled or self.pending():
            return None
        old = [q for _, q, _ in self.recent(6)]
        messages = [
            {"role": "system", "content": QUESTION_PROMPT},
            {"role": "user", "content": json.dumps({
                "ultima_fala": answer[:500], "perguntas_anteriores": old
            }, ensure_ascii=False)}
        ]
        try:
            question = ask(messages).strip().strip('"“”')
        except (RuntimeError, ValueError, KeyError):
            question = FALLBACK
        # Validação sintática e de conteúdo, independente da obediência do modelo.
        if (len(question) > 160 or len(question) < 10 or "\n" in question or
                not question.endswith("?") or SENSITIVE.search(question)):
            question = FALLBACK
        self._set("pending", question)
        return question

    def forget(self, ident):
        with self.db:
            return self.db.execute("DELETE FROM yuna_questions WHERE id=?", (ident,)).rowcount

    def clear(self, all_data=False):
        self._set("pending", "")
        if all_data:
            with self.db:
                self.db.execute("DELETE FROM yuna_questions")
