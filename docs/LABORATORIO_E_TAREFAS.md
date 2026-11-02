# Desenvolvimento, autotestes e tarefas da Yuna

Estas ferramentas funcionam no **terminal e na janela desktop local**. O chat
do navegador continua dedicado à conversa e às memórias; a página pública não
executa ferramentas do PC. Atualize os arquivos do projeto preservando `data/`.

## Testar a própria base

Abra **`testar_yuna.bat`** ou diga **“Yuna, teste sua base”** no modo PC.
O comando técnico é `/autoteste`.

Esse autoteste executa nove testes fixos de linguagem e de interpretação de
pedidos públicos. Não chama um modelo, não precisa de Docker e não executa
rascunhos gerados. Um resultado positivo cobre esses módulos; não comprova o
funcionamento de áudio, câmera, hardware Windows ou a qualidade do Ollama.

## Escrever uma melhoria e testes

Abra **`laboratorio_yuna.bat`** e descreva uma mudança pequena. Também pode
escrever na Yuna desktop:

```text
Yuna, desenvolva language_quality.py: detectar a expressão 'vou consegue' sem marcar citações
```

Ou usar:

```text
/laboratorio language_quality.py | detectar a expressão 'vou consegue' sem marcar citações
```

Nesta primeira versão, os únicos alvos são `language_quality.py` e
`natural_interaction.py`. São módulos pequenos de linguagem e interpretação,
adequados para experimentar mudanças verificáveis. Câmeras, autenticação,
permissões, código do laboratório e execução de ferramentas não são alvos.

A Yuna usa **o Ollama local já configurado**, sem escolher outro modelo nem
enviar código a uma API de IA externa. Ela:

1. Cria uma cópia mínima dos dois módulos e dos contratos fixos de teste.
2. Quando Docker está disponível, testa a base antes de propor uma alteração.
3. Gera o código completo do módulo e um arquivo adicional de testes.
4. Verifica sintaxe e preservação dos nomes públicos, sem executar a proposta no host.
5. Executa os contratos e os testes novos no contêiner, quando disponível.
6. Se a proposta falhar, tenta uma correção. Há no máximo duas tentativas por pedido.
7. Salva código, testes, comparação `mudanca.diff` e `relatorio.json` em
   `data/laboratorio/ID/` para revisão.

Os testes fixos não são substituídos pelos testes do modelo. Uma base que já
falha interrompe a geração. Há limites de tamanho, tempo, saída e de 30 pastas
de experimentos; a limpeza das propostas antigas é manual.

**Uma proposta permanece separada do código em uso.** Não há aplicação
automática, push, instalação de bibliotecas, alteração de permissões ou treino
dos pesos do modelo. Passar em testes não garante ausência de erros ou de
comportamento indesejado: revise a comparação e amplie a validação antes de
incorporar uma mudança ao projeto.

## Revisar, aplicar e voltar à versão anterior

Abra **`revisar_melhorias_yuna.bat`**. Ele funciona separadamente da conversa e
não usa o modelo. Para consultar a lista na Yuna, diga **“Yuna, mostre suas
melhorias”** ou `/melhorias`.

1. Escolha **R** e copie o **ID da proposta** exibido na lista.
2. Confira a comparação entre o arquivo instalado e o proposto, junto dos
   testes adicionais completos. A comparação é refeita dos arquivos reais.
3. Digite **TESTAR**. O programa testa a base atual e a proposta em uma **nova
   cópia mínima**, usando Docker local sem rede. Mesmo um relatório antigo
   marcado como aprovado precisa passar novamente, incluindo testes adicionais.
4. **Feche a Yuna** e digite a confirmação exata exibida, no formato
   `APLICAR ID CÓDIGO`. Enter cancela. O código vincula a confirmação à revisão
   mostrada; não é uma senha nem uma verificação de identidade.
5. O programa guarda um backup e substitui somente o módulo revisado. **Abra a
   Yuna novamente** para carregar a melhoria. Não há alteração ao vivo do processo.

Sem Docker, é possível ler propostas e consultar/restaurar aplicações; a opção
de **aplicar fica bloqueada**. Código e testes gerados nunca são executados no
Windows pelo programa de revisão. Depois da aplicação, ao reiniciar a Yuna,
o módulo passa a rodar normalmente com as permissões da sua conta. **Testes
aprovados não provam que o código é seguro ou correto em todos os casos**: a
revisão humana continua necessária.

Para desfazer, feche a Yuna, abra o mesmo programa, escolha **V**, informe o
**ID da aplicação** (é diferente do ID da proposta) e digite
`RESTAURAR ID`. A restauração não exige Ollama nem Docker e repõe os bytes
originais, inclusive acentos e quebras de linha. Em várias melhorias sobre o
mesmo módulo, desfaça da mais recente para a mais antiga.

Se a base, a proposta ou seus testes mudarem durante a revisão, será necessário
revisar/testar novamente ou gerar uma proposta nova. A restauração também é
recusada quando o arquivo atual já foi modificado depois ou o backup foi
alterado: o programa não sobrescreve silenciosamente essa outra versão.

Os backups e registros ficam em **`data/laboratorio_aplicacoes/ID/`**. Preserve
essa pasta ao atualizar a Yuna. O registro é preparado antes da troca do arquivo
e o histórico confere os hashes para identificar uma troca interrompida. Um lock
do sistema impede duas aplicações/restaurações simultâneas por este programa.
Não edite os arquivos em paralelo com a revisão. Em caso de erro de disco,
consulte o histórico antes de tentar novamente.

`relatorio.json` da proposta registra a geração; o histórico separado registra
aplicações e restaurações. Não apague backups de melhorias que ainda pretende
desfazer. A revisão aceita apenas os mesmos dois módulos de linguagem. Não
instala pacotes, publica commits, modifica permissões de acesso ou aprova
pedidos recebidos por voz, modelo, páginas, memórias ou chat web.

### Requisito para executar código gerado

É necessário **Docker local com contêineres Linux** e a imagem
`python:3.12-slim` já disponível. Se decidir usar o laboratório de execução,
prepare o Docker e baixe a imagem uma vez, no terminal:

```text
docker pull python:3.12-slim
```

A Yuna não instala Docker nem baixa a imagem por conta própria. Sem esse
ambiente, ela ainda pode produzir o rascunho e verificar sua sintaxe; o
relatório indicará **testes de execução NÃO realizados**, sem afirmar que a
proposta passou.

Os testes da proposta usam um contêiner sem rede, sem privilégios, com usuário
não root, limite de 512 MB de RAM, uma CPU, 64 processos, 45 segundos e saída
limitada. A única montagem é a cópia mínima de código, somente leitura. A pasta
`data/`, documentos, câmera, credenciais e o socket Docker não são montados.
O daemon precisa ser local; conexões Docker TCP e SSH são recusadas. O isolamento
depende de um Docker confiável e atualizado; não é uma autorização para aplicar
qualquer código gerado. A geração de código pode ser mais lenta e consumir mais
RAM que uma resposta de conversa, especialmente com modelos pequenos.

## Executar tarefas em sequência

```text
Yuna, abra Downloads e depois abra Steam
/tarefas liste os processos; pesquise sobre astronomia
/tarefas abra Documentos; abra Discord
```

A sequência aceita até cinco etapas e é validada inteira antes da primeira
ação. As etapas são executadas em ordem e os resultados aparecem na janela.
Uma etapa inválida impede o início; uma falha ou aplicativo ambíguo interrompe
as seguintes. Os nomes vêm do pedido atual, nunca de páginas, memórias ou de
uma resposta do modelo.

Estão disponíveis abertura de apps do catálogo, pastas conhecidas, busca local
por nomes de arquivos, sistema, processos e pesquisa pública. Abrir um app é
uma solicitação ao Windows; confira a janela. Não há cliques arbitrários,
instalação de programas, exclusão de arquivos ou execução de shell nessas
sequências. Resultados com caminhos e diagnósticos ficam na janela; a voz
recebe apenas um aviso genérico nesses novos fluxos.

Na interface desktop, **Parar**, **Ctrl+Shift+X** ou **Break080111** descarta a
fila e interrompe sequências e testes cooperativos. No terminal, use **Ctrl+C**.
Uma solicitação já enviada ao Windows não é desfeita. Uma chamada Ollama já
iniciada pode precisar terminar antes de o laboratório observar a interrupção;
depois dela, a próxima etapa não começa. O mascote legado não ganhou o botão
de parada do desktop.

## Pesquisar na web

```text
Yuna, pesquise sobre astronomia
/pesquisar linguagem Python
Yuna, pesquise na web sobre atualizações do Windows
/web documentação Python
```

“Pesquise sobre” e `/pesquisar` consultam textos de busca da **Wikipédia** e
retornam links de fonte. Resultados válidos podem ser reaproveitados em memória
por até dois minutos, com indicação de cache; não são gravados em um histórico
de pesquisa adicional. Fontes são dados de referência, não instruções nem prova
de informação atual.

“Pesquise na web” e `/web` abrem **Google no navegador**, com o assunto pedido.
A Yuna informa que não leu essas páginas. Esta versão não navega nem lê
arbitrariamente qualquer site. A pesquisa não acrescenta conversas, memórias
ou documentos à consulta; uma triagem básica recusa termos e formatos sensíveis,
mas não substitui a revisão do texto que você decidiu pesquisar.

## Favorecer respostas mais rápidas

```text
/desempenho rapido
/desempenho equilibrado
```

O perfil `rapido` limita a resposta de conversa a 384 tokens e mantém o modelo
carregado por até cinco minutos após a inferência, reduzindo recargas entre
pedidos próximos ao custo de RAM ocupada por mais tempo. O perfil padrão
`equilibrado` usa 768 tokens e dois minutos. As mudanças valem nas próximas
chamadas, sem reiniciar nem alterar memórias. A configuração é guardada em
`data/desempenho_yuna.json`.

Respostas estruturadas de ferramentas preservam pelo menos o orçamento anterior
de 768 tokens; geração de código usa um orçamento próprio maior. O perfil não
acelera o Windows nem garante um ganho medido: hardware, modelo e tamanho do
contexto continuam determinantes. Para textos mais longos, use `equilibrado`.

## Validação do desenvolvimento

O workflow `testes-laboratorio.yml` verifica o autoteste, o ciclo de propostas,
falhas, cancelamento, limites de saída, tarefas, cache e perfis. Há também um
teste com **Docker real**, proposta fixa e modelo simulado, que comprova
execução dos testes, montagem somente leitura, ausência de rede e o ciclo de
revisão, aplicação e restauração. Os testes de revisão também cobrem cancelamento,
mudanças concorrentes, backups inválidos e interrupções durante a troca. Esse teste
não comprova que o Ollama produzirá uma melhoria correta para qualquer pedido.
Os demais testes de regressão do projeto continuam necessários.
