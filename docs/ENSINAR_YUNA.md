# Ensinar a Yuna — 0.56.0

A Yuna agora pode consultar um caderno de exemplos que você revisou. Isso é
personalização por recuperação de exemplos: **não é treinamento dos pesos do
Qwen**, não aumenta automaticamente seu QI e não transforma tudo que ela diz
em conhecimento. O recurso é local e funciona com o modelo já selecionado.

## Ensinar pela janela

1. Abra **••• → Central da Yuna → Minha Yuna → Ensinar a Yuna**.
2. Na aba **Ensinar**, escreva uma pergunta ou situação e a resposta correta.
   **Usar a última resposta de conversa** preenche um rascunho; revise antes de salvar.
3. Clique em **Salvar lição revisada**. A mesma pergunta, ignorando acentos,
   maiúsculas e pontuação, atualiza a lição e aumenta seu número de revisão.
4. Na aba **Testar**, digite a pergunta e consulte os exemplos relacionados.
5. Converse normalmente com a Yuna. Até três exemplos relevantes podem entrar
   no contexto; uma correspondência exata usa só aquela lição.

Exemplo: pergunta **Como gosto de estudar Python?**, resposta **Com um exemplo
pequeno, explicação linha por linha e um exercício no final.**

Na aba **Minhas lições**, selecione uma lição para editar ou apagar.
O caderno aceita até 200 lições, perguntas de 3–600 caracteres e respostas
de 2–6000 caracteres. Ele não salva exemplos com alguns padrões comuns de
credenciais; revise sempre o conteúdo, pois essa detecção não é completa.

## Ensinar pelo chat

No desktop, terminal, mascote e chat servido no próprio PC:

```text
/ensinar Como gosto de estudar Python? => Com um exemplo pequeno e um exercício no final.
/licoes
```

Logo depois de uma resposta de conversa gerada pelo modelo:

```text
/corrigir Meu caderno é verde, não azul.
```

Também funciona **Yuna, corrigindo: Meu caderno é verde, não azul.**
Essa correção se refere à última pergunta do chat. Confira a pergunta na
janela de ensino se houver dúvida. Resultados de ações, pesquisas diretas,
documentos ou respostas canceladas não são candidatos a essa correção.
Conversas de versões anteriores não recebem candidatos retroativamente;
você pode copiá-las e ensinar um exemplo explicitamente.

`/ensino` mostra ajuda, `/esquecer_licao ID` apaga a lição pelo número e
`/testar_ensino` executa o teste local dos guias. Os comandos de gestão do
caderno não viram novas mensagens no banco. Lições salvas ficam na tabela
`teaching_lessons` de `data/yuna.db` e no retrato `conhecimentos.json`.

## O que muda nas respostas

A seleção compara palavras de conteúdo e exige relevância mínima. Ela não
usa um embedding adicional, não faz downloads e pode deixar de encontrar
sinônimos; use **Testar** para verificar uma formulação diferente. Uma lição
específica não vira uma regra geral para todos os assuntos.

A resposta antiga à pergunta corrigida continua no histórico para consulta,
mas deixa de entrar no contexto como exemplo. Lições são dados do usuário,
não fatos externos verificados nem autorização para ações. Texto como
“abra Steam” dentro de uma lição não passa pelo roteador de comandos.

Os 12 guias públicos em `ensino/curriculo.json` explicam microfone, fala,
modelos, memória, ensino, código Python, erros, documentos, pesquisa,
aplicativos, cancelamento e contexto. São referências da versão do projeto,
separadas das lições pessoais. Uma lição pessoal com a mesma pergunta tem
prioridade; o modelo ainda pode errar ao interpretá-la.

## Testes e limites

**Avaliar os guias do projeto** usa 36 casos em `ensino/avaliacao.json`:
24 perguntas relacionadas e 12 assuntos que não devem recuperar um guia.
Os casos são diferentes das perguntas e variantes dos exemplos. O relatório
mostra acertos e falhas reais da recuperação, sem executar o Qwen.

Os testes automatizados verificam persistência, migração, correção,
isolamento de ferramentas, cancelamento, seleção, exportação e uso no Qt.
Respostas do modelo são simuladas nos testes de integração. Não há nota
de inteligência, benchmark do notebook ou treinamento de pesos concluído.
Para avaliar a conversa real, teste perguntas relacionadas e diferentes
no seu Ollama, confira a resposta e corrija somente o que você revisou.

## Exportar e preservar

Selecione lições em **Minhas lições → Exportar selecionadas** (Ctrl permite
selecionar várias). O JSONL contém somente esses pares de pergunta/resposta
e seus IDs/revisões; não inclui automaticamente histórico, memórias,
documentos ou lições do guia. A exportação é local, não faz upload e não
inicia fine-tuning. Adaptar um conjunto de exemplos a uma ferramenta de
treinamento de pesos exige uma etapa separada, avaliação e hardware adequado.

Fechar ou atualizar a Yuna preserva o SQLite. `/nova` no terminal limpa o
histórico e preserva lições; `/apagar CONFIRMAR` também apaga as lições
pessoais. Exportações manuais e backups continuam onde foram salvos.
Faça backup privado de `data` com a Yuna fechada. A escola pública em
`aprendizado/` não recebe esse caderno nem as conversas do computador.

Avisos de gestão do caderno usam uma fala genérica. Nas conversas normais,
uma voz online que você tenha ativado continua podendo receber o texto
falado; use a voz Windows/offline para manter também a síntese local.
