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
- **Web:** movimento leve de parallax e respiração visual, frases e variações de cor por humor. Não conversa com o Ollama.
- **Desktop:** pequena oscilação do retrato, botões de humor que também atualizam o `AvatarController` já existente, conversa e recursos locais preservados. Os botões não enviam mensagens ao modelo sem você pedir.
- **Fallback:** se o arquivo da arte estiver ausente ou seu Qt não conseguir decodificá-lo, os recursos da Yuna continuam disponíveis com a apresentação antiga.
- **Ainda não é uma personagem 3D de produção:** o retrato 2.5D não tem esqueleto, física de cabelo ou sincronização labial real. Essas características dependem de um VRM rigado no renderizador 3D opcional.

## Próximos refinamentos possíveis

- Exportar um VRM original com aparência correspondente e expressões próprias.
- Criar sprites separados de olhos e boca se a prioridade for Live2D, com animações perceptíveis sem renderização 3D.
- Empacotar no futuro um instalador Windows, com testes de inicialização e áudio em hardware real.

Nenhuma informação pessoal é publicada pela página de demonstração. Não adicione `data/`, credenciais ou vídeos privados ao GitHub.
