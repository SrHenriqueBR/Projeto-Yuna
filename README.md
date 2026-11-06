<p align="center">
  <img src="docs/yuna-portrait.webp" width="280" alt="Retrato de referência da Yuna: personagem anime de cabelo escuro e olhos violetas">
</p>

<h1 align="center">Yuna — Assistente pessoal de IA para Windows</h1>

<p align="center">
  <strong>Assistente local • Conversa em português • Memória • Voz • Avatar anime • Automação autorizada</strong>
</p>

<p align="center">
  <a href="https://github.com/SrHenriqueBR/Projeto-Yuna/releases/latest/download/Yuna-Setup.exe"><strong>⬇ Baixar Yuna para Windows</strong></a>
  · <a href="docs/INSTALACAO_WINDOWS.md">Guia de instalação</a>
  · <a href="https://raw.githack.com/SrHenriqueBR/Projeto-Yuna/main/docs/yuna-preview.html">Prévia anime na web</a>
  · <a href="https://raw.githack.com/SrHenriqueBR/Projeto-Yuna/main/docs/yuna-3d-viva.html">Prévia 3D na web</a>
</p>

> **Versão do código:** 0.54.1 · **Plataforma principal:** Windows 10/11 x64 · **Qwen recomendado:** Ollama local + `qwen3.5:4b` (escolha manual). O modelo legado `qwen2.5:3b` continua ativo até você trocar.
> O instalador é distribuído sem assinatura digital comercial. Verifique a origem e o SHA-256 antes de executar.

**Revisão 0.54.1:** correções no botão Parar, análise de documentos após cancelamento,
respostas do Qwen3.5, migração dos índices SQLite e acentos nos eventos do Windows.
Veja os [detalhes da revisão e seus limites](docs/REVISAO_0541.md).

## A proposta da Yuna

A Yuna é um projeto de **assistente de IA instalado no computador**, com uma personagem anime como interface. O objetivo é manter a conversa, os arquivos, a memória e os modelos de texto **sob controle do usuário**, usando ferramentas locais e exigindo autorização para ações sensíveis.

A imagem no início deste LEIA-ME é **o retrato de referência visual oficial da personagem**. A mascote 2D, a prévia 3D geométrica e os futuros modelos VRM/Unreal ainda não reproduzem necessariamente essa ilustração com fidelidade total. Uma foto animada não substitui uma malha 3D articulada.

**Escopo atual do projeto:**

- Conversar em português com **Ollama local, sem API paga**, com Qwen3.5 2B (leve), 4B (recomendado) ou 9B (avançado), escolhidos manualmente. Qwen2.5 permanece para compatibilidade.
- Usar **memória SQLite** e preferências locais, com comandos explícitos para lembrar e consultar informações.
- Oferecer chat compacto, janela completa, mascote flutuante, voz local e um painel Central da Yuna.
- Analisar documentos e realizar **somente as ações de PC implementadas e permitidas**, por exemplo abrir pastas ou programas.
- Experimentar a personagem em **2D**, **3D/VRM com Three.js** e **Unreal Engine 5 em C++** (este último é experimental).
- Permitir recursos opcionais de câmera, microfone, jogos e alertas **com consentimento específico**, nunca como acesso oculto ou irrestrito.

A Yuna não é uma IA consciente nem tem acesso universal ao computador. Nem toda ação solicitada é implementada, e o sistema não deve ser usado como mecanismo de vigilância de outras pessoas.

## Instalação rápida — recomendada

**Você não precisa instalar Python ou Node.js separadamente para usar o instalador Windows.** O Ollama e seu modelo de linguagem são preparados à parte.

1. Acesse [Releases](https://github.com/SrHenriqueBR/Projeto-Yuna/releases/latest) e baixe **`Yuna-Setup.exe`**. Há também um arquivo `SHA256SUMS.txt` para conferir a integridade. **Não baixe de sites não oficiais.**
2. Feche a Yuna se ela já estiver aberta. Para atualizar, faça antes uma cópia privada da pasta `data` com a aplicação fechada.
3. Execute o instalador, escolha os atalhos e, se for sua primeira migração, indique **a pasta antiga que contém `data`** no assistente. Não selecione o arquivo `yuna.db` isoladamente.
4. Abra o atalho **Yuna.app** (ele inicia o aplicativo Windows **Yuna.exe**).
5. No chat, clique em **••• → Central da Yuna → Preparação → Verificar instalação e Ollama**.
6. Se ainda não tiver Ollama, use **Instalar ou abrir o site do Ollama**. Instale-o e volte à Central. Escolha **Qwen3.5 2B** (PC com 8 GB), **Qwen3.5 4B** (recomendado) ou **Qwen3.5 9B** (avançado, exige mais memória). Confirme o download. Os modelos anteriores Qwen2.5 continuam disponíveis.
7. **Reinicie a Yuna após escolher o modelo** e faça uma pergunta no chat. Se não houver resposta da IA, confira na Central se o Ollama está aberto e o modelo foi instalado.

**Guia com imagens/fluxos, atualização, preservação de memória e erros comuns:** [Instalação no Windows](docs/INSTALACAO_WINDOWS.md).

### Alternativa — executar pelo código-fonte

Para desenvolver ou testar uma cópia do GitHub:

1. Baixe o código pelo botão **Code → Download ZIP** e extraia em uma pasta sua.
2. Instale um **Python 3 de 64 bits compatível** com as dependências do projeto, com o `venv` disponível. No Windows, o comando `py` ajuda a localizar o Python.
3. Execute **`Yuna.bat`**, a **única entrada BAT mantida na raiz**. Ele chama `scripts/iniciar.ps1`, solicita confirmação e cria o ambiente `.venv` com as bibliotecas Python necessárias.
4. Abra e configure o **Ollama** conforme os passos 5–7 acima.

Ao usar o código-fonte, o renderizador 3D pode precisar de Node.js para compilar: em `avatar3d/`, execute `npm install` e `npm run build`. Esses comandos **não são necessários** para o instalador pronto.

**Importante:** não substitua somente um arquivo `.py` de uma versão por outro de versão diferente. Atualize a pasta de código e preserve seus dados pessoais. Para detalhes: [Instalação Windows](docs/INSTALACAO_WINDOWS.md).

## Yuna presente na bandeja do Windows (versão 0.53.0)

Ao abrir a Yuna, um ícone **Y** aparece na área de notificação do Windows,
perto do relógio (clique na seta **˄** caso esteja oculto). **Clique esquerdo**
abre o chat compacto; **clique direito** abre a Central, ferramentas
autorizadas e o menu **Modo de funcionamento**.

| Modo | Comportamento real |
| --- | --- |
| **● Ativa** | Conversa normal, voz somente com consentimento; USB/energia se a autorização estiver marcada. |
| **◐ Econômica** | Continua aberta no ícone e pronta para chat; interrompe escuta contínua, suspende monitor USB, reduz verificações da bateria e interrompe animações opcionais. Fechar a janela muda automaticamente para este modo. |
| **◇ Acompanhamento leve** | Após seleção explícita, acompanha USB/energia e bateria **deste computador**; verifica RAM e espaço livre em disco a cada 5 minutos e orienta somente se houver pressão persistente. Não ativa microfone, câmera ou IA automática. |
| **Ⅱ Pausada** | Pede para cancelar tarefas em andamento, escuta e monitoramento; reabrir o chat retoma o modo ativo. |
| **Sair da Yuna** | Encerra o processo; o ícone desaparece. |

O **pontinho no ícone** indica o estado: roxo = ativa, cinza = economia,
verde = acompanhamento, âmbar = pausada, azul = escuta autorizada.
Esses estados indicam atividade **local**, não conexão à internet nem
monitoramento de outras pessoas.

No modo econômico a CPU pode ser poupada por menos verificações
(200 ms → 1200 ms no timer de interface; bateria 90 s → 5 min),
mas o **Ollama é um processo separado** e pode continuar com um
modelo carregado na memória. A Yuna não encerra o Ollama
silenciosamente. No modo acompanhamento, USB/energia usa eventos do Windows com consulta
de confirmação; a bateria é verificada a cada 3 minutos, e RAM/espaço
livre do disco a cada 5 minutos. A Yuna oferece orientações com avisos
limitados por intervalo, sem acessar nomes de processos ou arquivos.
Não existe leitura oculta de tela, câmera ou envio desses dados. [Guia e permissões](docs/YUNA_APP.md).

## Yuna 0.54 — novas integrações locais e ferramentas de segurança

Na **Central da Yuna → Integrações** há quatro recursos opcionais,
acionados por botões com confirmação quando a ação modifica o estado:

| Recurso | O que realiza | Dados e custo |
| --- | --- | --- |
| **RAG / EmbeddingGemma** | Pesquisa semântica por trechos **dos documentos guardados manualmente na biblioteca**, indexados individualmente | Embeddings enviados **somente ao Ollama local**; cópia de índice em `data/yuna_rag.sqlite`; **sem API paga** |
| **Gerenciar memória do Ollama** | Lista modelos carregados em RAM/VRAM e permite descarregar um modelo escolhido | `/api/ps` e `/api/generate` somente em `127.0.0.1`; **não desinstala modelos** |
| **Eventos do Windows** | Mostra data, código, nível e origem de alertas/erros do sistema ou aplicativos nas últimas 24 horas | Leitura local via PowerShell, **sem mensagens privadas** e sem aplicar reparos |
| **OSV.dev** | Consulta vulnerabilidades conhecidas de um pacote **PyPI/npm** com versão exata | **API pública externa**, sem chave ou cobrança; envia apenas ecossistema, nome e versão escolhidos |

A indexação exige uma etapa separada para baixar `embeddinggemma`
(~622 MB) do Ollama, após confirmação. Ela **não varre o computador**
nem indexa automaticamente novas memórias, chats ou arquivos. A busca
mostra trechos e referências, **não executa instruções contidas neles**.
Se preferir, o botão **Apagar índice** remove somente a base semântica;
`data/yuna.db` e os documentos originais permanecem.

O modo econômico da bandeja **não encerra o Ollama automaticamente**.
Agora é possível liberar o modelo carregado manualmente; isso pode
afetar uma conversa em andamento, por isso a Central pede confirmação.

O OSV não fornece garantia de ausência de vulnerabilidades e não
atualiza dependências sozinho. **Nenhuma integração Qwen API paga
foi adicionada.** Leia o [guia de integrações 0.54](docs/INTEGRACOES_054.md).

## IA gratuita: Qwen3.5 pelo Ollama local

**Esta integração não exige a plataforma comercial Qwen API, cadastro, cartão, tokens de nuvem nem assinatura.** O Ollama executa o modelo no **seu próprio PC**, usando RAM/VRAM. A primeira instalação baixa o arquivo do modelo; pode consumir internet, armazenamento e energia elétrica. Depois de baixado, o texto pode ser processado offline.

| Modelo | Indicação | Tamanho aproximado do download |
| --- | --- | --- |
| `qwen3.5:2b` | Notebook com 8 GB de RAM, modo leve | 2,7–3,1 GB |
| `qwen3.5:4b` | **Recomendado** para 16 GB RAM + boa GPU | 3,3–4,0 GB |
| `qwen3.5:9b` | Avançado, somente se houver RAM/VRAM livre suficiente | 6,6–7,6 GB |
| `qwen2.5:1.5b` / `qwen2.5:3b` | Compatibilidade com instalações antigas | Mantidos |

Os tamanhos são do catálogo do Ollama; a **memória necessária durante a execução pode ser maior**, sobretudo com contexto longo, visão, voz e outras funções abertas. A GPU de 8 GB pode não acomodar `9b` e contexto grande completamente na VRAM; nesse caso o desempenho pode cair.

**Trocar com segurança:** abra **••• → Central da Yuna → Preparação**, clique no modelo, confirme o download e reinicie a Yuna. O modelo anterior continua selecionado se a transferência falhar. **Não há alteração automática, cobrança após várias conversas ou acesso secreto a APIs pagas.** Suas memórias SQLite não são apagadas.

**API Qwen na nuvem é outra coisa:** é cobrada por tokens consumidos e pode iniciar faturamento após acabar a cota gratuita, se o serviço estiver habilitado para pagamento. **A Yuna 0.53.0 não integra essa API.** Consulte [o guia de modelos locais](docs/MODELOS_LOCAIS.md).

## O que já funciona e o que é experimental

| Área | Situação |
| --- | --- |
| Chat, memória e Ollama | Funcional no ambiente local, com modelo instalado e em execução |
| Chat compacto / Central da Yuna | Aplicativo Windows e menus de preparação |
| Presença na bandeja / economia | Quatro modos locais, avisos autorizados e redução de verificações |
| Documentos, comandos do PC e ações | Suporte aos formatos e comandos implementados, mediante solicitação |
| Voz, USB/energia, câmera e jogos | Recursos específicos, dependentes de hardware e/ou autorização |
| Avatar 2D | Interface interativa e personalizável |
| Avatar 3D/VRM | Renderizador opcional; requer modelo VRM próprio para visual anime completo |
| Unreal Engine / C++ | Estrutura experimental; exige Unreal, compilação e rig/animador |
| Demonstrações web públicas | Prévia visual sem acesso ao modelo Ollama, às memórias ou ao PC |

**Não estão incluídos:** consciência artificial; controle irrestrito do sistema; acesso remoto oculto à câmera/microfone; personagem 3D profissional pronta e distribuída com licença; transmissão Unreal Pixel Streaming; reconhecimento exclusivo de voz como forma de autenticação.

## Onde ficam os dados e como manter a segurança

A memória principal é `data/yuna.db`, complementada por outros dados e preferências em `data/`. No instalador, o caminho padrão é:

```text
%LOCALAPPDATA%\Programs\Yuna\app\data
```

Feche a Yuna antes de copiar essa pasta. Atualizações e desinstalação foram projetadas para preservar os dados pessoais, mas mantenha seu próprio backup. **Nunca publique `data/`, tokens, senhas, gravações, modelos privados ou arquivos de terceiros no GitHub.**

Câmera, escuta e controle de jogos permanecem condicionados a opções e autorizações próprias. A página pública de demonstração não acessa câmera, microfone, arquivos locais nem conversa com o Ollama.

## Estrutura do repositório

```text
Projeto-Yuna/
├── Yuna.bat                  # Único iniciador da cópia do código
├── yuna_launcher.py          # Inicialização da interface e erros
├── yuna_desktop.py           # Janela completa e integrações
├── yuna_overlay.py           # Mascote/overlay Windows
├── yuna.py                   # Núcleo e conversação
├── app_center.py             # Central de recursos e configuração
├── avatar3d/                 # Renderizador Three.js / VRM opcional
├── unreal/                   # Experimentos Unreal Engine / C++
├── docs/                     # Guias, retrato oficial e prévias web
├── packaging/                # Empacotamento e instalador Windows
├── scripts/                  # Inicialização PowerShell e ferramentas
├── tests/                    # Testes automatizados
├── aprendizado/              # Escola da Yuna / aprendizado revisado
└── data/                     # Dados privados locais (IGNORADOS pelo Git)
```

Os módulos Python permanecem na raiz **de propósito**, porque vários imports e pontos de entrada dependem desses caminhos. Mover tudo para novas pastas sem refatorar os imports e testes quebraria a Yuna. O restante está separado por finalidade.

## Guias e recursos

| Quero... | Onde encontrar |
| --- | --- |
| Instalar, atualizar ou reparar | [Instalação no Windows](docs/INSTALACAO_WINDOWS.md) |
| Entender menus, permissões e voz | [Yuna.app no Windows](docs/YUNA_APP.md) |
| Navegar pelos arquivos e módulos | [Mapa do repositório](docs/ESTRUTURA_DO_PROJETO.md) |
| Encontrar documentação por assunto | [Índice de documentação](docs/README.md) |
| Ler todas as funções e comandos | [Guia completo (referência)](docs/GUIA_COMPLETO.md) |
| Criar o avatar anime VRM | [Criar Yuna Anime](docs/COMO_CRIAR_YUNA_ANIME.md) |
| Configurar o experimento Unreal | [Yuna Unreal](unreal/README.md) |
| Desenvolver o renderizador 3D | [Avatar Three.js / VRM](avatar3d/README.md) |
| Conhecer os testes e as releases | [Workflow do instalador](.github/workflows/instalador-windows.yml) |

## Desenvolvimento e contribuições

Os testes estão em `tests/`, `avatar3d/tests/` e `unreal/tests/`, com fluxos automatizados em `.github/workflows/`. Alterações no projeto devem incluir testes proporcionais ao risco e, quando necessário, uma validação no Windows real. Para melhorias de código, prefira Pull Requests revisáveis e mantenha a pasta `data/` fora de qualquer commit.

**Repositório:** [SrHenriqueBR/Projeto-Yuna](https://github.com/SrHenriqueBR/Projeto-Yuna) · **Licenças:** confira as condições dos componentes e modelos de terceiros antes de redistribuir a Yuna, seus avatares ou uma build com Unreal Engine.
