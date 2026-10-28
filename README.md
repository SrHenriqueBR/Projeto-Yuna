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
