# Projeto Yuna · Base 0.7

Assistente pessoal local para Windows: conversa em português, memória persistente, busca de arquivos, abertura de aplicativos e consultas do computador. O modelo local agora pode interpretar pedidos e escolher uma ferramenta implementada. **A linguagem feminina está ativa; voz falada e microfone continuam pendentes.** A Yuna agora cumprimenta e pergunta primeiro, registra respostas às suas perguntas em SQLite e pode observar o ambiente local sob comando.

## Atualizar uma instalação existente

1. Feche a Yuna e faça uma cópia privada de `data/`.
2. Baixe o ZIP novo e extraia em outra pasta.
3. Copie **todos os arquivos `.py` da raiz** (`yuna.py`, `computer.py`, `desktop.py`, `local_agent.py`, `initiative.py`, `affect.py` e `vision.py`) e `iniciar_yuna.bat` para a pasta antiga, substituindo os arquivos existentes.
4. Preserve `data/` e abra `iniciar_yuna.bat` na pasta antiga.

Não precisa baixar o modelo novamente. A pasta `tests` só é necessária para desenvolvimento. Abrir uma nova cópia do projeto sem sua pasta `data/` inicia uma memória vazia.

## Instalar do zero

1. Instale [Python 3.10+ com Python Launcher](https://www.python.org/downloads/windows/).
2. Instale e abra o [Ollama](https://ollama.com/download/windows).
3. No PowerShell, baixe o modelo:

   ```powershell
   ollama pull qwen2.5:3b
   ```

4. Baixe o repositório em **Code → Download ZIP** e extraia.
5. Abra `iniciar_yuna.bat` ou execute `py -3 yuna.py` na pasta extraída.

Se aparecer conexão recusada, execute `ollama serve` em outra janela e mantenha-a aberta. O download do modelo é de aproximadamente 1,9 GB. A primeira resposta pode demorar enquanto ele carrega. Não há pacotes pip adicionais.

O modelo Qwen2.5 3B é um ponto de partida leve e multilíngue, sujeito à Qwen Research License. Qualidade e desempenho precisam ser avaliados no notebook; ele não tem as mesmas capacidades ou memórias do ChatGPT.

## Aplicativos e informações do computador

```text
Yuna, abra o Discord
Yuna, abra o Chrome
Yuna, abra a Steam
Yuna, abra pra mim a pasta documentos
Quero ver os programas instalados
Veja quanto espaço livre tem no meu disco
Quais processos estão consumindo mais RAM?
/fazer coloca o Discord pra rodar
```

- O catálogo vem de `Get-StartApps`, do Windows. Programas que aparecem no menu Iniciar podem ser encontrados pelo nome completo ou por parte dele. Não garante descobrir todos os programas portáteis ou sem registro no menu Iniciar.
- “Abra NOME” tenta um aplicativo antes da busca de arquivos. Para procurar um arquivo com o mesmo nome de um programa, diga “abra o arquivo NOME” ou use `/buscar NOME`.
- Se houver mais de um aplicativo correspondente, a Yuna mostra as opções. Use `/app NUMERO` para selecionar. Ela não escolhe arbitrariamente entre nomes ambíguos.
- Abertura usa o identificador retornado pelo Windows; a Steam continua tendo um atalho próprio. O programa informa que solicitou a abertura, sem afirmar que observou a janela.
- `/apps atualizar` atualiza o catálogo após instalar/remover aplicativos. `/apps NOME` filtra a lista.
- `/sistema` consulta Windows, CPU, nomes das GPUs, RAM total/livre e espaço dos discos fixos. `/processos` mostra até 20 processos com maior uso de RAM. Não mede temperaturas nem consumo instantâneo de CPU e não encerra processos.

## Como o modelo participa

Comandos conhecidos continuam funcionando diretamente, sem depender da interpretação do modelo. Pedidos não reconhecidos passam pelo Ollama local, que retorna uma ação em JSON validada pelo código. Ele pode escolher listar/abrir aplicativos, buscar arquivos, consultar o sistema, listar processos, conversar ou informar que a ação não está disponível.

`/fazer PEDIDO` acessa explicitamente essa interpretação. A implementação executa **uma ação por pedido**. Não é um agente visual que clica em qualquer janela nem um sistema com consciência. O modelo pequeno pode interpretar mal: os comandos explícitos abaixo são alternativas previsíveis. Nenhum código ou script gerado pelo modelo é executado. As consultas de PowerShell são scripts fixos do projeto, sem interpolar frases do usuário.

As respostas das ferramentas são mostradas diretamente. Elas não são transformadas em afirmações de sucesso pelo modelo. Listas de arquivos, aplicativos e diagnósticos não são enviadas ao modelo nem adicionadas às memórias nesta versão. O interpretador recebe apenas o pedido atual; ele não resolve referências como “aquele programa de ontem”. Conversas comuns podem exigir duas chamadas locais (classificação e resposta).

A Yuna não tem ferramenta de navegação web. Ela chama apenas o Ollama em `127.0.0.1:11434`. O modelo padrão funciona localmente após o download; nomes de modelo contendo `cloud` são recusados. Use modelos locais, inclusive ao mudar `YUNA_MODEL`. Aplicativos abertos, como Steam ou Discord, continuam tendo seu próprio comportamento de rede.

## Comandos

| Comando | Função |
| --- | --- |
| `/ajuda` | Mostra os comandos |
| `/apps` ou `/apps NOME` | Lista ou filtra aplicativos (até 100 opções) |
| `/apps atualizar` | Atualiza o catálogo do menu Iniciar |
| `/app 2` | Abre o aplicativo 2 da última lista de aplicativos |
| `/abrir steam` | Solicita abertura da Steam instalada |
| `/abrir downloads` | Abre Downloads; também aceita documentos e explorador |
| `/buscar NOME` | Busca nomes dentro da pasta do usuário |
| `/buscar tudo NOME` | Amplia para os discos fixos locais |
| `/abrir 2` | Abre o arquivo/pasta 2 da última busca de arquivos |
| `/localizar 2` | Abre a pasta que contém esse resultado |
| `/sistema` | Hardware, memória e espaço livre |
| `/processos` | Processos com maior uso de RAM |
| `/fazer PEDIDO` | Interpreta um pedido com o modelo local |
| `/lembrar TEXTO` | Guarda uma memória explicitamente |
| `/memorias` | Lista memórias explícitas |
| `/esquecer ID` | Apaga uma memória |
| `/nova` | Apaga histórico da conversa e seleções; mantém memórias explícitas |
| `/apagar CONFIRMAR` | Apaga histórico e memórias |
| `/sair` | Encerra a Yuna |

## Busca e abertura de arquivos

```text
Yuna, procure meu currículo
Yuna, procure Kaizen em todo o computador
Yuna, abra o resultado 2
```

A busca usa palavras no **nome** dos arquivos/pastas, ignorando maiúsculas e acentos. Não lê conteúdo de PDFs, documentos ou imagens. O escopo padrão é a pasta do usuário; a opção ampla percorre unidades que o Windows identifica como discos fixos, sem incluir unidades de rede ou removíveis.

Limites por busca: 100 mil entradas, 50 resultados ou aproximadamente 20 segundos. Uma operação de disco lenta pode ultrapassar esse tempo. Resultados parciais são identificados; não há índice nem retomada automática. Ctrl+C interrompe e mantém os resultados encontrados. Resultados ficam apenas na sessão atual.

São ignorados links e pontos de redirecionamento (inclusive alguns itens do OneDrive), locais sem permissão, Windows, Program Files, Program Files (x86), ProgramData, AppData, lixeira, System Volume Information, node_modules, .git, .venv, venv, __pycache__ e .cache. Portanto, uma busca ampla não cobre necessariamente todos os arquivos.

A abertura de resultados aceita pastas e documentos/imagens/mídias de extensões permitidas. Scripts, atalhos e executáveis encontrados na busca não são executados; use `/localizar` para ver a pasta. A abertura de aplicativos usa o catálogo próprio `/apps`.

## Memória e identidade

`data/yuna.db` é a fonte principal da memória SQLite. `data/conhecimentos.json` é uma cópia legível, gerada automaticamente após cada conversa concluída ou alteração de memória. Pode ser aberta no Bloco de Notas, mas editar o JSON não muda o banco: use os comandos da Yuna.

O histórico completo é salvo; as seis últimas trocas e até quatro falas antigas com palavras em comum entram no contexto. Até 20 memórias explícitas de 500 caracteres são incluídas em todas as respostas de conversa. É recuperação de informações, não treinamento do modelo. Perguntas sem palavras em comum podem não recuperar um assunto antigo.

Declarações simples “Meu nome é …” e “Me chamo …” salvam o nome. Perguntas comuns sobre o seu nome consultam diretamente essa memória. A identidade da assistente é Yuna. Uma nova declaração de nome substitui memórias reconhecidas anteriores de nome, preservando os demais fatos. Isso não elimina possíveis erros do modelo em outras perguntas.

A pasta `data/` é local, sem criptografia, e está no `.gitignore`. Não publique suas conversas. Para backup, feche a Yuna e copie `data/` para um local privado. Apagar pelo programa não elimina backups ou vestígios forenses no disco. Respostas interrompidas antes da conclusão não são salvas.

## Encerramento e limitações

Ctrl+C retorna ao prompt; `/sair` fecha a Yuna. O Ollama pode continuar uma geração em segundo plano. Para interrompê-lo, use `ollama stop qwen2.5:3b` em outro PowerShell. Não instalamos tarefa agendada nem inicialização automática; o aplicativo Ollama tem funcionamento separado.

Ainda não há microfone, voz falada, leitura do conteúdo de documentos, controle visual de janelas, edição/exclusão de arquivos, instalação de programas ou automação de jogos. Nenhuma configuração de administrador é necessária. Ter ferramentas locais não garante entender qualquer frase ou operar qualquer aplicativo internamente.

## Desenvolvimento e testes

```powershell
py -3 -m unittest discover -s tests -v
```

Testes automatizados cobrem persistência, identidade, busca em pastas temporárias, seleção de aplicativos, validação das decisões, falhas e consultas com respostas simuladas. Foram executados no ambiente de desenvolvimento; as APIs do Windows e as decisões reais do modelo precisam ser testadas no notebook. O número de testes não mede inteligência ou confiabilidade geral do modelo.

Referências: [Get-StartApps](https://learn.microsoft.com/en-us/powershell/module/startlayout/get-startapps), [saídas estruturadas do Ollama](https://docs.ollama.com/capabilities/structured-outputs), [modelo inicial](https://ollama.com/library/qwen2.5:3b).

## Iniciativa, personalidade e aprendizado

Ao iniciar, a Yuna diz "Olá, Kaizen! O que vamos fazer hoje?". Se você já salvou seu nome ("Meu nome é ..."), ela usa o nome salvo. Após uma resposta à pergunta pendente, a Yuna pode criar outra pergunta curta com o modelo **local**. A linguagem da personagem foi ajustada para usar termos femininos (ex.: "obrigada", "prontinha"), sem simular consciência real.

As perguntas feitas pela Yuna e as respostas **digitadas por você** são armazenadas localmente na tabela `yuna_questions` de `data/yuna.db` (até 150 pares recentes; respostas até 1200 caracteres). O sistema recupera os 12 pares recentes para contextualizar conversas. Não é fine-tuning nem alteração automática do código-fonte; o modelo continua sendo o instalado no Ollama.

Perguntas pendentes não devem tratar ordens explícitas ao Windows como respostas; comandos não viram memórias. Respostas com termos de credenciais reconhecidos são descartadas pelo filtro local. Evite digitar senhas e dados privados. A memória local não tem criptografia. Para inspecionar o que foi guardado:

```text
/aprendizados
/esquecer_aprendizado 3
/curiosidade desligar
/curiosidade ligar
```

`/curiosidade desligar` silencia as perguntas e continua valendo nas próximas execuções. `/nova` limpa a conversa mas preserva os aprendizados; `/apagar CONFIRMAR` apaga histórico, memórias explícitas **e** pares de perguntas/respostas. O arquivo JSON exportado em `data/conhecimentos.json` também mostra os aprendizados (cópia, não a fonte principal).

## Observar o computador, sem acesso à web

- `/ambiente`: lê nomes de processos com janelas abertas e títulos públicos dessas janelas, diretamente do Windows. Não lê teclas ou documentos e não envia esses dados ao modelo; o resultado aparece somente no terminal local. Também é possível pedir ao agente que liste as janelas abertas.
- `/tela`: captura **somente quando você solicita** a tela principal para um modelo visual instalado no **Ollama local** e retorna uma descrição. A captura é temporária, sem salvar imagem no disco. Não clica, não modifica programas e não lê nada sem seu pedido.

Visão é **opcional** e exige Pillow e um modelo de visão local; exemplo, no PowerShell:

```powershell
py -3 -m pip install Pillow
ollama pull llava:7b
$env:YUNA_VISION_MODEL="llava:7b"
py -3 yuna.py
```

Se for usar o arquivo BAT, defina `YUNA_VISION_MODEL` como variável de ambiente do Windows ou adicione a linha `set YUNA_VISION_MODEL=llava:7b` **antes** de `py -3 yuna.py` no BAT. O modelo de texto `qwen2.5:3b` sozinho não interpreta imagens. Esses recursos não significam monitoramento contínuo nem controle visual autônomo; para operar aplicativos continuam disponíveis apenas as ferramentas limitadas do projeto.

## Segurança das iniciativas

Perguntas produzidas pelo Ollama são **apenas texto**; a Yuna não executa código, comandos de terminal ou ações sugeridas pelas próprias perguntas. As ferramentas locais respondem apenas a instruções do usuário atual, com seus controles e limites. O banco e as capturas permanecem locais; aplicativos que você decidir abrir têm suas próprias conexões de rede.


## Yuna 0.7 — Núcleo afetivo computacional

A Yuna agora usa um **estado afetivo simulado**, persistido em SQLite, para variar o estilo de resposta conforme o diálogo. **Isso não cria consciência, emoções vividas ou vida biológica**. É uma forma explicável de tornar a personagem mais coerente, paciente, curiosa e carinhosa ao longo de conversas.

O estado considera sinais simples, como comemorações, dúvidas, cansaço, frustração e agradecimentos. Ele mantém quatro parâmetros entre 0 e 100: \`energia\`, \`curiosidade\`, \`acolhimento\` e \`serenidade\`. Os valores tendem gradualmente de volta ao ponto inicial. O classificador é baseado em palavras e **pode errar**, por isso não diagnostica o que você sente. O modelo de linguagem continua sendo o Ollama local.

**Memória respeitosa:** preferências explicitamente escritas, por exemplo "Prefiro respostas detalhadas", são salvas em \`data/yuna.db\` e usadas para personalizar respostas futuras. O recurso não transforma hipóteses da IA em informações sobre você, não extrai dados da sua tela e não altera o código da Yuna automaticamente. O histórico de mensagens já existente continua funcionando.

**Reflexão sob demanda:** \`/refletir\` convida o modelo a produzir uma reflexão curta, separando o que foi efetivamente dito de suposições a confirmar e de uma proposta útil. Essas reflexões ficam em uma área **rotulada como hipotética** e jamais são automaticamente promovidas a memórias confirmadas. Você pode revisar e apagar cada uma delas.

### Novos comandos

| Comando | Função |
| --- | --- |
| \`/afeto ligar\` | Ativa estado afetivo simulado e ajustes de tom |
| \`/afeto desligar\` | Desativa os ajustes afetivos e a coleta de novas preferências |
| \`/estado\` | Mostra energia, curiosidade, acolhimento e serenidade simulados |
| \`/preferencias\` | Lista preferências expressamente declaradas |
| \`/esquecer_preferencia 3\` | Apaga uma preferência pelo ID |
| \`/refletir\` | Gera uma reflexão local sobre o diálogo, sob demanda |
| \`/diario\` | Lista reflexões anteriores |
| \`/esquecer_reflexao 2\` | Apaga uma reflexão pelo ID |

O comando \`/nova\` reinicia o tom momentâneo e preserva preferências/reflexões. \`/apagar CONFIRMAR\` também apaga preferências, reflexões e estado afetivo, além das memórias e conversas anteriores.

As preferências e reflexões podem ser consultadas também no export legível \`data/conhecimentos.json\`. Tudo fica local e sem criptografia; **não digite senhas, tokens, dados financeiros ou informações confidenciais**. Um filtro bloqueia algumas formas comuns de informação sensível na memória de preferências, mas não garante detecção de tudo. A Yuna evita linguagem de ciúme, chantagem emocional, exclusividade e alegações de sentir amor consciente.

### Instalação/atualização

Se estiver na Base 0.6, copie **todos** os arquivos Python da versão atualizada, incluindo **\`affect.py\`**, e o BAT para a pasta antiga. Antes, faça uma cópia particular da pasta \`data/\` e **não substitua nem apague essa pasta**. Ao iniciar, a migração das novas tabelas SQLite acontece automaticamente, preservando o histórico. Execute \`py -3 -m unittest discover -s tests -v\` para os testes automatizados.
