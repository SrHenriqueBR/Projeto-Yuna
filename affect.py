"""Núcleo afetivo SIMULADO da Yuna.

O estado é uma régua de tom conversacional e atenção, não emoções conscientes.
Só registra preferências escritas explicitamente pelo usuário; jamais executa ações.
"""
import json
import re
import unicodedata

BASE = {"energia": 62, "curiosidade": 58, "acolhimento": 70, "serenidade": 63}
SIGNALS = {
    "alegria": (("feliz", "contente", "animado", "animada", "maravilhoso", "consegui", "deu certo"),
                {"energia": 9, "curiosidade": 3, "acolhimento": 2}),
    "dificuldade": (("triste", "sozinho", "sozinha", "chateado", "chateada", "desanimado",
                     "desanimada", "angustiado", "angustiada"),
                    {"energia": -4, "acolhimento": 12, "serenidade": 3}),
    "cansaco": (("cansado", "cansada", "exausto", "exausta", "sono", "descansar"),
                {"energia": -8, "serenidade": 5, "acolhimento": 6}),
    "frustracao": (("erro", "quebrou", "travou", "bug", "nao funciona", "não funciona",
                    "deu errado"),
                   {"energia": -2, "serenidade": 6, "acolhimento": 5}),
    "descoberta": (("aprender", "estudar", "criar", "projeto", "ideia", "descobri", "programar"),
                   {"curiosidade": 10, "energia": 3}),
    "carinho": (("obrigado", "obrigada", "carinho", "gosto de voce", "gosto de você",
                 "te adoro", "te amo"),
                {"acolhimento": 8, "serenidade": 2}),
}
# O filtro reduz riscos, mas não substitui cautela do usuário com dados privados.
SENSITIVE = re.compile(
    r"\b(senha|password|token|cvv|pin|cpf|rg|chave pix|código de acesso|codigo de acesso|"
    r"api key|secret key|número do cartão|numero do cartao|diagnóstico|diagnostico|"
    r"remédio|remedio|doença|doenca)\b", re.I)
PREF = re.compile(
    r"^(?:eu\s+)?(prefiro|gosto de|adoro|não gosto de|nao gosto de|"
    r"quero que você|quero que voce)\s+(.{2,180})[.!]?$", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
DIGITS = re.compile(r"\d[\d .-]{9,}\d")


def normalize(text):
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in normalized if not unicodedata.combining(c))


def contains_phrase(text, phrase):
    """Fronteiras de palavras impedem falsos positivos em outras palavras."""
    return bool(re.search(r"(?<!\w)" + re.escape(normalize(phrase)) + r"(?!\w)", normalize(text)))


def safe_preference(text):
    from initiative import looks_like_command
    text = text.strip()
    if (not text or len(text) > 220 or "\n" in text or looks_like_command(text)
            or SENSITIVE.search(text) or EMAIL.search(text) or DIGITS.search(text)):
        return None
    match = PREF.fullmatch(text)
    if match is None:
        return None
    # Armazena a frase do usuário, sem acrescentar inferências inventadas.
    return text


class AffectiveCore:
    """Persistência leve para mudanças de estilo; nenhuma pretensão de consciência."""
    def __init__(self, db):
        self.db = db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS yuna_affect_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS yuna_preferences (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS yuna_reflections (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def _get(self, key, default=None):
        row = self.db.execute(
            "SELECT value FROM yuna_affect_state WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def _set(self, key, value):
        with self.db:
            self.db.execute(
                "INSERT INTO yuna_affect_state(key,value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    @property
    def enabled(self):
        return self._get("enabled", "1") == "1"

    def enable(self, flag):
        self._set("enabled", "1" if flag else "0")

    def values(self):
        try:
            raw = json.loads(self._get("values", "{}"))
        except (ValueError, TypeError):
            raw = {}
        return {k: max(0, min(100, int(raw.get(k, default))))
                if isinstance(raw.get(k, default), (int, float)) else default
                for k, default in BASE.items()}

    def preferences(self, limit=20):
        return self.db.execute(
            "SELECT id,content FROM yuna_preferences ORDER BY id DESC LIMIT ?",
            (max(1, min(int(limit), 40)),)).fetchall()

    def forget_preference(self, ident):
        with self.db:
            return self.db.execute(
                "DELETE FROM yuna_preferences WHERE id=?", (ident,)).rowcount

    def observe(self, text):
        """Uma conversa altera apenas o estado simulado, nunca as permissões."""
        from initiative import looks_like_command
        if not self.enabled or looks_like_command(text) or SENSITIVE.search(text):
            return None
        norm = normalize(text[:1000])
        state = self.values()
        # Retorno lento ao equilíbrio: humor não fica permanentemente definido.
        for key, base in BASE.items():
            state[key] += (1 if state[key] < base else -1 if state[key] > base else 0)
        signal = "neutro"
        for label, (keywords, deltas) in SIGNALS.items():
            if any(contains_phrase(norm, phrase) for phrase in keywords):
                signal = label
                for key, delta in deltas.items():
                    state[key] = max(0, min(100, state[key] + delta))
                break
        with self.db:
            self.db.execute(
                "INSERT INTO yuna_affect_state(key,value) VALUES ('values',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(state, ensure_ascii=False),))
            self.db.execute(
                "INSERT INTO yuna_affect_state(key,value) VALUES ('signal',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (signal,))
            self.db.execute(
                "INSERT INTO yuna_affect_state(key,value) VALUES ('turns',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(int(self._get("turns", "0")) + 1),))
            preference = safe_preference(text)
            if preference:
                exists = self.db.execute(
                    "SELECT id FROM yuna_preferences WHERE content=? COLLATE NOCASE",
                    (preference,)).fetchone()
                if not exists:
                    self.db.execute(
                        "INSERT INTO yuna_preferences(content) VALUES (?)", (preference,))
                    self.db.execute(
                        "DELETE FROM yuna_preferences WHERE id NOT IN "
                        "(SELECT id FROM yuna_preferences ORDER BY id DESC LIMIT 40)")
        return signal

    def state_summary(self):
        state = self.values()
        signal = self._get("signal", "neutro")
        return {"estado_simulado": state, "ultimo_sinal": signal,
                "interacoes": int(self._get("turns", "0")),
                "preferencias_ditas_pelo_usuario": [s for _, s in self.preferences(10)]}

    def style_instructions(self):
        if not self.enabled:
            return ("Modo afetivo desligado: converse de modo gentil e objetivo. "
                    "Não use nem atualize estados afetivos simulados.")
        state = self.state_summary()
        signal = state["ultimo_sinal"]
        suggestions = {
            "alegria": "Acompanhe a notícia positiva de modo natural, sem exagerar.",
            "dificuldade": "Responda com delicadeza e escuta; não presuma causa ou diagnóstico.",
            "cansaco": "Seja breve, tranquila e respeite pausas.",
            "frustracao": "Seja paciente, prática e ajude a resolver uma coisa por vez.",
            "descoberta": "Demonstre curiosidade e ofereça próximos passos concretos.",
            "carinho": "Receba o carinho com gratidão, sem fingir dependência afetiva.",
        }
        return (
            "O estado abaixo é um controle numérico de TOM, não uma sensação vivida. "
            "Não diga que tem coração biológico, consciência, medo de ser desligada "
            "ou necessidade emocional do usuário. Não faça cobranças, ciúme, romance "
            "exclusivo nem diga que é mais importante que pessoas reais. Pode falar "
            "com carinho, humor e delicadeza, como uma personagem assistente. "
            "Quando perguntarem sobre seus sentimentos, explique com naturalidade "
            "que são respostas e estados computacionais simulados. "
            + suggestions.get(signal, "Seja cordial, útil e atenta ao contexto.") + "\n"
            + json.dumps(state, ensure_ascii=False)
        )

    def status_text(self):
        if not self.enabled:
            return "Afeto simulado desativado. Use /afeto ligar quando quiser."
        d = self.state_summary()
        values = " | ".join(f"{key}: {value}/100" for key, value in d["estado_simulado"].items())
        return (f"Estado afetivo simulado (não biológico): {values}.\n"
                f"Contexto: {d['ultimo_sinal']} | conversas observadas: {d['interacoes']}.\n"
                "Esses números influenciam o estilo das respostas, não representam consciência.")

    def save_reflection(self, text):
        if not isinstance(text, str) or not text.strip():
            return
        with self.db:
            self.db.execute(
                "INSERT INTO yuna_reflections(text) VALUES (?)", (text.strip()[:1500],))
            self.db.execute(
                "DELETE FROM yuna_reflections WHERE id NOT IN "
                "(SELECT id FROM yuna_reflections ORDER BY id DESC LIMIT 30)")

    def reflections(self, limit=5):
        return self.db.execute(
            "SELECT id,text FROM yuna_reflections ORDER BY id DESC LIMIT ?",
            (max(1, min(int(limit), 30)),)).fetchall()

    def forget_reflection(self, ident):
        with self.db:
            return self.db.execute(
                "DELETE FROM yuna_reflections WHERE id=?", (ident,)).rowcount

    def clear(self, all_data=False):
        if all_data:
            with self.db:
                self.db.execute("DELETE FROM yuna_preferences")
                self.db.execute("DELETE FROM yuna_affect_state")
                self.db.execute("DELETE FROM yuna_reflections")
        else:
            self._set("signal", "neutro")
            self._set("values", json.dumps(BASE))
