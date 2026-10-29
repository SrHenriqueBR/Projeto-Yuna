# Avatar 3D VRM da Yuna — protótipo experimental

Este módulo é **opcional**, independente da Yuna Desktop em Python. Usa
Three.js + `@pixiv/three-vrm` e funciona em navegador moderno com WebGL.

## Instalação (computador com GPU / Alienware)

1. Instale **Node.js 22 LTS** (ou Node >=20.19) no Windows.
2. Abra um terminal em `avatar3d/` e execute `npm install`. É necessário
   acesso à internet **nessa instalação inicial**.
3. Execute `npm run dev` e acesse `http://127.0.0.1:5173`.
   Como alternativa, da raiz do projeto execute `iniciar_yuna_3d.bat`
   **depois** de instalar as dependências.
4. Clique em **Importar modelo .VRM**, escolha **seu próprio arquivo** e teste
   as expressões. Até 80 MB por arquivo. Também é possível soltar o arquivo
   na área de visualização.

Sem `.vrm`, a aplicação mostra apenas uma **prévia geométrica original**
com cabelo escuro e olhos violeta. Não é o modelo final da Yuna, nem um VRM.

Para validar o código: `npm test` e `npm run build`.

## Controles

- Mova o cursor: movimentos leves de cabeça e olhos.
- Arraste com o mouse: gira a câmera; roda: zoom.
- Botões: neutra, feliz, curiosa, surpresa, tímida e acenar.
- Barra **Prévia da fala**: abertura de boca de demonstração (não é áudio real).
- Marque **Economizar movimento** para reduzir movimentos; há limite de 30/60 FPS.
- Ao ocultar a aba, a renderização pausa para economizar GPU.

## Privacidade, licenças e limitações

- Nenhuma câmera, microfone, LLM, SQL, captura de tela ou comando do Windows
  é acessado por este renderizador. Não há servidor de entrada de ações.
- O arquivo VRM é escolhido localmente pelo usuário e carregado por URL
  temporária (blob); não é enviado a provedores externos.
- **Não estão implementados:** conexão com a fala real, eventos do
  AvatarController, reconhecimento facial, VRM de produção, avatar flutuante
  transparente e instalação automática do Node.
- A Yuna 2D permanece padrão e funciona mesmo sem `avatar3d/node_modules`.
- **Direitos dos modelos 3D:** o usuário deve ter licença para usar seu VRM;
  modelos de exemplo de outros projetos não são redistribuídos aqui.
- `@pixiv/three-vrm` e Three.js são dependências locais. Consulte as licenças
  dos pacotes e de eventuais texturas/modelos externos antes de distribuir.
- O preview 3D precisa de WebGL. Não há garantia de FPS específico no Alienware
  até testes na máquina real; se houver travamentos, use 30 FPS ou volte ao 2D.

## Próxima etapa

Ligar o contrato de eventos `AvatarController` → renderer 3D (preferencialmente
via uma ponte local com controle de origem e autenticação, **não** execução
de comandos vindos do browser). Sincronizar boca com **reprodução real** do
QMediaPlayer e adicionar bone rigs/animação de braços quando suportados pelo
arquivo VRM.
