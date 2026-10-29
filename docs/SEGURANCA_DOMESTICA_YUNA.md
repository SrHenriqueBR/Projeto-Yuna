# Yuna 0.41 — Vídeo na interface e Segurança doméstica opt-in

Este módulo foi planejado para uso entre pessoas que **concordam** em
compartilhar uma chamada ou em ativar um monitor de segurança no seu próprio
notebook. **Instalar a Yuna nunca habilita uma webcam nem um microfone.**

## Vídeo remoto na própria janela da Yuna

O botão **▣ Videochamada dentro da Yuna** recebe um convite `Magi1020`
e abre uma janela Qt própria com a reunião Jitsi. A câmera só aparece
se a pessoa no outro notebook **participar da chamada e permitir o uso da
webcam**; ela pode desligá-la ou sair a qualquer instante.

1. Em um dos notebooks, digite `Magi1020` e crie um novo convite.
2. Copie o link e compartilhe **privadamente** com a outra pessoa.
3. Cada participante pode clicar em **▣ Videochamada dentro da Yuna**,
   colar o mesmo link e confirmar a abertura.
4. Se Qt WebEngine estiver instalado, a chamada aparece **dentro da Yuna**.
   Se não estiver, clique em *Abrir em navegador externo*.
5. Quem quiser compartilhar câmera/microfone autoriza a permissão na
   própria janela ou navegador. **A Yuna não contorna essa autorização.**
6. **Sair da chamada nesta janela** encerra a participação neste cliente.
   Quando a chamada for aberta num navegador externo, use o botão *Sair*
   do próprio navegador para encerrá-la.

**Dependências:** PySide6 Qt WebEngine compatível com sua instalação.
A disponibilidade depende dos pacotes presentes e dos drivers. A
reunião via meet.jit.si usa um **serviço externo** (não LAN nem P2P
garantido). O Jitsi indica que o serviço público é para testes, não
uma infraestrutura de produção para aplicativos integrados. Host pode
precisar se autenticar, e a inclusão de câmera/microfone depende
do funcionamento do navegador e das permissões do Windows. Não é uma
câmera oculta nem monitoramento remoto persistente.

## Modo Segurança — SOS e sons altos (por 30 minutos)

No notebook monitorado, a pessoa presente abre
**◉ Segurança doméstica (SOS)**. A sessão começa **DESLIGADA**.
A própria pessoa informa o telefone do contato de confiança com
DDI/DDD, escolhe se deseja usar o microfone e clica
*Ativar modo Segurança*. Uma confirmação explica o escopo.
A sessão vale no máximo **30 minutos** e oferece
**Desligar monitoramento** e `Ctrl+Shift+X`.

- **SOS manual:** gera um **rascunho do WhatsApp** para o contato de
  confiança, depois de a pessoa confirmar que deseja abrir o chat.
  **É necessário apertar Enviar** no WhatsApp. Não há confirmação
  automática de entrega.
- **Som alto local (opcional):** utiliza `QAudioSource` com amostras PCM
  temporárias para calcular só o nível RMS; não armazena nem transcreve
  áudio, não identifica vozes nem reconhece palavras. Som sustentado
  pode gerar uma indicação de possível problema.
- **Falso alarme:** há uma janela de 15 segundos para cancelar um
  alerta sonoro. Após o prazo, abre-se uma opção para **revisar** um
  rascunho do WhatsApp. Nenhuma mensagem é enviada sem ação local.
- **Sem webcam:** o modo SOS/som não liga a câmera. A videochamada
  remota e a webcam continuam separadas e dependentes de consentimento.

### Alerta local de movimento na webcam (opcional)

Na janela **◉ Ver câmera autorizada**, depois de autorizar a fonte,
existe uma caixa **Detectar mudanças de imagem localmente**.
A detecção é desligada por padrão; se ativada, analisa apenas uma
miniatura cinza 64x36 em memória, com cooldown contra repetições.
Pode confundir sombras ou luz com movimento. Mostra aviso **no notebook**
e **não** envia vídeo, fotos nem notificações ao WhatsApp.

## O que NÃO foi implementado

- **Envio automático de WhatsApp:** a infraestrutura WhatsApp Business
  Cloud API requer conta comercial, número, destinatário autorizado,
  credenciais e modelo de mensagem aprovado. O módulo de envio
  automático NÃO foi integrado nesta etapa; o rascunho WhatsApp é
  apenas uma alternativa **manual**.
- **Monitoramento remoto sem aprovação da pessoa:** não existe.
- **Detecção confiável de emergência, violência, queda ou pedidos de
  socorro por reconhecimento de fala:** não implementada; som alto
  sozinho não comprova que algo ruim aconteceu.
- **Captura em segundo plano, gravação, envio de áudio/vídeo para
  terceiros por conta da Yuna, reconhecimento facial ou identificação
  biométrica:** não implementados.
- **Garantia de interrupção de uma chamada em serviço externo via
  Break080111:** impossível garantir. O comando para os recursos
  controlados pela Yuna, mas cada participante precisa sair da chamada
  externa ou desligar seu dispositivo no navegador.

**Recomendação para alertas importantes:** não depender apenas de
um notebook, de detecção de som ou de uma integração em testes.
Use contato direto e serviços de emergência quando houver perigo real.

### Próxima fase possível

Com consentimento e configurações verificáveis, adicionar uma integração
com provedor oficial de mensagens, incluindo alertas de entrega,
consentimento do destinatário, limites de frequência e política de
retenção. Só então será possível classificar um alerta como
**solicitação automática enviada** — nunca como **entregue** sem
confirmação do provedor.

## Testes

- `tests/test_home_safety.py`: permissão, intensidade sonora, cancelamento,
  detecção de movimento e URL de rascunho sem transmissão.
- `tests/test_home_safety_desktop.py`: aprovação local, recusa, abertura
  de convite dentro da Yuna e botão de parada sem hardware externo.

### Fontes técnicas

- Jitsi IFrame API: https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-iframe/
- Qt WebEngine: https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineCore/QWebEnginePermission.html
- Jitsi API pública: https://jitsi.org/api/
