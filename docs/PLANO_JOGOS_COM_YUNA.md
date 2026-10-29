# Yuna jogando com o usuário — piloto de controle supervisionado

**Status: somente contrato de sessão / segurança implementado.**
A Yuna ainda **não vê jogos**, não produz comandos de gamepad e **não joga
The Last of Us nem qualquer outro título** nesta etapa. O código atual
de `game_sessions.py` só cria e valida propostas curtas, sem executar teclas.

## Experiência desejada

A pessoa está jogando um título individual e diz: "Yuna, quer jogar comigo?".
A Yuna explica o que consegue fazer e pede autorização **por sessão**.
Depois de aprovado, o modo futuro deverá:

1. Confirmar **qual executável** de jogo está ativo, qual janela/processo
   possui foco e se a pessoa marcou um modo individual/offline.
2. Capturar **somente a janela do jogo**, após autorização explícita;
   não capturar desktop inteiro, emails ou notificações.
3. Usar um modelo visual local compatível com o hardware para reconhecer
   elementos de jogo (caminhos, objetos, objetivos, HUD), sem afirmar
   compreender a cena quando não reconhece.
4. Formular uma ação limitada (por exemplo, caminhar 0,15 s), executar
   **somente através de adaptador local autorizado** e observar o resultado.
5. Reavaliar foco, jogo permitido, sessão e limites **antes de cada input**.
   Em falta de foco, falha de visão, mudança de janela ou latência alta:
   soltar todas as teclas/botões, parar e relatar.
6. Responder a **Break080111**, botão de parada e encerramento do programa,
   sem insistir em completar uma tarefa antiga.

## Segurança e recursos

- Nenhuma ação de teclado, mouse ou controle é habilitada pelo código atual.
- Sessões futuras: autorização explícita, jogo individual/offline,
  executável local completo, expiração máxima de 10 minutos e até 120
  propostas de comandos curtos (máximo 0,5 s por proposta).
- Não executar ações genéricas de shell ou abrir arquivos a partir do
  texto do modelo. O catálogo contém somente movimentos de jogo.
- O módulo de permissão não autentica PID/HWND ainda; essa checagem precisa
  existir **também no adaptador efetivo de entrada**, antes de habilitar
  qualquer controle.
- Evitar multiplayer e jogos com anticheat até avaliar políticas e
  compatibilidade. Não automatizar compras, chat com outros jogadores,
  saves ou configurações do sistema.
- Respeitar modo de economia de bateria e desempenho dos modelos locais;
  não iniciar visão local automaticamente em PCs de 8 GB.

## Primeiro piloto recomendado

Testar **um jogo individual por vez**. The Last of Us Part I para PC
é uma opção mencionada pelo usuário, mas nenhuma compatibilidade foi
verificada e nenhum nome de executável é presumido. O piloto deverá usar
captura da janela selecionada e comandos limitados, com replay e logs
**locais e sem frames confidenciais por padrão**. Primeiro validar
em um ambiente de teste sem progresso importante; só então testar um
jogo real com autorização.

## Entregue agora

- `GameSession`: inicia desligada, só autoriza sessão com consentimento
  explícito e confirmação de jogo offline/individual.
- Validação de caminho local `.exe`, comparação de executável esperado,
  comandos permitidos, limite de duração por ação, limite de sessão,
  expiração e revogação por troca de aplicativo.
- `Break080111` revoga a sessão em memória. O botão **Parar** existente
  também desarma o módulo, mesmo que ainda não haja um driver ativo.
- Testes unitários sem teclado, câmera, jogo, rede nem GPU.

**Não afirmar "joguei" até que visão, input e verificação tenham sido
implementados e testados no PC real.**
