# Magi1020 — chamada por webcam entre duas instalações da Yuna

Este recurso abre uma **videochamada voluntária no navegador**, usando
um serviço externo (`https://meet.jit.si`). Ele **não** é uma ferramenta
de vigilância remota nem permite ligar a webcam da outra pessoa sem que
ela saiba. O comando `Magi1020` é público no código do projeto: **não
serve como senha**, identificação do criador ou autorização de câmera.

## Como usar no notebook de Kaizen

1. Atualize a Yuna Desktop e abra normalmente.
2. Digite **`Magi1020`** na conversa, ou clique no botão
   **◈ Magi1020 • Vídeo remoto**.
3. Selecione **Criar convite privado para minha esposa**.
4. A Yuna gera um **link aleatório novo para a sala**. Escolha
   **Copiar e abrir** para abrir a reunião no navegador e copiar o link.
5. Envie o link à sua esposa por um meio privado. Não publique o link:
   quem possui o endereço pode tentar participar da mesma sala.
6. O serviço público meet.jit.si pode exigir login de quem **inicia**
   a reunião. Use as opções de login exibidas pelo navegador.

## Como usar no notebook da esposa

1. Sua esposa recebe o convite e abre a Yuna Desktop ou simplesmente
   o link no navegador.
2. Pela Yuna, ela pode digitar **`Magi1020`**, escolher **Entrar com
   um convite que recebi**, colar o link e confirmar a abertura do navegador.
3. No Jitsi, **ela decide se ativa a webcam e o microfone**, podendo
   deixar qualquer um desligado.
4. A partir daí vocês se veem pela chamada. Para encerrar, cada pessoa
   pressiona **Sair** no serviço ou fecha a aba.

Muitos notebooks já possuem webcam integrada. Caso o Windows não
reconheça nenhuma webcam, será necessário conectar uma webcam externa
para transmitir vídeo. Quem recebe vídeo não precisa compartilhar a
própria câmera.

## Segurança, funcionamento e limites

- **Não existe conexão automática entre computadores** quando a Yuna
  é instalada: não há pareamento secreto, webcam de fundo, varredura
  de rede ou transmissão sem a aprovação da outra pessoa.
- A Yuna **não inicia WebRTC por conta própria**. Ela apenas cria/copia
  um convite e abre o link do Jitsi após clique. O navegador e o
  Windows controlam as permissões de câmera e microfone.
- **Serviço externo**: áudio/vídeo passam pela infraestrutura do Jitsi,
  conforme suas políticas e condições. Não é um fluxo hospedado na
  Yuna local, nem deve ser considerado criptografia ponta a ponta
  automática. Avaliem os controles de privacidade da reunião.
- O anfitrião deve entrar com uma conta aceita pelo serviço público
  meet.jit.si. Quem participa depois pode entrar como convidado,
  dependendo das políticas atuais.
- O link é aleatório por convite e não fica salvo no SQLite, no diário,
  em arquivos do projeto nem em logs da Yuna. É copiado **somente
  quando o usuário pede**. Pode continuar válido como nome de sala
  depois que a chamada termina: **não é um token com expiração imposta**.
  Não reutilize links antigos; gere um novo para cada chamada.
- O código Magi1020 **não é uma senha secreta**. Qualquer instalação
  pode abrir a opção de criar um convite. A segurança da webcam vem
  das permissões do dispositivo, dos controles do navegador e
  da decisão explícita da pessoa transmitindo.
- **Break080111 e o botão Parar da Yuna não encerram chamadas externas
  abertas em outra aba.** Cada participante deve usar **Sair** ou
  desativar a câmera no navegador. A Yuna não promete interromper
  aplicativos sobre os quais não tem controle.
- O projeto **não grava, não cria screenshots nem analisa** a chamada.
  Qualquer recurso de gravação próprio do Jitsi dependerá do
  funcionamento e das permissões daquele serviço.
- Para um fluxo **inteiramente dentro da Yuna**, sem serviço externo,
  será preciso implementar um servidor de sinalização/identidade,
  WebRTC, NAT/STUN/TURN e gerenciamento de consentimento e sessões.
  Isso **ainda não foi implementado**.

## Como verificar a webcam no Windows

1. Abra o aplicativo **Câmera** do Windows.
2. Veja se há imagem. Se não houver, verifique o obturador físico,
   as permissões em **Configurações → Privacidade e segurança → Câmera**
   e o **Gerenciador de Dispositivos → Câmeras**.
3. Se a webcam não existir ou estiver com defeito, a Yuna não pode
   criar uma câmera por software; é preciso um dispositivo físico.

## Referências do provedor

- https://jitsi.github.io/handbook/docs/user-guide/user-guide-join-jitsi-meeting/
- https://jitsi.org/blog/authentication-on-meet-jit-si/
- https://jitsi.org/security/
