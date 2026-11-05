# Instalar, atualizar e reparar a Yuna no Windows

[← Voltar ao LEIA-ME](../README.md) · [Índice dos guias](README.md)

Este é o passo a passo principal para **Windows 10/11 de 64 bits**.
Se o objetivo é somente conversar com a Yuna, **use o instalador**:
ele evita instalar Python e bibliotecas manualmente. O renderizador 3D
pode vir compilado, mas modelos VRM de terceiros não são incluídos.


## Passo a passo: instalar do zero

1. Abra a [versão mais recente do GitHub](https://github.com/SrHenriqueBR/Projeto-Yuna/releases/latest).
   Baixe **Yuna-Setup.exe** e **SHA256SUMS.txt** da **mesma release**.
   O arquivo pode ter algumas centenas de MB, pois inclui o runtime
   Python e dependências privadas.
2. Verifique o download: deixe os dois arquivos na pasta Downloads e
   abra o PowerShell nessa pasta. Execute:
   ```powershell
   (Get-FileHash .\Yuna-Setup.exe -Algorithm SHA256).Hash.ToLower()
   Get-Content .\SHA256SUMS.txt
   ```
   O hash longo deve corresponder ao valor listado no arquivo. Se não
   corresponder, **não execute o instalador** e baixe novamente.
3. Execute **Yuna-Setup.exe** somente após conferir origem e integridade.
   O projeto não possui assinatura de código comercial; o Windows pode
   avisar que o editor é desconhecido. Isso não confirma segurança:
   não desative o antivírus e não ignore uma divergência de hash.
4. Escolha se quer atalhos na Área de Trabalho e inicialização com o
   Windows. A instalação usa a sua conta, sem pedir acesso administrativo
   para o funcionamento normal.
5. Na tela de importação de memórias, **deixe em branco se nunca usou
   a Yuna**. Se já usa, selecione a pasta antiga que **contém**
   `data/`, mantendo a Yuna anterior fechada. O assistente preserva
   os dados antigos; não copia por cima de um destino já preenchido.
6. Abra o atalho **Yuna.app** no menu Iniciar ou na Área de Trabalho.
   É um atalho Windows para **Yuna.exe**; não é um aplicativo `.app`
   exclusivo do macOS.
7. No chat, clique em **••• → Central da Yuna → Preparação → Verificar
   instalação e Ollama**. Caso o Ollama esteja ausente, use **Instalar
   ou abrir o site do Ollama** (link oficial para Windows).
8. Instale e inicie o Ollama. Na Central, escolha e confirme a instalação
   de **qwen3.5:2b** (leve, indicado para testar com 8 GB de RAM),
   **qwen3.5:4b** (recomendado) ou **qwen3.5:9b** (avançado,
   exige RAM/VRAM adicional). Os Qwen2.5 anteriores continuam disponíveis
   em Compatibilidade. O download é separado e pode consumir vários GB.
   Não há API Qwen paga integrada à Yuna.
9. **Reinicie a Yuna** depois de escolher o modelo. Envie uma pergunta
   curta para conferir a resposta.
10. Para experimentar os recursos adicionais, use a própria Central.
    Microfone, câmera, alertas, controle de jogos e integrações externas
    têm opções e autorizações separadas.

### Como saber se a instalação funcionou

O chat da Yuna deve abrir sem pedir Python/Node.js. Em **Central →
Preparação**, o diagnóstico deve reconhecer o ambiente e o Ollama
instalado/aberto, e um modelo preparado deve responder a perguntas
em português. A personagem e os botões podem aparecer mesmo antes
da instalação do modelo: **interface funcionando não comprova que o
cérebro Ollama está funcionando**.

### Se você já tem Yuna em outro computador ou pasta

Feche a Yuna antiga, faça backup privado de **toda** a pasta `data/`
e use o campo de importação para indicar a pasta original. Não
mescle bancos `.db` manualmente nem exclua a origem até conferir
as memórias na nova instalação. Se a instalação antiga estiver fora
de `data/`, guarde separadamente seus modelos VRM, imagens e anexos
que desejar preservar.

## Modelos locais — sem cobranças por mensagens

Escolha o modelo na **Central → Preparação**. Qwen3.5 utiliza somente
`http://127.0.0.1:11434`, que é o Ollama rodando no próprio computador.
Não é necessário criar conta em qwen.ai, fornecer cartão, cadastrar API key
nem aceitar cobranças por tokens.

| Modelo | Para que serve | Download aproximado |
| --- | --- | --- |
| `qwen3.5:2b` | Mais leve, para 8 GB RAM | 2,7–3,1 GB |
| `qwen3.5:4b` | Recomendado para 16 GB RAM | 3,3–4,0 GB |
| `qwen3.5:9b` | Avançado, requer folga de memória | 6,6–7,6 GB |

Mesmo que o download caiba no disco, a memória para execução pode ser
maior. A escolha ocorre **somente após o download concluir**; não troca
automaticamente o modelo de instalações antigas. Para verificar a seleção,
digite `/modelo` no chat. Reinicie a Yuna para aplicar a mudança.

Leia [Modelos locais e custos](MODELOS_LOCAIS.md) para comparar
Ollama com APIs comerciais e encontrar as opções de segurança.

## Onde ficou cada recurso

| Central | Opções |
| --- | --- |
| Minha Yuna | Chat compacto/completo, personagem 2D, avatar 3D, chat web e segundo plano |
| Permissões | Escuta local, USB/energia, avisos falados, câmera, jogo e parada |
| Preparação | Diagnóstico, modelos Ollama, atalhos, início com Windows, pasta de memórias e atualização |
| Avançado | Autoteste, terminal, laboratório, revisão/restauração, gestão e interface clássica |

O app usa as autorizações que já existiam: câmera e microfone são por sessão;
jogos exigem escolha explícita. Instalar não autoriza esses recursos automaticamente.
O botão Parar continua acessível. Não há uma permissão genérica de controle total.

As ferramentas avançadas abrem uma janela própria com andamento e instruções.
O chat web e o servidor 3D permanecem ativos enquanto suas janelas estiverem abertas.
Após abrir o 3D, use **Conectar Yuna 3D** na janela completa para vincular animação e voz.
Modelos VRM pessoais e o projeto Unreal continuam opcionais e não são baixados.

## Memórias, atualização e desinstalação

A pasta padrão de dados do app instalado é
`%LOCALAPPDATA%\Programs\Yuna\app\data`. Use **Preparação → Abrir pasta das memórias**.
Feche a Yuna antes de fazer backup manual. Para atualizar ou reparar, execute o
instalador novo no mesmo local. Ele substitui os arquivos do programa, preservando
`data`. Pelo Windows, **Aplicativos instalados → Yuna → Desinstalar** remove o app e
seus atalhos; dados pessoais permanecem na pasta para permitir recuperação.

Na importação, não mesclamos bancos. Se o destino já tem dados, ele permanece
intacto e o instalador informa que a importação não foi concluída. Avatares pessoais
fora de `data` continuam na instalação anterior; faça backup deles separadamente.

## Usar a Yuna perto do relógio

Depois de instalar a versão 0.53.0, procure o ícone **Y** na bandeja do
Windows (seta **˄** ao lado do relógio). Clique esquerdo para abrir o
chat compacto ou direito para abrir o menu de estados:
**Ativa**, **Econômica**, **Acompanhamento leve** e **Pausada**.
Fechar a janela normalmente entra em modo econômico em vez de
encerrar a Yuna. Clique em **Sair da Yuna** para desligar o processo.

O acompanhamento leve observa apenas USB/energia e bateria locais,
mediante seleção explícita. Escuta e câmera não são ativadas por esse
modo. [Controle e detalhes](YUNA_APP.md).

## Problemas frequentes

| Situação | O que verificar |
| --- | --- |
| **O chat abre, mas a Yuna não responde** | Abra **Central → Preparação → Verificar instalação e Ollama**. Confira se Ollama está rodando e o modelo escolhido terminou de baixar. Reinicie a Yuna após trocar o modelo. |
| **Aparece pedido de Python ou janela do terminal** | Você possivelmente abriu o ZIP do código-fonte. Para usar sem Python, baixe **Yuna-Setup.exe** nas Releases. |
| **`Yuna.bat` não abre ou fecha** | Use o instalador pronto ou execute o BAT a partir de uma pasta extraída, com Python 3 x64 e internet para configurar `.venv`. O launcher pode registrar detalhes em `data/yuna_startup_error.txt`. |
| **Python instalado, mas alguma biblioteca falha** | Não misture `.venv` antiga com outra versão do Python. Faça backup de `data/` e prepare o ambiente da cópia atual. |
| **A câmera ou microfone não funciona** | Esses recursos exigem hardware, permissão do Windows e ativação explícita dentro da Yuna; não são ligados só pela instalação. |
| **Avatar 3D mostra um modelo simples** | É a prévia geométrica; o visual anime completo requer importar um VRM próprio com esqueleto, de acordo com [o guia de avatar](COMO_CRIAR_YUNA_ANIME.md). |
| **Unreal Engine não abriu** | É um módulo experimental separado. Precisa do editor, SDK de C++, projeto compilado e modelo rigado. Veja [Yuna Unreal](../unreal/README.md). |
| **Atualização aparentemente apagou a memória** | Não reinstale repetidamente: confira a pasta de dados aberta pela Central e se a importação foi concluída. A instalação não deve sobrescrever um banco existente. |
| **Windows bloqueia o executável** | Confirme que o arquivo veio das Releases oficiais e valide seu SHA-256. Não desligue o antivírus nem execute se houver divergência. |

## Método alternativo: código-fonte

O caminho de desenvolvimento é diferente do instalador:

1. Baixe o ZIP pelo botão **Code → Download ZIP** e extraia a
   pasta completa.
2. Instale um Python 3 **x64** com `venv` disponível. O ambiente de
   distribuição testado nesta versão utiliza Python **3.14.10**; usar
   outras versões pode exigir validação de compatibilidade das bibliotecas.
3. Dê dois cliques em **Yuna.bat**. O script
   `scripts/iniciar.ps1` oferece criar um ambiente privado `.venv`.
   Confirme se deseja baixar as bibliotecas; isso exige internet.
4. Aguarde a preparação local e abra a Yuna. Prepare o Ollama em
   **Central → Preparação** conforme o passo a passo anterior.
5. Se desejar compilar o renderizador 3D do código-fonte, instale
   Node.js 22, abra um terminal na pasta `avatar3d/` e execute:
   ```powershell
   npm install
   npm test
   npm run build
   ```

O instalador **não exige** esses comandos. Para manter o projeto,
consulte [a estrutura de pastas](ESTRUTURA_DO_PROJETO.md).

Ao atualizar uma pasta antiga por ZIP, inicializadores legados
**conhecidos pelo programa** são movidos para
`data/inicializadores-antigos` sem eliminar os dados da instalação.
Cópias personalizadas com outros nomes não são apagadas automaticamente.

## Empacotamento e testes

O workflow **Instalador Windows da Yuna** monta o app com Python embeddable oficial
(versão e SHA-256 fixos), dependências em diretório privado, launcher `Yuna.exe` e
Inno Setup. Executa a suíte no runtime distribuído e testa instalação silenciosa,
abertura da interface, importação, atualização e desinstalação preservando dados.
Só então publica `Yuna-Setup.exe` e sua soma SHA-256 em Releases.

Uma release existente nunca é sobrescrita pelo workflow: aumente `VERSION` em
`self_model.py` para publicar outra. Builds de uma versão já publicada ficam nos
artefatos do workflow. Microfone, câmera, carregadores e jogos reais ainda precisam
de verificação na máquina em que a Yuna será usada.
