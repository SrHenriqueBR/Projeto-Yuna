# Alertas gratuitos da Yuna: Telegram opcional + WhatsApp manual

## Decisão de custo (outubro de 2026)

Você pediu para **parar se houver custo**. Portanto:

- **WhatsApp automático permanece DESLIGADO / NÃO IMPLEMENTADO.**
  Os templates iniciados pela empresa na API oficial da Meta são
  potencialmente **cobrados por mensagem**. A regra brasileira de outubro
  de 2026 indica tarifa de utilidade de referência de R$0,035 por
  mensagem entregue. A franquia gratuita de mensagens de serviço não
  se aplica automaticamente a esses modelos e não garante custo zero
  para alertas iniciados pelo computador.
- **WhatsApp permanece GRATUITO no modo manual** (link `wa.me` que abre
  mensagem pronta, exige que a pessoa pressione **Enviar**).
- **Telegram automático é OPCIONAL** e usa a Bot API gratuita no
  tráfego normal. Nenhum plano, provedor pago, saldo de Stars,
  recurso `allow_paid_broadcast` ou método de cobrança é ativado.
  A Yuna envia no máximo **6 tentativas em cada sessão de 30 minutos**,
  sem retries automáticos.

A Bot API gratuita usa a infraestrutura do Telegram — **os textos
predefinidos dos alertas passam pelo Telegram**, não pelo WhatsApp.
O notebook precisa de internet. A confirmação técnica da API
**não garante entrega, leitura ou disponibilidade do seu telefone**.

## Preparar bot e celular (gratuito)

1. No **seu celular**, instale/abra o Telegram e localize o bot
   oficial **@BotFather** (verifique o identificador).
2. Envie `/newbot`, dê um nome único e copie o **TOKEN** do bot. Ele
   funciona como uma senha; **não cole no chat da Yuna, não envie a
   terceiros e não faça commit no GitHub.**
3. Abra uma conversa privada com seu novo bot e envie **`/start`**.
   Bots geralmente não podem enviar mensagens ao usuário que nunca
   iniciou uma conversa com eles.
4. No notebook que fará os alertas, abra um terminal na raiz da Yuna e
   execute `py -3 configurar_alertas_telegram.py`. Cole o token no
   prompt seguro (os caracteres não aparecem na tela).
5. O script consulta **somente chats privados** que falaram com seu bot.
   Copie o **ID numérico da sua conversa**, conferindo se ele é o
   correto. Ele não grava token, conversa ou histórico.
6. Abra **◉ Segurança doméstica (SOS)** na Yuna instalada no notebook
   da pessoa que concorda com o monitoramento.
7. Informe o número de WhatsApp de confiança (continua útil caso você
   escolha modo manual), marque **Telegram gratuito**, digite o TOKEN
   no campo mascarado e cole o chat ID.
8. Opcionalmente marque o microfone para detectar **apenas sons altos**.
   A pessoa do notebook deve ler e **confirmar** a ativação. O modo
   só dura **30 minutos**, não inicia sozinho e tem botão para desligar.

## O que a Yuna envia

- **SOS:** depois da pessoa pressionar SOS e confirmar o pedido,
  um texto fixo de ajuda é enviado para o chat privado configurado.
  Não contém áudio, imagem, localização nem transcrição.
- **Som alto:** somente quando o microfone está ativo por consentimento,
  há som alto sustentado e não foi cancelado em **15 segundos**.
  A Yuna envia um texto fixo deixando explícito que pode ser falso alarme.
- **Movimento da webcam:** permanece **apenas aviso local**, sem alerta
  remoto. Não foi conectado ao Telegram nesta etapa.

Existem dois limites contra alertas repetidos: **45 segundos para SOS**,
**5 minutos para som alto** e **máximo de 6 tentativas por sessão**
(sucesso ou falha). Não há retentativas escondidas nem compra de quota.

Ao desligar a Yuna ou usar **Break080111**, novas solicitações
do sistema são interrompidas. Um pedido HTTP **já transmitido**
pode não ser cancelável. A Yuna nunca afirma que a mensagem
chegou ao celular: só exibe se a API aceitou a solicitação.

## Custos e privacidade

- Não há envio automático pago pelo WhatsApp nesta implementação.
- Telegram Bot API é oferecida **sem custo para o uso normal**, mas
  depende da internet e de termos de serviço externos. Caso a
  política de preços mude, não existe verificação automática
  independente; revise a documentação do Telegram antes de utilizar.
- **Não use o Telegram como único canal de emergência.** O aplicativo
  pode ficar sem internet, deslogado, sem notificações ou com o bot
  bloqueado. Contato direto é prioritário em suspeita de emergência.
- **A pessoa no notebook escolhe quando ativar e desligar.**
  O programa não ativa webcam, microfone ou avisos remotamente,
  nem esconde indicadores de monitoramento.
- Tokens ficam só na memória durante a sessão; o campo é mascarado
  e limpo ao desligar. Nunca são enviados à IA Ollama, guardados em
  arquivos, banco de dados, histórico de mensagens ou log de erros.
- O notebook usa conexão HTTPS com `api.telegram.org`. As mensagens
  não incluem informações de identidade ou dados pessoais.

## Fontes

- WhatsApp Pricing:
  https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/
- Telegram APIs gratuitas: https://core.telegram.org/
- Telegram Bot API: https://core.telegram.org/bots/api#sendmessage
- BotFather/tutorial: https://core.telegram.org/bots/tutorial
- Link manual WhatsApp: https://faq.whatsapp.com/5913398998672934/
