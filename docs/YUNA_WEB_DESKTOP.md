# Yuna 0.44 — mesma identidade visual no navegador e no Windows

## Ver a prévia web

- Link público de demonstração: https://raw.githack.com/SrHenriqueBR/Projeto-Yuna/main/docs/yuna-preview.html
- Código da prévia: `docs/yuna-preview.html`
- Retrato da personagem: `docs/yuna-portrait.webp` (ilustração original)
- Se você preferir usar offline, abra a página HTML a partir de uma cópia da pasta `docs` com a imagem ao lado. As animações básicas funcionam sem conexão e a síntese de voz depende das vozes do navegador.
- O link é servido por um visualizador de arquivos estáticos de terceiros, **não** por um servidor local da Yuna. O site não contém memória, arquivos de usuários ou tokens.

## Windows

1. Feche a Yuna e preserve em backup `data/` e `assets/` da instalação antiga.
2. Baixe a versão atual do GitHub e atualize **os arquivos Python e a pasta docs completa**, preservando `data/` e `assets/`. Não misture arquivos de versões.
3. Execute `iniciar_yuna.bat` normalmente.
4. A janela principal inclui, entre menu e conversa, o retrato anime compartilhado com a web, frases de reação e botões de humor.
5. O botão **▶ Ouvir a Yuna** utiliza a voz selecionada na interface principal; se a voz estiver desligada, não reproduz nada. A síntese Edge continua opt-in conforme as regras existentes.
6. O painel de personagem não ativa câmera, microfone, APIs, portas ou processos extras. Câmeras, segurança e vídeo continuam exigindo autorização explícita, como antes.

## Como funciona

- **Mesma arte, sem divergência de identidade:** navegador usa `./yuna-portrait.webp`; desktop lê `ROOT/docs/yuna-portrait.webp`.
- **Web:** avatar SVG de corpo inteiro com proporções mais humanas e traço anime, incluindo cabeça, cabelo, braços, cotovelos, mãos, pernas, joelhos, olhos e boca articulados; expressões e falas prontas. “Ver rosto” aproxima a personagem para conferir as expressões e retorna ao corpo inteiro. O botão de retrato mostra a ilustração de referência. A pausa interrompe os movimentos dos dois modos e os efeitos de fundo, e a preferência por movimento reduzido é respeitada ao abrir a página. Abas ocultas suspendem o ciclo de animação. No link público, a página demonstra as expressões. No modo local pelo launcher web, o painel conversa com o Ollama.
- **Voz na web:** o botão alterna entre ouvir e parar. Trocar a expressão interrompe a fala anterior; falhas ou ausência de início da voz geram um aviso sem apagar a legenda. A disponibilidade e o timbre dependem das vozes do navegador, e algumas podem precisar de internet.
- **Desktop:** pequena oscilação do retrato, botões de humor que também atualizam o `AvatarController` já existente, conversa e recursos locais preservados. Os botões não enviam mensagens ao modelo sem você pedir.
- **Fallback:** se o arquivo da arte estiver ausente ou seu Qt não conseguir decodificá-lo, os recursos da Yuna continuam disponíveis com a apresentação antiga.
- **Ainda não é uma personagem 3D de produção:** o retrato 2.5D não tem esqueleto, física de cabelo ou sincronização labial real. Essas características dependem de um VRM rigado no renderizador 3D opcional.

## Próximos refinamentos possíveis

- Exportar um VRM original com aparência correspondente e expressões próprias.
- Criar sprites separados de olhos e boca se a prioridade for Live2D, com animações perceptíveis sem renderização 3D.
- Empacotar no futuro um instalador Windows, com testes de inicialização e áudio em hardware real.

Nenhuma informação pessoal é publicada pela página de demonstração. Não adicione `data/`, credenciais ou vídeos privados ao GitHub.

## Verificar os controles web

Execute `python -m unittest discover -s tests -p test_yuna_live_web.py -v` e `node --test tests/yuna_web_controls.test.cjs`. Os testes de JavaScript simulam a animação e as respostas do serviço de voz, incluindo pausa, alternância de modo, aba oculta e eventos atrasados de áudio. Confira também o layout no navegador em tela estreita e o áudio no dispositivo de destino.



## Chat local e novas reações

Abra `iniciar_yuna_web.bat` com o Ollama em execução. O endereço local padrão é `http://127.0.0.1:8787/`. A primeira resposta pode demorar enquanto o modelo é carregado; o painel indica quando Yuna está pensando. Enter envia a mensagem; Shift+Enter adiciona uma linha. “Ler respostas em voz alta” é opcional, e “Parar voz” interrompe a leitura.

O chat reutiliza `data/yuna.db` e `data/conhecimentos.json`. Guarde essa pasta ao atualizar. O servidor serve apenas os arquivos da interface e as rotas de conversa; não publica a pasta `data`. Cada pergunta é processada de uma vez. O modelo do chat não executa programas nem pesquisa na web.

No link público não há um modelo de texto hospedado: os campos indicam como abrir a conversa local. A página pública não tenta descobrir servidores, modelos ou arquivos no computador do visitante. O serviço local não aceita chamadas de outras origens do navegador.

A animação ganhou saudação inicial, atenção durante a escrita, postura de pensamento e gestos ao responder, além de dança e riso selecionáveis. Os movimentos são visuais e não representam sentimentos reais. A voz do navegador pode depender de serviços de voz externos; a leitura vem desligada.

Testes: `python -m unittest discover -s tests -p test_yuna_web.py -v` e `node --test tests/yuna_web_controls.test.cjs tests/yuna_chat.test.cjs`. Os testes de respostas utilizam o modelo simulado; avalie a qualidade das respostas reais com o Ollama instalado no notebook.
