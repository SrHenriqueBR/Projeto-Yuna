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

Sem `.vrm`, a aplicação mostra uma **personagem anime geométrica original**
com aparência editável. É uma prévia, não o modelo VRM artístico definitivo.

Para validar o código: `npm test` e `npm run build`.

## Vincular à voz real da Yuna Desktop (nova etapa)

1. Instale as dependências opcionais em `avatar3d/` com `npm install`
   uma única vez (Node 22 LTS).
2. Abra a **Yuna Desktop** normalmente em `iniciar_yuna.bat`.
3. Execute `iniciar_yuna_3d.bat` para iniciar o renderizador local em
   `http://127.0.0.1:5173`.
4. Na janela da Yuna, clique em **◇ Conectar Yuna 3D**. Ela abrirá uma nova
   aba com credencial de sessão temporária e habilitará a sincronização.
5. Escolha um modelo `.vrm` próprio (ou use a prévia geométrica para testar).
   Ao ouvir a resposta da Yuna, a boca acompanhará o áudio reproduzido.
6. Para encerrar a comunicação, clique em **■ Desconectar Yuna 3D** ou
   feche a Yuna Desktop. O renderizador continuará em modo de prévia.

A ponte só inicia com **ação explícita**, usa uma porta dinâmica em
`127.0.0.1`, exige token aleatório e aceita apenas a origem local
`http://127.0.0.1:5173`. Ela envia apenas `pose`, `emotion`, flags
de fala, amplitude e número de revisão. **Não transmite voz bruta,
transcrição, histórico, documentos, identidade, memória ou ações.**

Para falas Windows WAV, a abertura da boca usa a amplitude medida
na reprodução. Para Edge TTS MP3, ainda é uma **animação rítmica
aproximada**, não fonemas nem amplitude real. Quando o player para,
o estado remoto fecha a boca. Se a comunicação cair, a prévia
permanece manual e marca a desconexão. O navegador não controla o PC.

## Estúdio de personagem anime original (nova etapa)

O renderizador inclui uma **personagem original feita com geometria Three.js**,
sem imagens, texturas ou modelos de terceiros: corpo e rosto estilizados,
franja, cílios, olhos brilhantes, sorriso, figurinos e acessórios.

No painel **PERSONALIZAÇÃO DA PRÉVIA ORIGINAL** você pode alterar:
- **cabelo:** preto, branco, ruivo ou roxo;
- **penteado:** longo, curto, maria-chiquinhas ou rabo de cavalo;
- **olhos:** violeta, vermelho, azul ou dourado;
- **roupas:** cores escura/clara e figurinos vestido gótico, casual ou casaco;
- **acessórios:** laço, tiara, óculos ou nenhum;
- **presets:** Yuna original, Lua de inverno, Eclipse violeta.

As opções são validadas e guardadas no `localStorage` **apenas deste
navegador** (pode estar desativado). Não mexem na pasta `data/` ou em
qualquer VRM importado. **Mostrar Yuna original** remove o VRM importado
da cena e restaura o personagem geométrico; isso não exclui arquivos do
disco.

Quando a ponte local da Yuna Desktop estiver conectada, um comando como
**"Yuna, deixa o cabelo branco"** ou **"Yuna, coloca o casaco"**
atualiza o estilo autorizado no `data/avatar_yuna.json` e também
a prévia geométrica 3D na aba conectada. Nesse caso, o estilo vindo da
Yuna Desktop tem prioridade ao ser alterado. O navegador não envia
comandos de volta ao Python.

**Importante:** a prévia é um personagem 3D construído de formas;
**não é um arquivo VRM completo** nem o modelo artístico definitivo,
e suas opções não alteram malhas, texturas ou licenças de VRMs importados.
Para uma waifu 3D com rig e física de cabelos de produção,
será necessário criar/autorizar um modelo VRM próprio.

## Controles

- Mova o cursor: movimentos leves de cabeça e olhos.
- Arraste com o mouse: gira a câmera; roda: zoom.
- Botões: neutra, feliz, curiosa, surpresa, tímida e acenar.
- Barra **Prévia da fala**: abertura de boca de demonstração (não é áudio real).
- Marque **Economizar movimento** para reduzir movimentos; há limite de 30/60 FPS.
- Ao ocultar a aba, a renderização pausa para economizar GPU.

## Privacidade, licenças e limitações

- Nenhuma câmera, microfone, LLM, SQL, captura de tela ou comando do Windows
  é acessado por este renderizador. A ponte Python recebe apenas leituras
  autenticadas de estados; não há endpoint que execute ações.
- O arquivo VRM é escolhido localmente pelo usuário e carregado por URL
  temporária (blob); não é enviado a provedores externos.
- **Não estão implementados:** fonemas precisos para MP3, reconhecimento
  facial, VRM artístico de produção, avatar flutuante transparente,
  instalação automática do Node ou envio de comandos do navegador para a IA.
- A Yuna 2D permanece padrão e funciona mesmo sem `avatar3d/node_modules`.
- **Direitos dos modelos 3D:** o usuário deve ter licença para usar seu VRM;
  modelos de exemplo de outros projetos não são redistribuídos aqui.
- `@pixiv/three-vrm` e Three.js são dependências opcionais locais. Consulte as licenças
  dos pacotes e de eventuais texturas/modelos externos antes de distribuir.
- O preview 3D precisa de WebGL. Não há garantia de FPS específico no Alienware
  até testes na máquina real; se houver travamentos, use 30 FPS ou volte ao 2D.

## Próxima etapa

Ligar o contrato de eventos `AvatarController` → renderer 3D (preferencialmente
via uma ponte local com controle de origem e autenticação, **não** execução
de comandos vindos do browser). Sincronizar boca com **reprodução real** do
QMediaPlayer e adicionar bone rigs/animação de braços quando suportados pelo
arquivo VRM.
