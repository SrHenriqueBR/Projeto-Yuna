# Yuna.app no Windows

## Atualizar e abrir

1. Na Yuna antiga, escolha **Sair da Yuna** no menu da bandeja. Antes desta atualização, fechar a janela já encerrava o programa.
2. Baixe o ZIP atual do repositório e extraia. Preserve a pasta **`data`** da sua instalação: ela contém conversas, preferências e conhecimentos. Atualize todos os arquivos do projeto, inclusive os novos `.py`, `.ps1` e `.bat`.
3. Abra **`configurar_yuna_app.bat`**. Ele cria **Yuna.app** na Área de Trabalho e no menu Iniciar. Você pode escolher iniciar junto com o Windows, somente na sua conta.
4. Abra **Yuna.app** ou **`iniciar_yuna.bat`**. O chat compacto usa o mesmo Ollama e banco da janela completa. O botão **↗** abre a interface completa.

Se faltarem as bibliotecas da interface, use `instalar_yuna.bat`. O Ollama e o modelo de conversa já precisam estar instalados/abertos para respostas livres. Saudações e comandos implementados não precisam de uma resposta do modelo.

**Yuna.app é o nome da janela, da bandeja e dos atalhos.** Esta distribuição continua sendo Python: o Gerenciador de Tarefas pode mostrar `pythonw.exe`, não um executável independente chamado Yuna.app. O atalho aponta para a pasta extraída; configure novamente se mover essa pasta.

## Segundo plano e chat compacto

- Fechar a janela recolhe a Yuna para a bandeja, quando ela estiver disponível. Clique no ícone **Y** para recuperar o chat; **Sair da Yuna** encerra o processo. Sem bandeja disponível, a janela completa continua como acesso ao aplicativo.
- `iniciar_yuna_segundo_plano.bat` abre na bandeja. Abrir outra vez ativa a instância existente da mesma conta.
- O chat aparece quando o Windows/Qt informa ausência de entrada ou saída de áudio, quando faltam as dependências de voz, ou quando a captura/reprodução falha. Alto-falantes também contam como saída; não é obrigatório usar fone. Nem todo botão físico de mute ou dispositivo silenciado pode ser detectado.
- Mensagens novas aparecem ao final da conversa, com rolagem automática. As respostas usam a voz selecionada na janela completa; a voz Windows local continua como padrão.
- As animações do painel completo pausam enquanto ele está escondido. O modo residente não fica enviando perguntas ao modelo sem uma mensagem sua. A escuta opcional consome CPU e RAM enquanto estiver ativa.

Para remover a inicialização automática, execute no PowerShell, na pasta do projeto:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\configurar_yuna_app.ps1 -RemoverInicializacao
```

## Voz e chamados

Use **`instalar_voz_yuna.bat`** para instalar `sounddevice` e `faster-whisper`. No menu **•••**, marque **Escutar “Olá Yuna” nesta sessão**. A primeira ativação pode baixar o modelo Whisper `base`; a transcrição é local, sem chave de API ou serviço pago. Não guarda gravações.

Esse modo precisa ser ativado novamente ao iniciar a Yuna. O indicador mostra quando o microfone está ativo. Diga a chamada e o pedido juntos, com uma breve pausa entre pedidos. A captura usa blocos curtos: ruído, frases cortadas entre blocos e potência do computador podem afetar a compreensão.

| Pedido | Comportamento |
| --- | --- |
| “Olá Yuna” | “Olá, Kaizen! Em que posso te ajudar hoje?” |
| “Yuna abra a Steam” | Solicita a abertura da Steam pelo Windows. |
| “Yuna desliga o computador” | Anuncia boa noite e inicia contagem de 30 segundos no chat. |
| “Yuna cancele o desligamento” | Cancela a contagem da Yuna. O botão no aviso também cancela. |
| “Yuna parar agora” ou botão **Parar** | Interrompe voz, desativa a escuta, revoga o jogo e cancela o desligamento pendente. |

A voz não autentica Kaizen: outras pessoas ou um áudio perto do microfone também podem chamar. A captura pausa durante a fala da Yuna e o processamento de uma resposta. Para cancelar imediatamente enquanto ela fala/pensa, use **Parar** ou o botão do desligamento. O botão **🎙** faz ditado pontual, que você revisa antes de enviar.

## Desligar e despertar

O desligamento tem espera **dentro da Yuna**, sem forçar o fechamento dos aplicativos. Ao chegar a zero, solicita `shutdown.exe /s /t 0`. Salve o trabalho antes; o Windows pode bloquear a solicitação por programas abertos. Sair da Yuna antes do fim cancela a contagem. Depois que o Windows inicia o desligamento, o cancelamento da Yuna já não controla essa operação.

Para solicitar uma tentativa de despertar, diga **“Yuna acorde o computador amanhã às 07:00”** ou use **`/despertar 07:00`**. A Yuna mostra data/hora e pede confirmação. Usa o relógio local do PC; sem data, escolhe a próxima ocorrência. Aceita até sete dias no futuro. Há apenas um horário por vez; um novo substitui o anterior.

- **`/despertar`** consulta a tarefa no Windows.
- **`/despertar cancelar`** remove a tarefa `Yuna.app - Despertar`.
- Mantenha a sessão do Windows conectada, o PC na tomada e deixe-o **suspenso ou hibernando**. O Agendador de Tarefas, os timers de ativação e o hardware precisam permitir o despertar. A tela pode continuar apagada ou bloqueada.
- **Não liga um computador totalmente desligado.** Para isso, seria necessário suporte/configuração específica de RTC/alarme na BIOS ou Wake-on-LAN com outro equipamento. A Yuna não muda sua BIOS nem contorna a tela de bloqueio.
- A tarefa de despertar é do Windows e permanece após sair da Yuna. O botão Parar cancela ações em execução; para remover esse horário persistente, use `/despertar cancelar`.

## Jogos e desempenho

No menu **••• → Configurar controle de jogo**, escolha o executável de um jogo individual/offline e autorize a sessão. A autorização dura cinco minutos, com até 120 comandos. Cada pedido aguarda três segundos para você voltar ao jogo. Antes de enviar uma tecla, confere janela, PID, executável e modificadores do teclado. Trocar o foco durante a ação interrompe e libera a tecla.

| Pedido | Tecla enviada por até 0,15 s |
| --- | --- |
| “Yuna no jogo avance / recue / esquerda / direita” | W / S / A / D |
| “Yuna no jogo pule” | Espaço |
| “Yuna no jogo interaja” | E |
| “Yuna no jogo agache” | C |
| “Yuna no jogo pause” | Esc |
| “Yuna no jogo olhe para a esquerda / direita” | Setas esquerda / direita |

Esses controles são simples e dependem do mapeamento de cada jogo. Não há navegação autônoma, leitura contínua de partidas ou garantia de compatibilidade. Jogos com privilégios diferentes, proteção contra inputs ou controles próprios podem recusar teclas; não há bypass de anti-cheat. Navegadores e ferramentas comuns do sistema não são aceitos como jogo. `/jogo parar` revoga a autorização.

**“Yuna otimize o computador”** ou **`/diagnostico`** consulta RAM e espaço dos discos e apresenta sugestões. **`/ajustes inicializacao`**, **`/ajustes armazenamento`**, **`/ajustes energia`** e **`/ajustes modo jogo`** abrem a página correspondente do Windows para você escolher as alterações. Não apaga arquivos nem muda drivers/registro/BIOS automaticamente. Para respostas mais curtas da própria Yuna: `/desempenho rapido`; para restaurar: `/desempenho equilibrado`.

Pedidos de operações bancárias e abertura de aplicativos bancários conhecidos são bloqueados. Isso é um limite dos comandos da Yuna, não um bloqueio de aplicativos ou sites de todo o Windows.

## Câmera e memória

**Abrir câmera** mantém a escolha de fonte e a autorização por sessão. A prévia e o indicador ficam visíveis. **Descrever este quadro • Ollama local** envia somente a imagem atual para um modelo de visão previamente instalado e configurado em `YUNA_VISION_MODEL`. Sem ele, a prévia continua funcionando e a Yuna explica a configuração necessária. Não há download automático de modelo de visão, gravação, envio de imagens à nuvem ou identificação de pessoas. Fechar a câmera descarta o quadro e ignora descrições tardias.

Texto digitado, chamados reconhecidos e respostas concluídas do desktop ficam no **`data/yuna.db`**, junto das conversas existentes. Comandos tratados na interface também entram no histórico. Preferências e fatos explícitos continuam usando o sistema de memória; anexos completos e gravações não são copiados automaticamente para ele. Faça backup da pasta `data` com a Yuna fechada. Esse banco fica no computador, não é publicado no GitHub.

Memória permite usar informações nas próximas conversas; não treina os pesos do modelo. Atualizações de código continuam no laboratório/Escola da Yuna, com testes e revisão. Um commit não garante uma melhora, e o aplicativo não substitui o próprio código em execução.

## Verificação

Os testes automatizados simulam desligamento, agendamento, microfone, câmera e teclado; cobrem negações, cancelamento, troca de foco, falhas, áudio atrasado e persistência. Os testes Qt constroem a interface real. O teste de instância única usa IPC real no Windows. Hardware de áudio, despertar físico e compatibilidade com jogos precisam ser verificados no computador onde a Yuna será usada.

Referências técnicas: [Qt — bandeja](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html), [Qt — dispositivos de áudio](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaDevices.html), [Windows — shutdown](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/shutdown), [Windows — WakeToRun](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-waketorun).
