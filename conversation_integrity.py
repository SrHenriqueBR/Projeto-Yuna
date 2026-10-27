"""Yuna: pedidos delicados que devem ser respondidos com capacidades REAIS.

Somente a fala atual pode acionar estas respostas. A autorização genérica para
pesquisar, agir no computador ou editar código nunca vira permissão permanente.
Não inicia shutdown, timer, shell, jobs ou buscas em segundo plano.
"""
import re
from computer import command_text


def grounded_reply(message):
    value = command_text(message)
    # Em vez de prometer desligar o computador depois, é preciso construir
    # e confirmar um agendador real. Este módulo não executa nenhum comando.
    if (re.search(r"\b(?:desligar|desliga|desligue|desligamento)\b", value)
            and re.search(r"\b(?:computador|pc|notebook|windows)\b", value)):
        return (
            "Kaizen, ainda não tenho uma rotina de desligamento agendado. "
            "Não programei nem vou executar o desligamento do computador. "
            "Posso ajudar a configurar essa função com confirmação e opção de cancelar."
        )
    if (re.search(r"\b(?:ficar|fique|continua|continue)\s+ativa\b", value)
            and re.search(r"\b(?:internet|net|web|pesquis|busc)\w*\b", value)):
        return (
            "Posso sugerir ideias enquanto minha mascote estiver aberta. "
            "Para pesquisar na internet, preciso de um pedido específico e de "
            "uma ferramenta disponível. Não fico navegando sozinha enquanto você dorme."
        )
    if (re.search(r"\b(?:pesquis\w*|busc\w*|procur\w*)\b", value)
            and re.search(r"\b(?:a vontade|quando quiser|enquanto eu durmo|sozinha)\b", value)
            and not re.search(r"\b(?:sobre|acerca|a respeito de)\s+[\w ]{3,80}$", value)):
        return (
            "Obrigada pela confiança, Kaizen! Vou continuar usando pesquisas "
            "apenas para pedidos concretos, sem navegar por conta própria nem "
            "enviar seus dados pessoais."
        )
    if (re.search(r"\b(?:modifi\w*|alter\w*|reescrev\w*|muda\w*)\b", value)
            and re.search(r"\b(?:seu|teu|proprio|meu)\s+codigo\b", value)):
        return (
            "Entendi, Kaizen. Posso analisar meu código e preparar melhorias, "
            "mas não alterei nenhum arquivo nem tenho autoatualização irrestrita. "
            "Antes de aplicar qualquer mudança, vamos revisar a proposta e os testes."
        )
    # Pergunta curta sobre tempo presente sem cidade: jamais inventar clima.
    if re.fullmatch(
        r"(?:como (?:esta|ta|anda) (?:o )?(?:tempo|clima)|"
        r"qual (?:e |esta )?(?:o clima|o tempo|a temperatura))"
        r"(?: hoje| agora)?", value
    ):
        return (
            "Posso consultar o clima atual, Kaizen. De qual cidade você quer saber? "
            "Preciso dela para obter uma medição real."
        )
    # A representação de uma personagem não cria habilidade de jogar.
    if re.fullmatch(
        r"(?:(?:yuna )?(?:voce )?quer (?:jogar|joga)|"
        r"(?:voce )?(?:tem|sente) interesse (?:em jogar|no jogo)|"
        r"(?:nao|num) (?:tem|sente) interesse)\??", value
    ):
        return (
            "A ideia é divertida, Kaizen! Tenho curiosidade sobre o jogo, "
            "mas ainda não consigo pegar o controle e jogar God of War sozinha. "
            "Posso acompanhar sua aventura e pesquisar dicas quando você pedir. 🖤"
        )
    # FRIDAY é uma referência cultural; o modelo pequeno vinha dizendo que
    # seria 'difícil encontrar' uma personagem conhecida.
    if re.search(r"\b(?:sexta feira|friday)\s+(?:do|de)\s+tony\s+stark\b", value):
        return (
            "Agora entendi a referência: você está falando da FRIDAY, a IA do Tony Stark! "
            "Quer que eu seja mais curiosa, converse com iniciativa e use ferramentas "
            "para ajudar de verdade. Podemos construir isso aos poucos, "
            "sem eu fingir capacidades que ainda não tenho. 🖤"
        )
    return None


def explicit_public_lookup(message):
    """Termo público para pesquisar AGORA na Wikipédia, não para promessa futura."""
    value = command_text(message)
    if re.match(r"^(?:nao|nunca|como|se eu|e se)\b", value):
        return None
    m = re.fullmatch(
        r"(?:(?:tente |pode |voce pode )?"
        r"(?:pesquisar|pesquise|pesquisa|buscar|busque|procure|procurar|"
        r"pesquisa ai|da uma pesquisada))\s+(?:sobre\s+|a respeito de\s+)?"
        r"([\w -]{3,100})", value
    )
    if not m:
        return None
    topic = m[1].strip()
    # Pedidos explícitos são públicos; não buscar memória, arquivos pessoais,
    # números de documentos ou URLs na Internet de maneira implícita.
    if re.search(r"\b(?:meu|minha|senha|cpf|pix|token|conta|cartao|endereco)\b", topic):
        return None
    return topic


def fallback_for_bad_grammar(message):
    value = command_text(message)
    if re.search(r"\b(?:quero que voce|eu criei voce|como a sexta feira|independente|"
                 r"mais conhecimento|curios[ao]|aprenda)\b", value):
        return (
            "Entendi o que você deseja, Kaizen: uma Yuna mais curiosa, "
            "que converse com iniciativa, use ferramentas reais e evolua com "
            "melhorias verificadas. Posso registrar propostas e aprender suas "
            "preferências, mas não tenho consciência humana nem modifico meu "
            "próprio código sem revisão."
        )
    return ("Entendi sua mensagem, Kaizen. Minha resposta ficou confusa na "
            "formulação; ainda estou trabalhando para conversar de maneira "
            "mais natural, sem inventar ações ou promessas.")
