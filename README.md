# Projeto Yuna · Base 0.11

Assistente pessoal local para Windows: conversa em português, memória persistente, busca de arquivos, abertura de aplicativos e consultas do computador. O modelo local agora pode interpretar pedidos e escolher uma ferramenta implementada. **A Yuna agora tem uma mascote flutuante 2D com voz feminina opcional. O microfone ainda não está integrado.** A Yuna agora cumprimenta e pergunta primeiro, registra respostas às suas perguntas em SQLite e pode observar o ambiente local sob comando.

## Atualizar uma instalação existente

1. Feche a Yuna e faça uma cópia privada de `data/`.
2. Baixe o ZIP novo e extraia em outra pasta.
3. Copie **todos os arquivos `.py` da raiz** (`yuna.py`, `computer.py`, `desktop.py`, `local_agent.py`, `initiative.py`, `affect.py`, `self_model.py`, `vision.py`, `voice.py`, `diary.py` e `yuna_overlay.py`) e `iniciar_yuna.bat` para a pasta antiga, substituindo os arquivos existentes.
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

Se aparecer conexão recusada, execute `ollama serve` em outra janela e mantenha-a aberta. O download do modelo é de aproximadamente 1,9 GB. A primeira resposta pode demorar enquanto ele carrega. A versão pelo terminal não requer pacotes pip adicionais; a mascote opcional precisa do PySide6.

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

O estado considera sinais simples, como comemorações, dúvidas, cansaço, frustração e agradecimentos. Ele mantém quatro parâmetros entre 0 e 100: `energia`, `curiosidade`, `acolhimento` e `serenidade`. Os valores tendem gradualmente de volta ao ponto inicial. O classificador é baseado em palavras e **pode errar**, por isso não diagnostica o que você sente. O modelo de linguagem continua sendo o Ollama local.

**Memória respeitosa:** preferências explicitamente escritas, por exemplo "Prefiro respostas detalhadas", são salvas em `data/yuna.db` e usadas para personalizar respostas futuras. O recurso não transforma hipóteses da IA em informações sobre você, não extrai dados da sua tela e não altera o código da Yuna automaticamente. O histórico de mensagens já existente continua funcionando.

**Reflexão sob demanda:** `/refletir` convida o modelo a produzir uma reflexão curta, separando o que foi efetivamente dito de suposições a confirmar e de uma proposta útil. Essas reflexões ficam em uma área **rotulada como hipotética** e jamais são automaticamente promovidas a memórias confirmadas. Você pode revisar e apagar cada uma delas.

### Novos comandos

| Comando | Função |
| --- | --- |
| `/afeto ligar` | Ativa estado afetivo simulado e ajustes de tom |
| `/afeto desligar` | Desativa os ajustes afetivos e a coleta de novas preferências |
| `/estado` | Mostra energia, curiosidade, acolhimento e serenidade simulados |
| `/preferencias` | Lista preferências expressamente declaradas |
| `/esquecer_preferencia 3` | Apaga uma preferência pelo ID |
| `/refletir` | Gera uma reflexão local sobre o diálogo, sob demanda |
| `/diario` | Lista reflexões anteriores |
| `/esquecer_reflexao 2` | Apaga uma reflexão pelo ID |

O comando `/nova` reinicia o tom momentâneo e preserva preferências/reflexões. `/apagar CONFIRMAR` também apaga preferências, reflexões e estado afetivo, além das memórias e conversas anteriores.

As preferências e reflexões podem ser consultadas também no export legível `data/conhecimentos.json`. Tudo fica local e sem criptografia; **não digite senhas, tokens, dados financeiros ou informações confidenciais**. Um filtro bloqueia algumas formas comuns de informação sensível na memória de preferências, mas não garante detecção de tudo. A Yuna evita linguagem de ciúme, chantagem emocional, exclusividade e alegações de sentir amor consciente.

### Instalação/atualização

Se estiver na Base 0.6, copie **todos** os arquivos Python da versão atualizada, incluindo **`affect.py`**, e o BAT para a pasta antiga. Antes, faça uma cópia particular da pasta `data/` e **não substitua nem apague essa pasta**. Ao iniciar, a migração das novas tabelas SQLite acontece automaticamente, preservando o histórico. Execute `py -3 -m unittest discover -s tests -v` para os testes automatizados.


## Yuna 0.8 — autoimagem, planejamento e iniciativa controlada

A Yuna agora sabe **explicar sua arquitetura documentada** e responder diretamente "como está seu código?" sem alegar que não pode conversar sobre seus próprios módulos. Isso NÃO quer dizer que o modelo abriu, leu ou alterou os arquivos de código. A descrição é um inventário do que foi implementado, atualizado pelos desenvolvedores.

- **/sobre**: versão, modelo de texto, memória, planos registrados e capacidades e limites reais.
- **/pensar TEMA**: solicita ao Ollama uma **síntese de planejamento em JSON validado**, com observação, próximo passo sugerido e dúvida. Salva até 30 notas em SQLite. Nenhuma dessas notas é executada como comando.
- **/pensamentos**: lista as notas auditáveis. **/esquecer_pensamento ID** apaga uma.
- **/autonomia ligar|desligar**: controla a geração de uma nota de planejamento a cada seis turnos elegíveis, **somente quando a Yuna estiver aberta**. As notas automáticas não controlam o Windows, não enviam dados à web e não mudam o código.
- Perguntas automáticas com intervalo de pelo menos três contribuições elegíveis, sem interromper perguntas dirigidas à assistente e com filtro de similaridade para evitar repetições.
- Respostas no modelo têm contexto de ideias anteriores rotuladas como **sugestões e hipóteses**, não fatos verificados.
- O modelo-base `qwen2.5:3b` pode cometer erros e retornar uma estrutura inválida: a aplicação rejeita o planejamento, sem executar qualquer ação.

**Importante:** isto aproxima a Yuna de um agente capaz de planejar e se autoavaliar, mas não cria consciência demonstrada, sentimentos humanos, autonomia irrestrita ou raciocínio fora do processo quando ela está fechada. O planejamento periódico consome uma consulta Ollama a cada seis interações elegíveis. Para evitar consumo extra, use `/autonomia desligar`.

### Atualizando da 0.7

Feche a Yuna, guarde uma cópia da pasta **`data/`**, copie **todos os `.py` da raiz** da versão 0.8 (incluindo `self_model.py`) e `iniciar_yuna.bat` para a instalação antiga. Preserve sua pasta `data/`; a Yuna acrescenta automaticamente a tabela das notas sem apagar a memória atual. Execute `py -3 -m unittest discover -s tests -v` para testar.


## Yuna 0.9 — Escuridão flutuante e voz jovem/atrevida

Este é um **modo gráfico opcional**. O terminal tradicional em `iniciar_yuna.bat` continua funcionando sem PySide6. A mascote usa o mesmo `data/yuna.db`, mas **não abra terminal e mascote simultaneamente na mesma instalação** para evitar inconsistências ou conflitos no banco.

### Instalação da mascote no Windows

1. Feche a Yuna antiga. **Copie sua pasta `data/` para backup e não a substitua.**
2. Baixe o ZIP mais recente do GitHub. Copie **todos os arquivos Python** e os dois arquivos BAT para sua pasta antiga.
3. Instale a interface pelo PowerShell (uma única vez):

   ```powershell
   py -3 -m pip install -r requirements-mascote.txt
   ```

4. Coloque os sprites `yuna_idle.png`, `yuna_wave.png`, `yuna_happy.png`, `yuna_thinking.png`, `yuna_speaking.png` e `yuna_sleepy.png` na pasta `assets/` da Yuna. Se não tiver sprites, a janela funciona com um símbolo visual temporário, sem personagem.
5. Deixe o Ollama aberto e inicie `iniciar_yuna_mascote.bat` (ou `py -3 yuna_overlay.py`).

A Escuridão aparece como uma janela **sem borda, flutuante e arrastável**; movimenta-se alternando poses, mostra balão de texto, permite digitar e usa a conversa e memória que você já tinha.

### Como funciona a voz

**Padrão — voz feminina local (Windows):** usa `System.Speech`, sem enviar o texto pela internet. O Windows precisa ter uma voz feminina **pt-BR** instalada. As vozes instaladas variam de máquina para máquina; se não houver uma, a Yuna continua funcionando em texto e informa o erro.

**Opcional — voz mais jovem pelo Edge TTS:** toque no botão **Voz: Offline**, confirme o aviso de privacidade e instale `edge-tts`:

```powershell
py -3 -m pip install edge-tts
```

A síntese utiliza `pt-BR-FranciscaNeural`, velocidade `+13%` e altura `+8Hz`, com leve estilo adolescente/atrevido **na fala escrita**, sem imitar pessoa real. Os parâmetros podem ser ajustados em `voice.py`. O Edge TTS usa um serviço remoto, não requer chave API por padrão, e **envia o texto falado para fora do computador**; sua disponibilidade pode mudar sem aviso. Não o utilize para senhas, conversas confidenciais ou assuntos privados. O áudio gerado é um MP3 temporário e apagado após a reprodução.

O botão alterna entre **Offline → Jovem (online) → Muda**. O modo online exige consentimento em cada sessão, mesmo se a variável `YUNA_VOICE_ENGINE=edge` estiver configurada.

A fala offline depende da voz pt-BR instalada; por isso não é possível garantir uma timbragem adolescente idêntica em todas as máquinas. A animação facial nesta versão alterna sprites conforme o estado **falando, pensando ou descansando** — ainda não é sincronização labial por fonema ou Live2D. Não há microfone, câmera, gravação contínua nem controle do computador sem pedido explícito.

### Como atualizar a versão com segurança

- Atualize todos os arquivos `.py` (especialmente `voice.py` e `yuna_overlay.py`), o launcher `iniciar_yuna_mascote.bat` e `requirements-mascote.txt`.
- Guarde os seis PNGs em `assets/` e **preserve `data/`**.
- Se não quiser a mascote, pode continuar usando `iniciar_yuna.bat` normalmente.
- Para testar o código sem abrir a interface: `py -3 -m unittest discover -s tests -v`. O áudio final e a interface Windows devem ser verificados no seu notebook.


### Se a voz Jovem mostrar `'lazy_import' object is not callable`

A interface está funcionando, mas a biblioteca de síntese falhou no Python 3.15. A correção atual tenta importar diretamente a classe de voz; se a incompatibilidade persistir, **usa automaticamente o Python 3.13 somente para gerar o áudio**, mantendo a janela da Yuna no Python atual.

1. Instale o **Python 3.13 (64 bits)** pelo instalador oficial [Python para Windows](https://www.python.org/downloads/windows/), selecionando o Python Launcher. Não remova o Python 3.15 nem apague a pasta `data/`.
2. No PowerShell, instale apenas a voz para o interpretador 3.13:

   ```powershell
   py -3.13 -m pip install edge-tts
   ```

3. Reabra `iniciar_yuna_mascote.bat` e ative a voz Jovem novamente. A Yuna detecta o erro de importação e tenta reproduzir a fala usando o Python 3.13, sem precisar reinstalar PySide6.

Para conferir a geração sem abrir a Yuna:

```powershell
py -3.13 -m edge_tts --voice pt-BR-FranciscaNeural --text "Oi, Kaizen!" --write-media teste_yuna.mp3
```

Abra `teste_yuna.mp3` no Windows. Se o áudio funcionar, a geração está correta; se a mascote ainda estiver muda, verifique o volume/dispositivo de saída e a reprodução Qt. Mantenha o texto privado fora da voz online.



## Voz Amanda Kelly (ElevenLabs) — opção adicional

A Yuna oferece a voz **Amanda Kelly — Sweet, Warm and Clear** da ElevenLabs, com a identificação pública da voz `oi8rgjIfLgJRsQ6rbZh3`. A integração usa a API oficial de texto para fala da ElevenLabs, com o modelo `eleven_multilingual_v2` e saída MP3.

**Requisitos:** conta ElevenLabs com acesso autorizado a essa voz, chave de API com permissão Text-to-Speech e créditos suficientes. O plano gratuito pode ter créditos limitados, mas a disponibilidade de Amanda Kelly **não é garantida em toda conta**. O modo gera áudio na internet e pode consumir créditos. A voz nunca é clonada pela Yuna.

### Instalar e ativar

1. Crie uma conta em [elevenlabs.io](https://elevenlabs.io/). Localize Amanda Kelly na biblioteca de vozes e confira se sua conta possui acesso.
2. Crie uma chave no painel de **API Keys**, com permissão de Text-to-Speech. **Nunca coloque a chave no GitHub, no chat ou em um arquivo público.**
3. Feche a mascote e abra o PowerShell na pasta do projeto. Configure a chave somente nessa janela, sem mostrar os caracteres no terminal:

   ```powershell
   $segredo = Read-Host "Cole sua chave da ElevenLabs" -AsSecureString
   $env:ELEVENLABS_API_KEY = [System.Net.NetworkCredential]::new("", $segredo).Password
   py -3 yuna_overlay.py
   ```

4. Na Yuna, clique no novo botão **🎙 Amanda** e leia o aviso sobre envio das falas à internet e consumo de créditos. Clique em **✓ Confirmar**. A personagem tocará uma frase curta de teste e usará essa voz nas respostas seguintes.

A chave fica somente no ambiente da sessão do PowerShell; não é guardada na memória `data/yuna.db` nem no código. Para usar Amanda em uma nova sessão, repita a configuração no PowerShell. Com a chave ausente, a opção mostra instruções e mantém a voz anterior. O modo Edge TTS e a voz local continuam funcionando sem chave ElevenLabs.

**Atenção à privacidade:** ao confirmar a voz Amanda, o texto falado será enviado para a ElevenLabs, inclusive qualquer resposta da Yuna que possa conter fatos pessoais, e pode ser armazenado pelo provedor conforme o plano. Não use para conversas privadas. É possível desligar a voz a qualquer momento. A Yuna não envia áudios ou memórias completas à ElevenLabs: envia somente o texto que seria falado, limitado a 520 caracteres.

A reprodução pelo Windows/Qt e o acesso à voz Amanda precisam ser validados no seu computador. Os testes automatizados apenas simulam a resposta da API; não consomem créditos nem garantem que sua chave tenha acesso à voz.


## Correção da mascote muda (Yuna 0.9)

Identificamos um erro de **fluxo da interface**, independente do provedor de voz: o MP3 era gerado mas não era encaminhado ao `QMediaPlayer`. O método `say()` foi corrigido para emitir `edge_ready` depois de sintetizar o arquivo; também foram adicionadas indicações de **Preparando voz…**, **Reproduzindo voz…** e mensagens separadas para erros de síntese e reprodução.

Se a mascote mostra `🔊 Jovem` mas não fala, feche-a, copie a versão atualizada de `yuna_overlay.py` para sua pasta instalada e reabra `iniciar_yuna_mascote.bat`. **Preserve `assets/` e `data/`**; não é necessário reinstalar o Ollama, o PySide6 ou o Edge TTS para corrigir este defeito.

A voz **Jovem** utiliza o `edge-tts`, que não exige chave de API mas depende de conexão com internet e de um serviço não oficial sujeito a mudanças. Ative-a somente quando aceitar que as frases sintetizadas sejam enviadas para fora do computador. As opções **Offline** e **Muda** continuam disponíveis gratuitamente.

Caso apareça `'lazy_import' object is not callable` mesmo com o áudio agora conectado ao reprodutor, isso **é outro erro**, relacionado ao ambiente Python/bibliotecas: siga a seção anterior sobre usar Python 3.13 para síntese. Se o status indicar `Falha ao tocar MP3`, teste o arquivo MP3 fora da Yuna e confira as saídas de áudio do Windows.

## Yuna 0.10 — Diário da Escuridão escrito aos poucos

A mascote agora possui o botão **📖 Diário**, que abre uma segunda janela com as páginas da personagem Yuna/Escuridão. Ao clicar em **✍ Escrever agora**, o **Ollama local** gera um parágrafo de reflexão fictícia sobre a evolução da assistente. A Yuna mostra e salva o texto gradualmente, em pequenos trechos, no arquivo **`data/diario_yuna.md`**.

Se você escolher **▶ Ativar automático**, a Yuna gera uma nova página a cada **15 minutos**, **somente enquanto a mascote estiver aberta**. A opção começa desligada e pode ser desativada na própria janela. É guardada em **`data/diario_yuna_config.json`** para as próximas sessões. O diário não roda com o computador desligado nem faz gravações pela câmera ou microfone.

O arquivo é **Markdown**, que pode ser aberto no Bloco de Notas, VS Code ou convertido mais tarde em documento Word/PDF. O limite de tamanho é 1 MB para evitar crescimento descontrolado. O botão **✍ Escrever agora** funciona mesmo com a escrita automática desligada. Entradas antigas são preservadas, inclusive após fechar e abrir a Yuna. Faça backup da pasta `data/` antes de atualizar.

**Privacidade e limites:** o diário usa o mesmo modelo Ollama já instalado e não envia dados a APIs de voz ou outros serviços. O prompt de geração **não contém conversas, arquivos, memórias ou dados pessoais** do usuário; ele escreve ideias gerais sobre aprender a ajudar melhor. São reflexões **literárias simuladas**, não um registro de sentimentos conscientes. A Yuna só pode criar/modificar esse arquivo na pasta `data` e não altera outros documentos por conta própria.

**Instalação:** feche a Yuna, copie `diary.py`, `yuna_overlay.py`, `self_model.py`, `yuna.py` e `iniciar_yuna_mascote.bat` atualizados para a pasta antiga, sem apagar `assets/` nem `data/`. Se preferir, atualize todos os arquivos `.py` a partir do ZIP. Não precisa instalar bibliotecas adicionais. Abra `iniciar_yuna_mascote.bat` e clique no botão **📖**.

**Desempenho:** uma reflexão demanda uma chamada ao Ollama, então pode demorar alguns segundos dependendo do modelo. Se estiver conversando com a Yuna, a escrita aguarda sua vez e não executa comandos do computador.

## Yuna 0.11 — arquivos reais Word, TXT e Markdown

Antes desta atualização, o Ollama apenas **explicava** como criar um Word e não tinha permissão ou ferramenta para salvar arquivos. Agora a Yuna pode criar arquivos reais com o botão **📄** na mascote ou com pedidos explícitos pelo chat.

### Jeito mais fácil: escolher onde salvar

1. Abra `iniciar_yuna_mascote.bat` com o Ollama funcionando.
2. Clique no botão **📄** ao lado do diário.
3. Escolha **Word (.docx)**, **Texto (.txt)** ou **Markdown (.md)**; informe o nome e o assunto.
4. Use **📂 Escolher pasta…** para selecionar qualquer pasta existente no seu Windows em que você tenha permissão de escrita.
5. Clique em **✨ Criar arquivo**. O Ollama local escreve o conteúdo; a Yuna cria o documento e exibe o **caminho onde realmente salvou**. O Word não precisa estar instalado ou aberto para gerar `.docx`.

### Pedidos pelo chat e terminal

Estes comandos são reconhecidos pelo programa, não por instruções inventadas pelo modelo:

```text
Crie um documento Word chamado Diário da Yuna na pasta Documentos
Cria um Word chamado Contas 2026 na Área de Trabalho
/criar word Diário da Yuna | Documentos | Escreva a primeira página do diário
/criar texto Lista de tarefas | Downloads | Faça uma lista curta
```

Pedidos escritos no chat só salvam automaticamente nas pastas **Documentos, Downloads ou Área de Trabalho** do perfil. Para qualquer outra pasta, use o botão **📄** e selecione o local explicitamente. Se o pedido estiver incompleto, a Yuna deve explicar como completá-lo, não fingir que criou um arquivo.

Os arquivos **não são sobrescritos**: se `Diário da Yuna.docx` já existir, será salvo `Diário da Yuna (2).docx`. O conteúdo é gerado no computador pelo Ollama; nome, formato e caminho são determinados pela ferramenta local e nunca pela resposta do modelo. Nenhum comando do sistema é executado a partir do conteúdo gerado.

**Importante:** nesta versão há suporte a **criação inicial** de documentos. Ela ainda não edita documentos Word existentes, nem cria planilhas Excel ou apresentações PowerPoint. Essas funções podem ser acrescentadas depois. O diário próprio em `data/diario_yuna.md` continua independente.

### Instalação da versão 0.11

Feche a Yuna e faça backup da pasta `data/`. Copie `document_writer.py`, `yuna.py`, `yuna_overlay.py`, `self_model.py` e `requirements-mascote.txt` da versão nova para a antiga. Preserve as pastas **`data` e `assets`**. No PowerShell aberto dentro da pasta do projeto, execute:

```powershell
py -3 -m pip install python-docx
```

Depois abra `iniciar_yuna_mascote.bat`. Não precisa reinstalar o Ollama ou o PySide6. O `python-docx` é gratuito e funciona localmente. Um arquivo DOCX de teste é verificado nos testes automatizados da versão.
