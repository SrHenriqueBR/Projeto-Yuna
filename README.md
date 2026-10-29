# Projeto Yuna — versão 0.26

Assistente pessoal local para **Windows 10/11**, com conversa em português, memória SQLite, interface gráfica, leitura de documentos, acesso limitado a ferramentas do computador e avatar chibi **2D**. O modelo de texto padrão é **Ollama + qwen2.5:3b**. O computador precisa permanecer ligado enquanto a Yuna funciona.

A Yuna **não é uma IA consciente nem um agente com controle irrestrito**. Executa apenas as ações implementadas e permitidas pelo programa.

## Instalação em outro Windows — assistente 0.26

1. Instale o **Python 3.11 ou 3.12 de 64 bits** com o **Python Launcher**: https://www.python.org/downloads/windows/
2. Instale e abra o **Ollama**: https://ollama.com/download/windows
3. No GitHub, use **Code → Download ZIP**, extraia e execute **`instalar_yuna.bat`** com dois cliques, **sem abrir como administrador**.
4. Siga o assistente. Ele verifica Python, bibliotecas, Ollama e memória RAM, pergunta antes de instalar pacotes ou baixar modelos, permite criar um atalho e pode iniciar a Yuna.
5. Depois use **`iniciar_yuna.bat`** normalmente; a conversa ocorre na janela **Conversa com a Yuna** e o avatar é opcional.

O assistente é um **script de instalação guiada (.bat + PowerShell)**, ainda **não um instalador .exe ou MSI**. Não instala Python ou Ollama automaticamente nem exige elevação. Se faltar algum dos dois, mostra o endereço oficial e orienta a instalação. Pacotes Python são baixados do índice configurado no seu pip, somente após autorização. O download do modelo é feito pelo próprio Ollama, também com confirmação.

### Computador com 8 GB de RAM

O instalador recomenda **`qwen2.5:1.5b`** para até 8 GB, mas você pode manter **`qwen2.5:3b`** se preferir melhor capacidade e aceitar mais uso de memória. O programa salva apenas essa escolha em **`data/modelo_yuna.txt`**, sem apagar o banco SQLite. Usuários avançados podem continuar definindo a variável **`YUNA_MODEL`**, que tem prioridade. Em instalações antigas, sem essa escolha, o padrão continua 3B.

Para descobrir o que falta sem baixar nada, execute **`diagnosticar_yuna.bat`**. O diagnóstico consulta o ambiente e não instala bibliotecas, modelos ou atalhos.

### Instalação manual (alternativa)

Abra PowerShell **na pasta extraída**, não em `C:\Windows\System32`:

~~~powershell
py -3 -m pip install -r requirements-mascote.txt
ollama pull qwen2.5:3b
~~~

Se o Ollama não responder, abra o aplicativo; se necessário, execute **`ollama serve`** em outro terminal. Para testar isoladamente: **`ollama run qwen2.5:3b`**. Se aparecer `py não reconhecido`, reinstale o Python com Python Launcher e abra um novo terminal.

## Como atualizar sem perder as memórias

1. Feche todas as janelas da Yuna e copie sua pasta **data/** para um backup privado.
2. Baixe e extraia a nova versão em outra pasta.
3. Atualize **todos os arquivos .py**, os arquivos .bat, o novo **instalar_yuna.ps1** e os arquivos requirements da instalação antiga. Não copie uma seleção de módulos de versões diferentes.
4. **Preserve data/ e assets/** da sua instalação; não as substitua pelo ZIP. Reabra **iniciar_yuna.bat**.

A memória principal fica em **data/yuna.db**, e as preferências visuais ficam em **data/avatar_yuna.json**. A cópia **data/conhecimentos.json** não substitui o banco SQLite. **Não envie data/ para GitHub.**

## Entradas oficiais

| Arquivo | Quando usar |
| --- | --- |
| **instalar_yuna.bat** | Instalação assistida com diagnóstico, escolha de modelo e criação opcional de atalho |
| **diagnosticar_yuna.bat** | Diagnóstico somente leitura, sem baixar nada |
| **iniciar_yuna.bat** | **Padrão:** janela de conversa, biblioteca de documentos, voz e avatar 2D opcional |
| **iniciar_yuna_mascote.bat** | Interface flutuante legada com funcionalidades específicas (diário, criação de arquivos, iniciativas e provedores opcionais) |
| **iniciar_yuna_terminal.bat** | Modo de texto para diagnóstico, especialmente quando a interface gráfica falhar |

O desenho **yuna_avatar.py** é um componente da interface principal: não é uma janela independente de conversa. Os modos acima compartilham módulos e dados; **não remova yuna_overlay.py, yuna.py ou os módulos de apoio** ao atualizar.

Para mudar de modelo de texto, use uma variável de ambiente **YUNA_MODEL** e tenha o modelo instalado no Ollama. Um modelo 7B é opcional e consome mais RAM; não faz parte do requisito da Yuna.

## Conversa, comandos e memórias

A Yuna responde a pedidos comuns, por exemplo:

~~~text
Oi Yuna, o que vamos fazer hoje?
Yuna, abra o Discord
Yuna, abra a pasta Downloads
Yuna, procure meu currículo
Yuna, lembra que eu prefiro respostas objetivas
O que você lembra de mim?
~~~

Atalhos úteis para terminal e diagnóstico:

| Comando | Função |
| --- | --- |
| **/ajuda** | Lista comandos disponíveis |
| **/apps**, **/apps atualizar** | Lista e atualiza aplicativos do menu Iniciar |
| **/abrir steam**, **/abrir downloads** | Abre aplicativo ou pasta permitida |
| **/buscar NOME**, **/buscar tudo NOME** | Busca nomes na pasta do usuário ou nos discos fixos |
| **/abrir 2**, **/localizar 2** | Abre um resultado permitido ou localiza sua pasta |
| **/sistema**, **/processos**, **/ambiente** | Consultas locais disponíveis, sem monitoramento contínuo |
| **/fazer PEDIDO** | Solicita interpretação estruturada por Ollama de uma ação suportada |
| **/lembrar TEXTO**, **/memorias**, **/esquecer ID** | Gerencia memórias explícitas |
| **/nova** | Limpa histórico de conversa, preservando memórias explícitas |
| **/apagar CONFIRMAR** | Exclui histórico e memórias mediante confirmação explícita |
| **/sair** | Fecha o modo terminal |

As buscas não garantem cobrir todos os discos ou documentos; não executam scripts encontrados. As memórias não treinam os pesos do modelo. O sistema tem filtros locais, mas não deve receber senhas, credenciais nem dados confidenciais de terceiros.

### Documentos

O **Yuna Desktop** permite anexar e analisar **DOCX, XLSX, PPTX, PDF, TXT e MD**. O original não é alterado. A cópia para **data/biblioteca** exige autorização. O modo de mascote legado inclui ferramentas adicionais de criação de arquivos. Nem todo pedido é executável: a Yuna informa quando uma ação não é suportada.

### Avatar 2D e aparência

O botão **Mostrar Yuna viva** abre a personagem flutuante. Clique com o botão direito para ajustar cores, penteado, roupa, acessórios, tamanho (75%, 100% e 130%), gestos e movimento. As preferências persistem em **data/avatar_yuna.json**.

Exemplos de pedidos: **Yuna, deixa o cabelo curto**, **Yuna, acena pra mim**, **Yuna, pisca pra mim**, **Yuna fica tímida**, **Yuna vai dormir**, **Yuna acorda**, **Yuna reduz as animações** e **Yuna retoma as animações**. As animações são expressões fictícias. A personagem ainda não possui modelo 3D, rigging, captura de movimento nem reconhecimento de emoções.

### Magi1020 — convite de vídeo entre dois notebooks

Ao digitar **`Magi1020`** na Yuna Desktop (ou clicar em **◈ Magi1020 • Vídeo remoto**), você pode criar e copiar um convite de videochamada, ou entrar com um convite recebido de outra pessoa.

**A câmera de outra pessoa não é ativada pelo comando**. A chamada acontece no navegador via **Jitsi Meet (serviço externo)** e quem transmite precisa entrar e autorizar sua webcam. A pessoa que inicia uma sala no serviço público pode precisar se autenticar. Os links são aleatórios por convite, mas **não possuem expiração garantida**: não publique nem reutilize convites. A Yuna não grava a chamada, não ativa câmeras escondidas, não transmite vídeo dentro da interface Python e não cria pareamento remoto automático.

O comando é apenas um **atalho de convite, nunca uma senha**. Para parar a transmissão, use **Sair** ou desligue a webcam no navegador. **Break080111 não encerra uma chamada Jitsi externa**. Guia detalhado: [`docs/MAGI1020_VIDEO_REMOTO.md`](docs/MAGI1020_VIDEO_REMOTO.md).

### Câmeras autorizadas — webcam e RTSP experimental

A Yuna Desktop pode agora abrir uma **prévia temporária** de uma webcam
local (índice `0`, `1` etc.) ou câmera RTSP da **rede local privada**
cujo acesso você esteja autorizado a utilizar. A função é opt-in:
clique em **◉ Ver câmera autorizada** ou peça **"Yuna, mostre a câmera"**
para abrir a seleção. É exigida uma confirmação antes de acessar a fonte.

Para instalar o decodificador opcional na mesma instalação Python da Yuna,
execute `py -3 -m pip install opencv-python`. Não há instalação,
ligação de câmera ou descoberta automática. O acesso termina em no máximo
5 minutos, ao fechar a janela ou quando você usa **Break080111** / **Parar**.

**Não é ainda vigilância com alertas:** não há gravação, monitoramento
contínuo, reconhecimento facial, identificação de pessoas nem envio
de imagens ao Ollama/nuvem. URLs RTSP/credenciais nunca são salvas;
a URL completa fica visível enquanto digitada na caixa inicial. Consulte
[`docs/CAMERAS_YUNA.md`](docs/CAMERAS_YUNA.md) para configurar e
entender as limitações do piloto.

### Jogar junto com a Yuna — em preparação

O primeiro módulo `game_sessions.py` **não manipula nenhum jogo**:
é um contrato de autorização para futuros controles. Ele permite somente
sessão individual/offline aprovada, executável local conhecido, comandos
curtos, prazo limitado e interrupção por `Break080111` ou pelo botão Parar.

**Ainda não há visão de jogo nem controle de teclado/gamepad instalado.**
Ações propostas no módulo não são executadas; também não existe
compatibilidade comprovada com The Last of Us. Próxima etapa: piloto
supervisionado com captura consentida somente da janela selecionada,
reconhecimento visual local e adaptador de controles com verificação real
do processo em foco. Consulte
[`docs/PLANO_JOGOS_COM_YUNA.md`](docs/PLANO_JOGOS_COM_YUNA.md).

### Energia ilustrativa da Yuna (bateria do notebook)

Em notebooks Windows com sensor válido, a Yuna consulta **apenas a porcentagem
da bateria e se o carregador está conectado** pela API do Windows. A consulta
é local, leve e sem instalação adicional; em desktops sem bateria ou em
sensores indisponíveis ela **não inventa percentuais nem faz alertas**.

- **Até 35% sem carregador:** prefere ficar sentada e descansando.
- **Até 20% sem carregador:** mostra sono, reduz FPS para no máximo 12 e
  caminha lentamente até a lateral direita da tela, junto ao seu indicador
  virtual de energia (não detecta a tomada física).
- **Até 10% sem carregador:** pede conexão ao carregador com um alerta mais urgente.
- **Carregando:** relaxa e mostra a condição de carga.
- **100% de carga:** comemora e sugere uma atividade, **sem abrir nem controlar
  aplicativos automaticamente**.

O avatar 2D mostra um pequeno indicador e balões ocasionais; a Yuna
Desktop também comunica a mudança no chat, sem ligar TTS por conta própria.
Se o 3D estiver explicitamente conectado, a ponte transmite apenas carga,
estado AC e categoria visual. O monitoramento é consultado em intervalos
de 90 segundos — **não é uma leitura instantânea contínua**.
Gestos explícitos, voz em andamento e movimento reduzido têm prioridade
sobre a animação automática.

**Jogar de verdade em games de terceiros ainda não foi implementado.**
Automação de controles, compreensão visual e compatibilidade com jogos
precisam de autorização específica por sessão, mecanismo de parada e
testes offline antes de manipular teclado ou gamepad.

### Avatar 3D VRM experimental (opcional)

A versão 2D continua como padrão. Para testar o protótipo **3D opcional**
(com movimentos leves de cabeça, olhos, respiração, expressões e gestos),
instale **Node.js 22 LTS**, entre em `avatar3d/` e execute `npm install`.
Depois execute `iniciar_yuna_3d.bat` na raiz ou `npm run dev`
na pasta `avatar3d`, e abra `http://127.0.0.1:5173`.

Depois de iniciar o navegador 3D, clique em **◇ Conectar Yuna 3D** na Yuna Desktop para vincular a voz local (porta dinâmica e token de sessão). Essa ponte transmite somente movimentos, expressão e amplitude — **nunca conversas ou áudio bruto**. O link é opcional e fecha ao encerrar a janela.\n\nO protótipo inclui uma **personagem anime geométrica original e personalizável**.
No editor do navegador, altere cabelo, penteado, olhos, roupa, acessórios
e presets. Essas escolhas são guardadas localmente no navegador, sem
alterar VRMs importados. Com a ponte 3D ativada, comandos de visual
reconhecidos pela Yuna Desktop também atualizam essa prévia 3D.

O protótipo mostra uma prévia geométrica original enquanto não há modelo.
Importe **seu próprio arquivo .vrm**, com direitos de uso, para animar
uma personagem rigada. Ainda **não existe ligação** com a fala do
QMediaPlayer, com o cérebro Python/Ollama ou com o AvatarController.
O modo 3D não liga sozinho no Windows e não é instalado pelo assistente
padrão: preserve `data/` e `assets/` ao atualizar. Instruções e limites:
[`avatar3d/README.md`](avatar3d/README.md).

### Voz e boca animada (0.25)

A janela **Yuna Desktop** inicia com **Windows offline**, que exige uma voz feminina pt-BR instalada no próprio Windows. **▶ Testar voz** permite verificar a fala e o avatar.

A voz offline gera um **WAV temporário local**; a amplitude do áudio movimenta a boca enquanto a mídia está tocando. O movimento não corresponde a fonemas exatos. Se não existir uma voz compatível, uma mensagem de erro aparecerá na interface.

**Edge online** é opcional e **envia o texto falado ao serviço externo**, somente após consentimento. A boca acompanha o período de reprodução de maneira aproximada nesse modo. Para instalar:

~~~powershell
py -3 -m pip install edge-tts
~~~

Para ditado local **sob acionamento manual** do botão de microfone no Yuna Desktop:

~~~powershell
py -3 -m pip install -r requirements-voz.txt
~~~

O ditado usa dependências opcionais, pode baixar os pesos de reconhecimento na primeira utilização e não é escuta contínua. O modo de mascote legado possui integração adicional com ElevenLabs, **somente** mediante chave autorizada e possíveis custos; evite enviar conversas sensíveis a serviços de síntese online.

## Funções avançadas e serviços opcionais

Além das conversas locais, o modo de mascote/terminal mantém comandos como:

- **/clima CIDADE**, **/livros TEMA**, **/cep CEP**: consultas públicas sob pedido explícito.
- **/github**, **/github ler ARQUIVO**, **/melhorar ARQUIVO**: consulta de código público permitido e elaboração de **propostas locais**, sem executar nem publicar alterações automaticamente.
- **/ia gemini PERGUNTA**, **/ia groq PERGUNTA**, **/ia openrouter PERGUNTA**: provedores opcionais com chaves próprias. **/ias** consulta configuração.
- **/openai PERGUNTA**: API separada, somente com **OPENAI_API_KEY** e possíveis custos.
- **/tela**: descrição da tela **sob pedido explícito**, requer Pillow e um modelo visual local compatível.
- **Diário, curiosidade, propostas e iniciativa**: módulos locais disponíveis conforme a interface e configuração, sem autorização para alterar código ou arquivos arbitrários.

Serviços externos têm políticas, disponibilidade e limites próprios. Use variáveis de ambiente como **GEMINI_API_KEY**, **GROQ_API_KEY**, **OPENROUTER_API_KEY**, **OPENAI_API_KEY** ou **ELEVENLABS_API_KEY** só quando precisar, nunca como texto no repositório ou no banco.

## Evolução VTuber (planejamento)

Está disponível o [plano de arquitetura do avatar VTuber](docs/PLANO_AVATAR_VTUBER.md), baseado em estudo de AIRI, Open-LLM-VTuber, Xiaokeai, Soul-of-Waifu e alternativas de rigging 2D. O plano define a evolução do avatar 2D atual para uma personagem 2D em camadas e, opcionalmente, 3D/VRM, com voz e eventos sincronizados. **Esses renderizadores novos ainda não estão implementados.** O modo leve permanecerá disponível para máquinas de 8 GB.

## Estrutura do código

| Parte | Arquivos centrais |
| --- | --- |
| Modelo e memória | **yuna.py**, **initiative.py**, **natural_memory.py**, **self_model.py**, **affect.py**, **conversation_integrity.py** |
| Ferramentas locais e documentos | **computer.py**, **desktop.py**, **local_agent.py**, **agent_brain.py**, **office_agent.py**, **document_writer.py**, **document_library.py** |
| Interface principal | **yuna_launcher.py**, **yuna_desktop.py** |
| Avatar | **yuna_avatar.py**, **avatar_state.py**, **avatar_motion.py** |
| Voz | **voice.py**, **speech_input.py** |
| Mascote legada e funções extras | **yuna_overlay.py**, **diary.py**, **proactive.py**, **own_initiative.py**, **integrations.py**, **free_apis.py**, **web_actions.py** |
| Testes | **tests/** e **.github/workflows/testes.yml** |

Os outros módulos Python na raiz também são dependências de recursos existentes e permanecem no projeto. Os testes antigos protegem regressões: não são material descartável.

## Diagnóstico e desenvolvimento

No PowerShell aberto na pasta do projeto:

~~~powershell
py --version
py -3 -m pip install -r requirements-mascote.txt
py -3 -m unittest discover -s tests -v
~~~

Se **py** não for reconhecido, instale o Python com **Python Launcher**; não execute o instalador de dependências a partir de **C:\Windows\System32**. Se o menu não iniciar, confira **data/yuna_startup_error.txt**. Se o Ollama recusar conexão, verifique o serviço local e o modelo instalado. Se o avatar aparecer sem janela de conversa, execute **iniciar_yuna.bat**, não somente o módulo do avatar.

Os testes são executados no GitHub Actions com interface Qt offscreen. Eles não substituem o teste de áudio, placas de som, microfone e animações no Windows físico.

**Segurança:** a pasta **data/** não é criptografada; backups também devem ser privados. A Yuna não possui controle autônomo irrestrito do computador, não instala códigos criados pelo próprio modelo e não fica ativa com a máquina desligada.

**Histórico:** a evolução das versões 0.7–0.24 continua disponível no histórico de commits e pull requests do GitHub. Este README descreve a versão atual, evitando instruções contraditórias de lançamentos antigos.
