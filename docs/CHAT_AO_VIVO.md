# Chat ao vivo — Yuna 0.57.0

A Yuna mostra uma prévia enquanto o Ollama escreve a resposta de conversa,
na janela completa e no chat compacto. O painel informa que a prévia ainda
não foi salva. Depois da conclusão e eventual revisão do português, a
resposta final entra no histórico e pode ser falada normalmente.

## Conversar e parar

- Faça uma pergunta ou peça código. A prévia aparece quando chegam os
  primeiros trechos de resposta do modelo. Antes disso, o estado informa
  conexão, espera pelo modelo ou preparação da resposta.
- **Parar** ou **Ctrl+Shift+X** interrompe a voz, descarta a fila e solicita
  o encerramento da conexão de inferência local. Isso também vale para
  a análise de documentos e as inferências das ferramentas do roteador desktop.
- A prévia cancelada desaparece. Eventos atrasados de texto, resposta,
  erro ou estado de uma tarefa anterior são ignorados mesmo se já estiverem
  na fila da interface. Uma mensagem nova usa uma geração nova da fila.
- Respostas incompletas por queda da conexão não são gravadas como conversa
  concluída nem se tornam candidatas automáticas a correção no caderno.

A conexão inicial e o envio do pedido têm prazo de até 5 segundos; durante
a leitura, o cancelamento é verificado mesmo se o modelo ficar em silêncio.
O app fecha a sua conexão, mas não mata
o processo Ollama e não garante liberação imediata da RAM/VRAM. Ações já
concluídas no Windows não são desfeitas. Consultas web, downloads e outras
operações externas mantêm seus próprios prazos e pontos de cancelamento.

Só o texto público `message.content` da API vira prévia. Campos de raciocínio
interno e chamadas de ferramentas não são exibidos nem executados. A saída
estruturada usada por ferramentas e a análise de documentos não exibem
rascunhos no painel; seus resultados completos continuam nas interfaces
correspondentes. O chat servido no navegador e a mascote antiga mantêm o
fluxo de resposta completa nesta versão.

Mostrar trechos antes do fim melhora a percepção da espera, mas não aumenta
a velocidade de geração do modelo nem treina os pesos do Qwen.

## Ler, copiar e ensinar

As respostas na janela completa e no compacto podem mostrar listas,
negrito, tabelas e código formatado. As mensagens do usuário continuam como
texto literal. O conteúdo não carrega imagens ou arquivos externos; HTML
embutido fica desativado. Links HTTP/HTTPS compatíveis abrem no navegador
somente após clique. Caminhos locais, esquemas de execução, endereços locais
literais e portas fora de 80/443 são rejeitados pelo controle de links.

Na janela completa:

- **Copiar resposta** copia o texto original, incluindo Markdown.
- **Copiar código** copia só o bloco escolhido, mantendo quebras de linha e
  indentação. Se houver vários blocos, escolha pelo número/linguagem.
  Cercas de código sem fechamento não são apresentadas como bloco completo;
  o texto integral ainda pode ser copiado pelo botão da resposta.
- **Corrigir e ensinar** preenche um rascunho no caderno com aquela pergunta
  e resposta. Revise e salve a lição. Clicar não ensina automaticamente.

No compacto, **Copiar** pega a última resposta completa, mesmo se houver
uma nova prévia em andamento. Abra a janela completa pela seta para escolher
blocos de código e ensinar. Copiar nunca executa o conteúdo.

O chat preserva a posição quando você está lendo mensagens anteriores.
A barra lateral da janela completa agora rola, para não sobrepor o retrato,
os botões e a biblioteca em telas com pouca altura. O fundo do histórico
segue o tema escuro. Respostas muito grandes têm prévia limitada a 96 mil
caracteres; o botão de cópia usa o original. A geração também tem limites
de tamanho e tempo e informa quando um pedido precisa ser dividido.

## Validação e atualização

Os testes novos verificam NDJSON, UTF-8, cancelamento durante leitura HTTP
bloqueada (inclusive com servidor local real), queda de conexão, limite de
duração, ausência de gravação parcial, bloqueio de ações após cancelamento,
cópia fiel de código, conteúdo sem recursos externos, rascunho de ensino e
rejeição de eventos antigos na fila Qt.

Os testes de conteúdo do modelo usam respostas controladas; não medem a
qualidade do Qwen nem o desempenho do notebook. A atualização preserva a
memória e o caderno existentes. Feche a Yuna antes de instalar; mantenha seu
backup privado de `data`, como nas atualizações anteriores.

Referências de implementação: [API de chat do Ollama](https://docs.ollama.com/api/chat)
e [Markdown no Qt](https://doc.qt.io/qt-6/qtextdocument.html#setMarkdown).
