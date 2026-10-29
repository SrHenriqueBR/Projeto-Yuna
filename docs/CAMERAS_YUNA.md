# Yuna • prévia autorizada de câmeras (primeiro piloto)

**Status:** acesso local e temporário a webcams e fluxos RTSP compatíveis.
Ainda **não existe sistema de vigilância 24h, gravação, alertas de intrusão,
reconhecimento de pessoas, busca automática de câmeras, suporte ONVIF/DVR
proprietário ou análise por IA**. A câmera só funciona depois de confirmação.

## Requisitos

- Windows 10/11 e interface **Yuna Desktop** funcionando.
- **OpenCV opcional:** execute `py -3 -m pip install opencv-python`
  na **mesma instalação Python usada pela Yuna**. O pacote não é
  instalado ou importado automaticamente ao abrir o programa.
- Para webcam: conheça seu índice, normalmente `0` ou `1`.
- Para câmera IP: tenha permissão de uso e um **URL RTSP completo**
  fornecido pelo fabricante/administrador do equipamento, como
  `rtsp://192.168.1.50:554/stream1` (exemplo fictício, não é um
  endereço universal nem garante compatibilidade).
- No piloto RTSP, aceitamos apenas **IPs privados da rede local**; não há
  procura de dispositivos nem encaminhamento para serviços públicos.
  A funcionalidade exige que o PC esteja conectado à rede da câmera.

## Como usar

1. Na janela principal, clique em **◉ Ver câmera autorizada**.
2. Escolha `webcam 0`, `webcam 1`, ou informe uma URL
   `rtsp://...` válida da rede local.
3. Leia a confirmação e clique **Sim** apenas para uma câmera que você
   possui ou que esteja autorizado a visualizar.
4. A Yuna abre uma janela de prévia local. A sessão acaba após **5 minutos**
   ou ao clicar em **■ Encerrar câmera**.
5. O comando **Break080111**, o botão **Parar** da Yuna Desktop, o atalho
   **Ctrl+Shift+X** dentro da prévia e fechar o programa também solicitam
   a interrupção imediata. Operações de abertura/leitura que estiverem
   bloqueadas no driver podem depender do timeout do backend para terminar.

Também é possível escrever **“Yuna, mostre a câmera da garagem”**,
**“Yuna, abra a webcam”** ou **“Quero ver a câmera”**: a janela de
**escolha e consentimento** será aberta. A Yuna ainda não sabe qual
câmera corresponde a “garagem”, pois não mantém cadastro automático.

## Segurança e privacidade

- **Nenhuma câmera é aberta ao iniciar a Yuna**: o botão e os pedidos
  naturais apenas abrem a escolha e solicitação de autorização.
- **Nenhuma senha/URL RTSP é persistida**, adicionada ao banco SQLite,
  enviada ao Ollama ou registrada nos logs. Como os campos atuais recebem
  a URL completa em texto, ela fica visível enquanto você a digita:
  cuidado ao compartilhar tela. Futuramente deverá haver campo de senha
  mascarado e cofre de credenciais, antes de habilitar cadastro persistente.
- No momento, a aplicação **não tira fotos, não grava arquivos,
  não transmite a imagem a serviços e não realiza inferência por IA**.
  A prévia é renderizada apenas na memória da janela Qt.
- A câmera não fica em segundo plano após fechar a prévia. A interrupção
  de um driver de vídeo que não respeite timeout pode não ser instantânea;
  o acesso permanece sem persistência e o worker é daemon.
- Para vigilância real de propriedade, recomenda-se definir critérios
  específicos de consentimento, retenção, notificação e segurança, sem
  gravar pessoas em locais onde não exista autorização.
- URLs RTSP com credenciais embutidas são aceitas **somente na memória da
  sessão**; nunca compartilhe URLs com senhas. Prefira credenciais com
  permissões apenas de visualização, fornecidas pelo administrador.

## Limitações conhecidas

- Alguns DVRs/NVRs não oferecem RTSP padrão ou exigem integração própria.
- OpenCV/FFmpeg pode falhar conforme codec, firewall, driver e autenticação.
- A prévia não possui verificação de qual pessoa está diante do computador.
  A aprovação de acesso é feita pelo operador da sessão Windows, não por
  reconhecimento biométrico.
- A janela apresenta até ~10 quadros/s para reduzir consumo, não é um
  gravador de segurança nem substitui sistema de CFTV profissional.
- Compatibilidade com um modelo de câmera específico precisa ser testada
  diretamente no equipamento com autorização.

## Próximas etapas possíveis

**Somente com solicitação do usuário e configuração explícita:**
detector local de movimento, câmera cadastrada com credencial no cofre do
Windows, alertas definidos pelo operador, armazenamento criptografado com
prazo de retenção e visão local baseada em modelo instalado. Não habilitar
captura persistente nem notificações sem consentimento.
