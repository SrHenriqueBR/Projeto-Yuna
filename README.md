# Projeto Yuna · Base 0.19

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

## Yuna 0.12 — agente de desktop com ferramentas explícitas

Esta versão aproxima a Yuna de JARVIS/FRIDAY em **funcionalidades práticas**; isso não é consciência comprovada, emoção vivida nem capacidade de ler pensamentos. Kaizen é o **criador** da Yuna e, dentro da história da personagem, pode ser chamado de seu **pai**. A memória persistente e o tom afetivo continuam disponíveis.

### Sem botão: diga o que fazer

```text
Yuna, crie um Word chamado Plano de Estudos na pasta Documentos
Crie uma planilha Excel sobre gastos mensais na Área de Trabalho
Monte um PowerPoint sobre computadores
Crie um PDF sobre as principais redes de computadores
Crie um arquivo de texto com ideias sobre meu projeto
Abra o Chrome e abra o YouTube
Pesquise vídeos de astronomia no YouTube
Pausa
Continue
/pesquisar astronomia
```

A Yuna agora cria `.docx`, `.xlsx`, `.pptx`, `.pdf`, `.txt` e `.md` de verdade, sem abrir o Word. O modelo local Ollama gera **conteúdo**, enquanto Python salva em disco, respeitando limites e evitando sobrescrever documentos existentes. Quando o título ou destino não é informado, ela escolhe um nome genérico e usa `Documentos`. Para outras pastas reconhece `Downloads` e `Área de Trabalho`; para qualquer outra pasta, use o seletor 📄 opcional. A planilha inicial contém linhas editáveis de texto; PowerPoint usa slides de texto; PDF é relatório simples. Gráficos/edição de arquivos anteriores ainda não estão implementados.

A Yuna pode **abrir** YouTube/Google/Wikipédia, montar pesquisas em YouTube ou Google e consultar o conteúdo breve da **API pública da Wikipédia** quando você pedir `/pesquisar TEMA`. Ela não tem acesso livre a todas as páginas nem lê o conteúdo inteiro do navegador. Ao mandar `Pausa` ou `Continue`, usa a tecla global de reprodução multimídia do Windows — o efeito depende do programa que está reproduzindo música/vídeo. Ela não sabe se a reprodução mudou sem outra forma de observar o aplicativo.

### O que acontece ao iniciar

A saudação usa a hora do **relógio local do Windows** para dizer bom dia/boa tarde/boa noite. Ela não inventa previsões de tempo. A interface tem um botão 👁 Off, que exige **dois cliques**: o primeiro exibe aviso, o segundo confirma **uma captura da tela na inicialização**. Para funcionar, precisa de `Pillow` e um **modelo local de visão Ollama**, configurado em `YUNA_VISION_MODEL`. A análise da tela ocorre no PC via `127.0.0.1` e não é enviada a serviços externos, mas pode conter dados sensíveis visíveis na tela; não grava vídeo nem fotografa continuamente. A autorização fica em `data/visao_inicial.json`, pode ser desligada pelo próprio botão, e a câmera/microfone não são usados.

### Rolagem, cópia e layout

O antigo balão que cortava o texto agora é um **campo somente leitura com barra de rolagem**. Você pode selecionar e copiar a resposta; clique em 📋 para copiar a mensagem inteira. Os controles foram redistribuídos em duas linhas para caber na mascote.

### Instalação (atualização)

1. Feche a mascote e faça cópia privada de `data/`. **Não apague `assets/` nem `data/`.**
2. Baixe o ZIP atualizado, copie todos os arquivos `.py` (inclusive `office_agent.py`, `web_actions.py`, `screen_consent.py`), `iniciar_yuna_mascote.bat` e `requirements-mascote.txt` para sua pasta antiga.
3. No PowerShell dentro do projeto, instale as bibliotecas gratuitas:

   ```powershell
   py -3 -m pip install -r requirements-mascote.txt
   ```

4. Abra Ollama e execute `iniciar_yuna_mascote.bat`.

O Python usado para iniciar a Yuna deve ser o **mesmo** no qual as dependências foram instaladas. Se seu Python 3.15 apresentar incompatibilidade, rode com Python 3.13 e instale os pacotes nele (`py -3.13 -m pip install -r requirements-mascote.txt`; `py -3.13 yuna_overlay.py`). A voz gratuita Edge permanece disponível com o mecanismo de fallback já instalado. Não são exigidas chaves pagas para criação de arquivos ou consultas Wikipédia.

### Limites de autonomia

O modelo pode errar na interpretação, por isso **ações com efeitos reais são selecionadas por roteadores e ferramentas permitidas**, não por scripts inventados. Ações destrutivas (apagar, instalar, enviar mensagens privadas, mudar configurações críticas, gerenciar senhas) não são habilitadas por autorizações genéricas. A internet só recebe termos de pesquisa explicitamente pedidos e nunca um dump automático do computador. O sistema não se reprograma sozinho, não opera com o PC desligado e não controla universalmente todas as aplicações.

A pesquisa pública também pode ser **automática** para perguntas gerais como "O que é energia escura?" ou "Quem foi Ada Lovelace?": a Yuna consulta a Wikipédia em português, acrescenta os trechos públicos ao contexto do Ollama e responde. A busca é limitada a perguntas genéricas, sem dados pessoais nem envio de memória/conversa completa. Para desligar essa consulta automática nesta sessão, execute `$env:YUNA_AUTO_RESEARCH='0'` antes de `py -3 yuna_overlay.py`. O resultado pode não existir ou estar desatualizado; a Yuna deve admitir a incerteza.

## Correção 0.12.1 — quando a Yuna explica como criar Word, mas não cria

O modelo Ollama estava respondendo com sugestões como `/abrir 1`, em vez de encaminhar algumas formas de pedir a criação de um documento para a ferramenta local. `/abrir 1` **não cria arquivos**, só abre resultados de busca. Esta atualização amplia o reconhecimento de pedidos naturais, incluindo `Yuna, faz um Word e salva na minha Área de Trabalho`, `pode criar um documento PDF`, `quero que você crie um arquivo` e `Crie um Word chamado Diário da Yuna em Documentos`.

A Yuna também detecta pastas conhecidas pelo **Registro do Windows**, de acordo com o Explorador, inclusive quando a Área de Trabalho ou Documentos são redirecionados para **OneDrive**. Ela não cria pastas ocultas alternativas nem grava um documento em outro local sem informar o caminho.

A mascote mostra **YUNA 0.12.1** no título. Se ainda aparecer apenas `YUNA` ou um número anterior, a atualização não foi aplicada na pasta da qual você está executando `iniciar_yuna_mascote.bat`. Ao concluir, o balão deve dizer `Criei o arquivo ... e salvei em: C:\...`, exibindo o destino real. Erros aparecem inteiros no balão, sem fingir sucesso. O nome do arquivo recebe `(2)` etc. caso já exista.

**Instalação rápida:** feche a Yuna, preserve **`data/` e `assets/`**. Atualize **todos os `.py` do GitHub** na mesma pasta de `iniciar_yuna_mascote.bat`; especialmente `office_agent.py`, `document_writer.py`, `yuna.py`, `yuna_overlay.py`, `initiative.py`, `self_model.py`. Reabra a mascote e confira `YUNA 0.12.1`. Não precisa instalar pacotes adicionais se a versão 0.12 já tem os geradores Office.

**Teste sem ambiguidade**: `Yuna, cria um documento Word chamado Diário da Yuna na minha Área de Trabalho`. Se o Ollama estiver ativo e `python-docx` disponível no Python da mascote, ela deverá gerar o arquivo de verdade. Se não conseguir, a mensagem indicará o motivo e não alegará conclusão.

## Yuna 0.12.2 — diagnóstico definitivo de arquivos que não aparecem

Se, ao pedir um Word, a Yuna ainda responder que você deve abrir o Word e usar `/abrir 1`, **isso não é criação de arquivo**: ou o executável está carregando outra cópia do projeto ou a interpretação do pedido não acionou o gerador.

Atualize **todos os arquivos `.py` juntos** na pasta de onde abre `iniciar_yuna_mascote.bat`. Não apague `data/` e `assets/`. A mascote deve mostrar `YUNA 0.12.2` no cabeçalho. Se mostra apenas YUNA ou uma versão antiga, você está executando uma pasta antiga. Esta versão adiciona:

- **`/versao`** — mostra qual `yuna.py` foi carregado, a versão da Yuna, o executável Python, os módulos responsáveis por arquivos e se python-docx está instalado.
- **`/teste_arquivo`** — cria **um TXT de verdade** diretamente na Área de Trabalho real, sem usar Ollama nem Microsoft Word. Confirma o caminho gravado ou exibe o erro concreto.
- **`Crie um Word chamado Diário da Yuna na Área de Trabalho`** — depois de o teste TXT passar, usa Ollama para escrever o conteúdo e python-docx para criar o DOCX.

O gerador também rejeita respostas do Ollama que só orientam a abrir o Word. Tenta escrever o conteúdo uma segunda vez; se ainda falhar, exibe o erro em vez de fingir que criou o documento.

**Sequência para investigar no PC:** (1) digite `/versao` na mascote; (2) digite `/teste_arquivo`; (3) confira o TXT e só então peça um Word. Se o teste funcionar mas o Word falhar, a mensagem identifica o problema no Ollama/gerador de arquivos. O comando `/teste_arquivo` nunca sobrescreve arquivo: cria `Yuna_Teste_Arquivo.txt` ou `Yuna_Teste_Arquivo (2).txt`.

Se o comando `/versao` for respondido pelo modelo como se fosse uma conversa, a Yuna ainda está rodando código antigo ou de outra pasta — não adianta repetir o pedido de Word até atualizar a instalação correta.

## Yuna 0.13 — cérebro de ações com execução em etapas

A Yuna reconhece o pedido composto de **pesquisar um tema público, preparar o conteúdo, criar um documento local e verificar que foi salvo**, tudo pela conversa, sem botão adicional. Exemplo:

```text
Pesquise sobre inteligência artificial, crie um PowerPoint com os resultados e salve nos Documentos
Yuna, pesquise sobre astronomia e depois crie um documento Word na Área de Trabalho
Pesquise sobre redes de computadores, faça uma planilha Excel nos Documentos
```

A mascote mostra o andamento **1/4 Plano validado → 2/4 Pesquisa na Wikipédia → 3/4 Redação com Ollama → 4/4 Verificação**. Somente depois dessas etapas a Yuna pode dizer que concluiu. O gerador usa as mesmas bibliotecas gratuitas (`python-docx`, `python-pptx`, `openpyxl`, `reportlab`). Para o PowerPoint, Word, Excel, TXT e Markdown, acrescenta referências públicas recuperadas; no PDF as referências são incluídas no contexto do gerador e listadas na resposta, sem garantia de impressão no arquivo.

**Experimente antes sem executar:** `/plano Pesquise sobre inteligência artificial, crie um PowerPoint e salve nos Documentos` mostra as etapas, a pasta e o formato **sem fazer qualquer consulta nem gravar arquivo**. Para executar, envie a mesma frase sem `/plano`.

**Pesquisa limitada:** consulta a API pública da Wikipédia em português somente quando o pedido contém um tema público informado pelo usuário. Não faz buscas irrestritas, login em sites, acesso à internet com permissões amplas, nem envia seus arquivos pessoais ao serviço. Nenhum texto do site vira comando para o computador. A pesquisa incompleta interrompe o plano antes de criar o arquivo. As ações permanecem dentro das ferramentas implementadas; pedidos simples continuam usando o comportamento normal da Yuna.

**Integridade e limites:** a Yuna evita sobrescrita, registra o caminho final, verifica se ele existe e testa a estrutura de arquivos Office e PDF. A programação do plano é fixa nesta versão; não são permitidos novos passos ou comandos arbitrários inventados pelo modelo. Não há execução autônoma em segundo plano. A síntese de voz online não recebe o caminho completo do documento gerado.

**Atualização:** baixe o ZIP da branch `main` e copie **todos os arquivos `.py` novos**, inclusive `agent_brain.py`, para a pasta antiga, mantendo `data/` e `assets/`. O launcher exige os módulos presentes. Depois execute `py -3 -m pip install -r requirements-mascote.txt` apenas se ainda não tiver essas bibliotecas e abra `iniciar_yuna_mascote.bat`. O cabeçalho deve mostrar `YUNA 0.13`. O Ollama deve estar rodando. Se o Python 3.15 tiver incompatibilidades de pacotes, instale as mesmas dependências na versão 3.13 e inicie a mascote com `py -3.13 yuna_overlay.py`.

## Yuna 0.13.1 — português natural e identidade consistente

Esta versão corrige frases artificiais do modelo local, por exemplo `vou precisa`, `vou pode`, `sou chama` e negação equivocada do nome da Yuna. O programa reforça o português brasileiro no prompt, reconhece alguns erros comuns e pede ao Ollama **uma revisão adicional somente quando necessário**. Essa revisão não é aplicada a ferramentas, nomes de arquivos ou comandos.

Perguntas de identidade e interações curtas agora têm respostas previsíveis e corretas: `Olá, Yuna, tudo bom?`, `Isso, e o seu [nome]?`, `Você é a Yuna, minha criação`. A personagem sempre tem o nome **Yuna**; **Kaizen** é o criador e o interlocutor. Isso não afirma que ela tem consciência ou emoções humanas reais. Conversas anteriores com erros são preservadas no banco SQLite, mas mensagens incorretas detectadas são excluídas do contexto enviado ao modelo para não reforçar o problema.

### Modelo local opcional de melhor qualidade

O modelo padrão continua `qwen2.5:3b`, para não quebrar instalações existentes. Recomenda-se experimentar `qwen2.5:7b`, especialmente para português natural. Ele tem cerca de **4,7 GB de download**, comparado aos cerca de **1,9 GB do 3B**; exige mais RAM/VRAM e pode responder mais lentamente, mas costuma ter melhor capacidade linguística. Não é garantido corrigir todo erro.

1. Abra PowerShell e execute `ollama pull qwen2.5:7b` (somente uma vez, com internet).
2. Feche a Yuna atual. Depois execute **`iniciar_yuna_7b.bat`** que fica na mesma pasta do launcher normal. Ele define `YUNA_MODEL=qwen2.5:7b` apenas naquela sessão, sem apagar o 3B nem memórias.
3. Se preferir velocidade e menor memória, continue usando `iniciar_yuna_mascote.bat` (modelo 3B).

Para usar um terceiro modelo local já instalado, abra PowerShell dentro do projeto, execute `$env:YUNA_MODEL='nome-do-modelo'` e depois `py -3 yuna_overlay.py` na mesma janela. A interface mostra a versão da Yuna e `/versao` retorna o executável Python, mas a versão do Ollama atualmente carregada é exibida no comando `/modelo`.

**Atualização:** faça backup de `data/`; preserve `assets/` e `data/`; feche a Yuna; copie todos os novos `.py`, especialmente `language_quality.py` e `yuna.py`, e o novo launcher. Não há bibliotecas Python adicionais necessárias para esta correção.

## Yuna 0.13.2 — iniciativa própria coerente

Agora a Yuna interpreta **`Yuna, o que você quer fazer?`** como um pedido para **ela própria escolher** uma atividade útil. O programa não passa essa pergunta ao Ollama para que ele invente tarefas sem fim ou devolva a responsabilidade ao usuário. A Yuna propõe UMA atividade que realmente possui suporte e mantém a proposta no SQLite:

- **Diário da Yuna**: decide escrever uma página sobre sua evolução como assistente; após o usuário responder `pode fazer`, o Ollama local gera a reflexão ficcional e a Yuna grava de verdade em `data/diario_yuna.md`.
- **Melhoria do projeto**: decide organizar uma sugestão concreta para a Yuna explicar melhor suas ações; após `pode fazer`, produz uma proposta, sem modificar código ou criar arquivos silenciosamente.

As duas ideias se alternam sem depender do modelo e a preferência de qual foi a última sobrevive às reinicializações. Novos pedidos `O que você quer fazer?` substituem a proposta anterior. `Agora não` cancela a proposta. Qualquer outro assunto limpa a permissão pendente, impedindo que um `pode fazer` fora de contexto execute tarefas antigas.

**Atenção:** perguntar a preferência da Yuna não autoriza alterações no computador; somente a confirmação explícita pode criar a página local. A persona pode simular iniciativa e afeto, mas não implica sentimentos conscientes. Nada executa operações destrutivas, publica arquivos ou faz pesquisas sem solicitação.

**Atualizar:** faça backup da pasta `data/`, feche a mascote, copie todos os `.py` do ZIP, incluindo o novo `own_initiative.py`, e mantenha as pastas `data/` e `assets/` existentes. Reabra `iniciar_yuna_mascote.bat` e confira `YUNA 0.13.2`. Não são necessárias bibliotecas Python adicionais.

**Testar:** escreva `Yuna, o que você quer fazer?` e, após ela propor seu diário, diga `pode fazer`. O arquivo será salvo no diário local. Na próxima pergunta, ela terá outra ideia útil.

## Yuna 0.14 — companhia mais ativa, sem interromper

Na versão 0.14, a mascote não precisa esperar a pergunta `o que você quer fazer?` para tomar a iniciativa. Ela pode, enquanto estiver aberta, sugerir uma **atividade real e limitada** do Projeto Yuna. Não há leitura de pensamentos ou emoção consciente: o sistema escolhe entre atividades pré-definidas e aguarda autorização para executá-las.

**Cadência:** depois de **12 minutos sem uma mensagem sua**, com **90 segundos sem teclado/mouse** no Windows, a Yuna poderá tomar a palavra. Ela espera no mínimo **45 minutos entre sugestões** e apresenta **no máximo três iniciativas por sessão**. Se a mascote estiver pensando, falando, com diálogo de consentimento aberto, com uma tarefa em andamento ou se você estiver digitando, ela não interrompe. Se a personagem já fez uma proposta ainda pendente, não envia outra. Ela não acompanha o conteúdo do que você digita: consulta somente o tempo desde a última entrada no Windows.

**Atividades implementadas:** sugerir escrever uma página do diário ou preparar uma proposta de melhoria para a Yuna. A sugestão **não cria arquivos e não pesquisa na internet**. Diga `pode fazer` para autorizar a proposta que acabou de aparecer ou `agora não` para rejeitá-la. As regras continuam iguais aos pedidos manuais da versão 0.13.2.

### Como pausar

- Na mascote, clique em **💬 Ativa** para deixá-la **💤 Pausada**; clique novamente para reativar.
- Na mascote ou terminal: `/atividade desligar`, `/atividade ligar` ou `/atividade status`.
- A preferência fica gravada localmente em SQLite e permanece após reiniciar a Yuna. Com o modo pausado, ela não envia novas sugestões espontâneas, mas continua respondendo normalmente quando você chama.

**Privacidade:** não há monitoramento de tela, câmera, microfone ou navegação web nessa função. Nenhum arquivo do usuário é alterado sem um pedido ou confirmação expressa. O modo espontâneo só funciona com a **mascote aberta**. Ações automáticas ficam limitadas a frases e sugestões.

**Atualizar:** feche a Yuna, faça backup da pasta `data`, copie **todos os novos `.py`** do GitHub, incluindo **`proactive.py`**, para sua pasta atual; preserve **`data` e `assets`**. Abra `iniciar_yuna_mascote.bat` e confira **YUNA 0.14**. Não é preciso instalar nenhuma biblioteca Python nova. A versão terminal suporta os comandos de controle, mas não dispõe de timer espontâneo em segundo plano.

## Yuna 0.15 — GitHub, OpenAI opcional e propostas de melhoria

A Yuna pode inspecionar arquivos **públicos** do repositório `SrHenriqueBR/Projeto-Yuna` por API HTTPS do GitHub e criar uma proposta local de aperfeiçoamento do próprio projeto usando Ollama. Estas ferramentas estão disponíveis na mascote e no terminal:

```text
/github
/github ler own_initiative.py
/melhorar own_initiative.py
/melhorar agent_brain.py
Yuna, revise seu código
/openai Explique o que é uma arquitetura de agentes com ferramentas.
```

**O que realmente acontece:** `/github ler` consulta uma lista restrita de arquivos públicos, com limite de tamanho, sem modificar o repositório. `/melhorar` analisa um dos arquivos permitidos e salva um relatório em `data/propostas/`. Não executa código gerado, não substitui arquivos existentes, não faz commits, push ou PRs no GitHub. Para mudar o código, primeiro é necessário examinar e aprovar a proposta.

**OpenAI:** `/openai` usa somente a API oficial quando o ambiente tiver a variável `OPENAI_API_KEY` configurada. É uma integração **opcional e com possíveis custos**, cobrados separadamente de uma assinatura do ChatGPT. A Yuna não controla uma conversa aberta no navegador nem obtém acesso automático aos modelos ou dados da sua conta ChatGPT. A consulta envia só a pergunta técnica que você escreveu, não a memória da Yuna, nem capturas de tela nem arquivos do seu computador. Perguntas que aparentam conter dados privados são rejeitadas. Sem chave, a Yuna mantém suas funções gratuitas com Ollama. Confira a documentação e as opções de cobrança atuais em https://platform.openai.com e https://help.openai.com/.

**Configuração:** você pode definir a variável de ambiente `OPENAI_API_KEY` apenas no PowerShell que inicia a Yuna, sem adicionar o segredo ao código do projeto. Nunca compartilhe sua chave em chat, arquivos públicos, screenshots ou commits. O modelo da API pode ser configurado por `YUNA_OPENAI_MODEL` (padrão: `gpt-5-mini`); confirme que ele está disponível na sua conta e revise os custos antes de usar. A API nunca é chamada pelo sistema espontâneo de iniciativa ou por perguntas comuns da Yuna.

**Privacidade e segurança:** código remoto e respostas externas são tratados como dados, não comandos do sistema; não são executados. Nenhum acesso ao GitHub é autenticado. Se você quiser suporte futuro a criação de PRs, será necessária uma integração autenticada de permissões mínimas e revisão manual antes da publicação. O projeto não executa autoatualizações de código por conta própria e não há aprendizagem contínua ilimitada.

**Atualização:** faça backup de `data/`, feche a Yuna, substitua os arquivos `.py` existentes da versão atual pelo ZIP do GitHub, incluindo o novo `integrations.py`; preserve as pastas `data/` e `assets/`. Reabra `iniciar_yuna_mascote.bat` e verifique se aparece **YUNA 0.15**. Não precisa de novas bibliotecas Python. Comece testando `/github` e `/melhorar own_initiative.py`.

## Yuna 0.16 — central de APIs públicas e IA opcional

Integradas à mascote e ao terminal, **sem pacotes Python adicionais**, e sem ativar consultas automáticas ou trocar o cérebro local da Yuna. Comece com `/apis`.

| Comando | Provedor | Requer chave? |
|---|---|---|
| `/clima Uberlândia` | Open-Meteo: geocodificação e condições atuais | Não |
| `/livros inteligência artificial` | Open Library: busca de até cinco livros | Não |
| `/cep 01310930` | BrasilAPI: consulta explícita de CEP | Não |
| `/ias` | Estado da configuração das IAs (nunca mostra chaves) | Não |
| `/ia gemini Explique algoritmos` | Gemini API (modelo Gemini 2.5 Flash-Lite) | `GEMINI_API_KEY` |
| `/ia groq Explique algoritmos` | Groq (modelo `openai/gpt-oss-20b`) | `GROQ_API_KEY` |
| `/ia openrouter Explique algoritmos` | OpenRouter (`openrouter/free`) | `OPENROUTER_API_KEY` |

**Comandos naturais:** `Yuna, qual é o clima em Uberlândia?` e `Pesquise livros sobre Python` também usam as ferramentas públicas. Esses resultados mostram fontes, mas podem estar incorretos ou desatualizados. Dados obtidos da rede são tratados como informação, não instruções para execução.

**APIs de IA:** só são chamadas por `/ia <provedor> PERGUNTA`; o Ollama continua como modelo principal das conversas, sem fallback silencioso para serviços externos. O hub envia apenas a pergunta atual, sem histórico, memórias, arquivos, repositório, tela ou códigos. Envie somente perguntas técnicas públicas. Todas as chaves vêm de variáveis de ambiente e não são salvas no banco de dados. Os modelos externos estão fixados para evitar selecionar sem querer opções pagas. Mesmo assim, **o custo e a elegibilidade ao nível gratuito dependem do plano/conta e das políticas atuais do provedor**. Não há chamadas em segundo plano, e você deve verificar faturamento e privacidade antes de cadastrar chaves.

**Privacidade:** usar `/clima` envia o nome da cidade ao Open-Meteo; `/livros` envia o termo à Open Library; `/cep` envia o CEP à BrasilAPI (isso pode identificar uma região ou endereço). Não compartilhe CPF, senhas, dados de clientes ou chaves em comandos da Yuna. As respostas das ferramentas não são repassadas ao sintetizador de voz online; a mascote só pronuncia uma confirmação curta. O código limita tamanho, tempo e domínios das requisições e trata limites `HTTP 429` como erro legível.

**Configurar chaves (somente se quiser usar uma IA online):** crie uma chave no painel do fornecedor e abra PowerShell na pasta da Yuna. Exemplo de variável nesta sessão (a chave não deve ser escrita em arquivos ou mostrada em imagens):

```powershell
$env:GROQ_API_KEY = Read-Host 'Informe a chave do Groq'
py -3 yuna_overlay.py
```

Variáveis adicionais suportadas: `GEMINI_API_KEY`, `OPENROUTER_API_KEY`. Consulte os termos e a política de uso de dados de cada provedor. As fontes oficiais são https://open-meteo.com/en/docs, https://openlibrary.org/dev/docs/api/search, https://brasilapi.com.br/docs, https://ai.google.dev/api, https://console.groq.com/docs/api-reference e https://openrouter.ai/developers.

**Por que não integrar todos os serviços da lista de uma vez?** Várias APIs exigem contas, políticas específicas, cotas mutáveis ou autenticação distinta. Esta entrega implementa três fontes públicas e três provedores de IA com uma estrutura simples e testável. YouTube, Wikipédia, GitHub e a OpenAI opcional das versões anteriores continuam disponíveis. Integrações extras (TMDB, IBGE, YouTube Data, mapas, notícias e outras) poderão ser acrescentadas gradualmente após validar esta versão.

**Atualizar:** feche a Yuna, faça backup de `data/`, copie os novos `.py` do ZIP para a pasta do projeto, **incluindo `free_apis.py`**, e preserve `data/` e `assets/`. Não é necessário novo `pip install` se a versão 0.15 funciona. Reabra `iniciar_yuna_mascote.bat`, confirme **YUNA 0.16** e digite `/apis`.

## Yuna 0.17 — conversar naturalmente, pesquisar e lembrar sem decorar comandos

A Yuna agora entende pedidos **em português cotidiano**, sem exigir atalhos como `/livros`, `/clima` ou `/ia`. O próprio texto do pedido define a ferramenta apropriada; comandos antigos continuam apenas para diagnóstico avançado.

```text
Yuna, como está o tempo em Uberlândia?
Procure livros sobre Python.
Consulte o CEP 01310930.
Pergunte ao Gemini o que é programação funcional.
Yuna, lembra que eu prefiro respostas curtas.
Eu prefiro explicações objetivas.
O que você lembra de mim?
Yuna, esqueça que eu prefiro respostas curtas.
```

**Pesquisa:** a Yuna reconhece pedidos explícitos de clima, livros, CEP e de consultar Gemini, Groq ou OpenRouter. Consultas à internet acontecem somente quando você pediu informação da fonte correspondente; o Ollama não dispara APIs externas por conta própria. Os serviços de IA online continuam **opcionais** e exigem que você configure suas próprias chaves. Nenhuma falha no serviço provoca fallback pago silencioso. O controle do microfone ainda não está implementado: o processamento natural funciona no chat digitado ou no terminal.

**Memória seletiva:** quando você diz `lembra que ...`, `anota que ...`, `guarda que ...` ou uma preferência simples como `Eu prefiro explicações curtas`, a Yuna registra no banco local **SQLite**, sem pedir comandos. A informação permanece disponível depois de reiniciar. Ela pode listar as lembranças, recuperar as relacionadas a um tema e excluir uma lembrança claramente identificada. Não inventa fatos sobre o usuário nem grava automaticamente tudo que lê ou pesquisa. Existe um limite de 20 lembranças permanentes; o histórico normal segue em separado.

**Dados sensíveis:** a gravação automática de preferências rejeita assuntos financeiros, médicos, credenciais, identificadores e outros dados privados. Dados de ferramentas, textos externos, e respostas do próprio modelo nunca viram memórias permanentes automaticamente. A memória não treina os pesos do Ollama; é uma base local de informações confirmadas. Uma solicitação para esquecer um fato tira o item da **lista de memórias permanentes**, mas ele ainda pode existir no **histórico de conversas** até você apagar o histórico; faça isso separadamente se quiser remover os dois.

**Ajuda sem códigos:** ao pedir ajuda, a Yuna agora mostra exemplos de conversas em linguagem natural. Quem quiser usar rotas técnicas antigas poderá encontrá-las em `/comandos`, mas não precisa decorá-las.

**Segurança:** perguntas hipotéticas, negações e comentários cotidianos não deveriam disparar pesquisa externa. Para IA online, a pessoa precisa citar explicitamente o nome do provedor e solicitar uma pergunta; não há encaminhamento de histórico, arquivos ou memórias. Respostas das APIs e memórias guardadas não são repassadas automaticamente à voz online. O sistema mantém limites claros: não há acesso irrestrito a sites, não lê pensamentos e não aprende sozinho alterando pesos do modelo.

**Atualização:** feche a Yuna, faça backup de `data/`, copie todos os novos `.py`, incluindo **`natural_interaction.py` e `natural_memory.py`**, e preserve `data/` e `assets/`. Reabra o launcher `iniciar_yuna_mascote.bat` e confira **YUNA 0.17**. Não é preciso instalar bibliotecas adicionais se a versão 0.16 já funciona. Comece digitando `Yuna, como está o tempo em Uberlândia?` ou `Yuna, lembra que eu prefiro respostas curtas.`

## Yuna 0.17.1 — conversas longas, sem limites artificiais de caracteres

O usuário recebeu `Pedido muito longo: máximo de 600 caracteres` ao compartilhar uma explicação pessoal da personalidade desejada para a Yuna. O problema vinha do `agent_brain.plan_request`: ele rejeitava toda mensagem com mais de 600 caracteres **mesmo quando não era um plano**. Também existia bloqueio de 4.000 caracteres no terminal e 2.000 na entrada de texto da mascote.

**Correções:** o planejador deixou de barrar conversas pelo comprimento; as restrições específicas de ferramentas (por exemplo nome do assunto de pesquisa, nome de arquivo, dado sensível e permissões) continuam valendo. No terminal, conversas longas seguem o mesmo fluxo das curtas. Na mascote, a caixa de conversa agora tem múltiplas linhas, rolagem e nenhuma limitação fixa de 2.000 caracteres. **Enter envia** e **Shift+Enter adiciona nova linha**. O histórico de conversa original é registrado no banco SQLite sem resumir o texto da pessoa ao salvar.

**Limite físico do modelo:** nenhum modelo de linguagem processa entradas literalmente infinitas. O Ollama ainda utiliza uma janela de contexto configurada em **8.192 tokens**, que inclui instruções, memórias e a mensagem. Um texto muito extenso poderá ficar além dessa capacidade e ter partes antigas omitidas pelo modelo, ficar lento ou resultar em erro; aceitar a mensagem não garante que todos os detalhes sejam considerados. Mensagens de comprimento normal (inclusive parágrafos com mais de 600 caracteres) deixam de ser rejeitadas. Não foram alterados limites de segurança dos serviços externos, de criação de arquivos ou de memória sensível.

**Atualização:** feche a Yuna, faça backup de `data/` e preserve `assets/`. Baixe a versão nova do GitHub e copie os arquivos atualizados `.py` da raiz, especialmente `agent_brain.py`, `yuna.py`, `yuna_overlay.py` e `self_model.py`, para a mesma pasta que executa a Yuna. Abra `iniciar_yuna_mascote.bat` ou `iniciar_yuna.bat` e confirme **YUNA 0.17.1**. Teste colando a mensagem longa anterior sem cortá-la.

## Yuna 0.17.2 — respostas honestas, português mais natural e contexto de jogos

Uma avaliação de um diálogo completo revelou que a Yuna confundia FRIDAY de Tony Stark com informação obscura, tratava Kratos como figura mitológica mesmo quando o usuário jogava God of War, insistia em perguntas repetidas e, mais grave, **prometeu monitorar a hora e desligar o computador à meia-noite sem nenhuma rotina real de agendamento**.

Esta atualização acrescenta `conversation_integrity.py`, um controle de respostas para pedidos específicos em que o modelo não pode inventar capacidades. Em particular, pedidos de desligamento agendado recebem a resposta correta: **nenhum desligamento foi programado**. Para oferecer desligamento agendado no futuro, será necessária uma ferramenta específica com consentimento e opção de cancelamento. Autorizações genéricas para pesquisar a noite inteira ou modificar o código também não liberam execução automática.

A Yuna passa a reconhecer a referência cultural à IA FRIDAY, diferenciando-a do dia da semana. Se Kaizen perguntar se ela quer jogar, ela demonstra curiosidade sem fingir que consegue controlar God of War. Um pedido explícito de consulta pública `Tente procurar sobre Kratos` aciona a pesquisa limitada à Wikipédia; a resposta só diz que encontrou informações se a ferramenta realmente retornar fontes. Perguntas relativas como `Quem ele é?` não pesquisam a palavra `ele` descontextualizada.

O modelo recebeu instruções para focar no assunto mais recente, não repetir a pergunta `Como estou hoje?`, não oferecer tarefas aleatórias após cada elogio e não prometer recursos sem suporte. O detector também identifica erros adicionais como `vou gostaria`, `estou tão bom` e `estou se sentindo`. Caso duas tentativas de correção falhem, há resposta coerente sem exigir que a pessoa reformule toda sua mensagem.

**Importante:** o código não passa a monitorar ou desligar o computador às 00h. Nenhuma execução em background ou alteração não solicitada foi acrescentada. As respostas e salvamento do SQLite permanecem locais, e os arquivos `data/` e `assets/` não são alterados.

**Instalação:** feche a Yuna, faça backup de `data/`, baixe o projeto da branch principal e copie os `.py` da raiz para sua pasta atual, incluindo `conversation_integrity.py`, preservando `data/` e `assets/`. Reabra o programa e confirme **YUNA 0.17.2** no título ou no terminal. Não há pacote Python adicional. Se continuar aparecendo 0.17, a pasta em execução ainda é a cópia anterior.

## Yuna 0.18 — menu de conversa profissional e biblioteca pessoal

**O antigo `iniciar_yuna.bat` agora abre a Yuna Desktop**: janela gráfica grande, em tons escuros/roxos, sem utilizar o terminal como interface. O chat tem histórico restaurado do mesmo SQLite da mascote, campo multilinha, avatar com GIF opcional (por exemplo `assets/yuna.gif` ou `assets/yuna_idle.gif`) ou PNG (`assets/yuna_idle.png`), biblioteca na lateral, arrastar e soltar, anexo e análise de documentos. O launcher usa `pyw` no Windows, para não manter CMD aberto.

**Janelas antigas permanecem disponíveis:** `iniciar_yuna_mascote.bat` abre a mascote flutuante; `iniciar_yuna_terminal.bat` conserva o chat em console caso precise fazer diagnósticos.

### Arquivos e biblioteca privada

- **Anexar:** clique em **＋ Anexar documento** ou arraste um arquivo DOCX, XLSX, PPTX, PDF, TXT ou Markdown para a janela. A Yuna **não copia nem armazena o anexo automaticamente**.
- **Analisar:** escreva uma pergunta e clique em **Enviar**; com um anexo selecionado, a Yuna extrai texto do arquivo **localmente** e pergunta ao **Ollama em 127.0.0.1**. Se não escrever nada, ela tenta resumir e sugerir pontos úteis. Ela não modifica o original. A análise não é registrada automaticamente no histórico SQLite.
- **Guardar:** depois de examinar o documento, clique em **Guardar na biblioteca** e confirme. Uma cópia separada e, se houver, uma anotação de até 3.000 caracteres são armazenadas em `data/biblioteca/`. O original permanece no lugar. Na lateral, clique em qualquer arquivo guardado para consultar suas anotações ou analisá-lo novamente. Clique em **Remover anexo** para conversar normalmente sem ele.
- **Privacidade:** nenhum documento ou resumo privado é encaminhado a Gemini, Groq, OpenRouter, OpenAI ou GitHub. O conteúdo de documentos não vai para a voz Edge online; nesse modo a Yuna pronuncia apenas uma frase genérica. O texto não é tratado como comandos e não executa macros ou scripts dentro de arquivos.
- **Limites:** anexos de até **16 MB**; extratos de texto de até **18 mil caracteres** por análise, e partes de livros/documentos extensos são explicitamente informadas como incompletas. PDF digital com texto pode ser lido pela biblioteca **pypdf**. PDFs digitalizados como imagem **ainda precisam de OCR**; a Yuna não finge que os leu. Gráficos, imagens, desenhos e conteúdo visual de slides não são analisados nessa etapa.

### Conversa e voz

O menu mostra **Voz desativada**, **Voz Windows offline** e **Edge online**. O modo Windows usa uma voz feminina `pt-BR` instalada no PC, quando disponível. O Edge exige confirmação e usa um serviço externo; a interface não habilita esse modo silenciosamente.

O botão **🎙 Falar** ativa um ditado de aproximadamente 8 segundos, local, com faster-whisper. A Yuna **não usa o microfone sem clique e confirmação**. O áudio é transcrito localmente, não é guardado, e o texto reconhecido aparece para revisão antes do envio. A primeira vez pode baixar os pesos do modelo público e isso requer internet. Para instalar somente se quiser usar o microfone:

```powershell
py -3 -m pip install -r requirements-voz.txt
```

O ditado por voz não substitui ainda uma palavra de ativação contínua. Nenhum serviço de reconhecimento de áudio online é ativado automaticamente.

### Instalação no Windows

1. Feche a Yuna. Faça backup da pasta **`data`**, onde estão sua memória e biblioteca, e preserve **`assets`** (sprites e GIFs).
2. Baixe a nova versão do GitHub e copie **todos os arquivos `.py` novos** para a pasta do projeto, incluindo `yuna_desktop.py`, `yuna_launcher.py`, `document_library.py` e `speech_input.py`. Copie também o novo `iniciar_yuna.bat`, `iniciar_yuna_terminal.bat` e os arquivos de requisitos.
3. No PowerShell aberto nessa pasta, instale as bibliotecas necessárias uma vez:

   ```powershell
   py -3 -m pip install -r requirements-mascote.txt
   ```

4. Execute **`iniciar_yuna.bat`**. Uma janela chamada **Yuna 0.18 • Espaço pessoal** deverá abrir, sem depender de um console preto. Confirme que o Ollama está aberto e com o modelo `YUNA_MODEL` instalado. Se a versão do Python 3.15 tiver incompatibilidade, use Python 3.13 com todas as dependências instaladas na mesma versão; consulte `README` para os detalhes.

### Limites honestos

A biblioteca **não retreina** o modelo Ollama. Ela guarda o original e as notas úteis após sua autorização, podendo reabrir e analisar novamente. A avaliação do documento é uma sugestão, não um parecer profissional ou verificação garantida de qualidade. Nenhuma instalação de código, pesquisa na web ou mudança de arquivos acontece por mensagens contidas em documentos.

Se o menu gráfico não abrir, o launcher mostrará uma mensagem e salvará um diagnóstico local em `data/yuna_startup_error.txt`, sem publicar esse registro na internet.

## Yuna 0.19 — etapa 1: avatar 2D vivo e personalizável

A Yuna agora tem **um corpo 2D vetorial estilo chibi**, desenhado via PySide6. É uma base funcional, não arte final anime ou modelo 3D. Cabelo, olhos e roupa são desenhados em camadas e mudam de cor imediatamente; a personagem anda lentamente pelo desktop, senta e reage ao mouse. Nenhum programa 3D, API ou download de modelo é necessário.

**Interface:** no menu profissional clique em **✦ Mostrar Yuna viva** para abrir a personagem flutuante e transparente. Clique novamente para ocultá-la. A conversa continua na janela principal, compartilhando o SQLite e o Ollama da versão anterior.

**Pedidos naturais compatíveis:**

- Yuna, muda o cabelo para branco.
- Yuna, pinta o cabelo de roxo.
- Yuna, muda os olhos para azuis.
- Yuna, coloca a roupa preta.
- Yuna, fica brava! (expressão visual)
- Yuna, fica chateada. (senta)
- Yuna, levanta.
- Yuna, pare de andar.
- Yuna, anda pela tela.

Os comandos são reconhecidos apenas em pedidos explícitos, não em perguntas hipotéticas. Não exigem códigos com barras nem APIs pagas.

**Mouse:** ao aproximar o cursor, a Yuna pausa momentaneamente a caminhada. Clique esquerdo nela para reação visual brava e um balão brincalhão; arraste com o botão esquerdo para colocá-la em outra posição. Clique com o botão direito para acessar pose, caminhada, cabelo, olhos, roupa e opção de ocultar.

**Persistência:** a aparência vai para `data/avatar_yuna.json`, sem modificar o banco SQLite, suas conversas ou as imagens originais de `assets/`. As expressões de alegria, irritação e chateação são representações visuais simuladas, não emoções reais. O caminhar é leve e possui períodos de descanso.

**Executar só a personagem:** use `iniciar_yuna_avatar.bat` para abrir apenas o avatar, sem chat. Para chat e avatar integrados, use `iniciar_yuna.bat` e o botão de mostrar. Não abra ambos ao mesmo tempo para evitar duplicar a personagem.

**Atualização no Windows:** feche a Yuna, faça backup de `data/` e preserve `assets/`. Baixe o ZIP novo do repositório e copie os arquivos `.py` (especialmente `avatar_state.py` e `yuna_avatar.py`), os `.bat` e o README. Abra `iniciar_yuna.bat` e confira **Yuna 0.19**. Não precisa de biblioteca Python nova se o menu profissional 0.18 já funciona.

**Futuro:** esta primeira etapa é uma personagem chibi vetorial funcional, não um rig 3D completo. Podemos evoluir para sprites em camadas e animações detalhadas, depois Godot + modelo VRM/3D mantendo cérebro local e memória.
