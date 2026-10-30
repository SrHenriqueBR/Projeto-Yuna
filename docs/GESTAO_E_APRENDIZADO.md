# Gestão, aprendizado e acesso autorizado na Yuna

## O que funciona nesta etapa

- Chat local no navegador com Ollama, personalidade e memória da instalação.
- Recursos do computador na interface desktop: programas, pastas, documentos e demais ferramentas já implementadas.
- Prévia local de câmera e videochamada voluntária, com os controles de autorização dos respectivos módulos.
- Uma fila local de conhecimentos compartilhados voluntariamente, com revisão pelo responsável autenticado.
- Aprovação, rejeição, retirada da base e registro das decisões, sem publicar conversas privadas nesse painel.

**O painel é desta instalação. Não é uma central remota de todas as pessoas que instalaram a Yuna.** Instalar o programa não envia tela, câmera, informações do computador nem conversas ao criador do projeto.

## Configurar seu painel

1. Atualize o projeto completo, preservando a pasta `data`.
2. No computador que você administra, execute `configurar_gestao_yuna.bat`.
3. Informe o nome visível do responsável e crie uma senha de pelo menos 12 caracteres. A senha é digitada sem aparecer no terminal e armazenada como hash com sal.
4. Abra `iniciar_yuna_web.bat` e acesse `http://127.0.0.1:8787/yuna-gestao.html`.
5. Entre com a senha configurada. Escrever um nome, um código público ou dizer “sou o criador” no chat não concede acesso.

A configuração inicial só existe no terminal; não há cadastro de proprietário pela página pública. As sessões do painel expiram em 30 minutos e são invalidadas ao reiniciar o servidor. Use **Sair** para encerrar a sessão. Não há recuperação ou troca de senha pela web nesta etapa.

## Como a pessoa escolhe o que compartilhar

No chat, abra **Como a Yuna ajuda e aprende**. O painel informa quem é o responsável desta instalação. A pessoa escreve uma dica geral, revisa o texto e marca a autorização para compartilhar **aquele texto**, com aquele responsável, para possível uso na base comum local.

O formulário não envia outras mensagens, histórico, arquivos ou dados de câmera. Há uma triagem básica de informações sensíveis, que não substitui a revisão humana. Não coloque informações pessoais ou credenciais no texto.

O texto aguarda revisão. Somente itens aprovados podem aparecer como referências gerais no contexto do chat web. Eles são tratados como dados, não como novas instruções, e não concedem permissões para executar ações. São usadas até cinco referências por resposta; os pesos do modelo não são treinados por esse mecanismo.

Depois de compartilhar, guarde o **comprovante** em particular. Ele permite consultar o estado ou retirar a sugestão pelo mesmo painel, mesmo que já tenha sido aprovada. A retirada limpa o texto da fila e o remove das referências futuras. Ela não apaga respostas anteriores que já utilizaram a referência.

O responsável pode aprovar ou rejeitar uma sugestão e retirar um item da base. Não pode reativar um texto retirado pelo remetente. O registro de decisões contém o tipo de evento, a data e o identificador da proposta, sem copiar o texto ou as conversas.

## Memória pessoal e base comum

A memória pessoal continua em `data/yuna.db` e `data/conhecimentos.json`; a revisão fica em `data/gestao_yuna.db`. Não publique esses arquivos no GitHub. O servidor serve apenas uma lista fixa de arquivos da interface.

Esta versão ainda utiliza **uma memória por instalação**, não múltiplas contas de pessoas. Em um computador compartilhado, cada pessoa precisa de uma cópia dedicada no próprio perfil. Contas com isolamento de conversas e dados dentro da mesma instalação ainda precisam ser implementadas antes de uso multiusuário em produção.

O nome do responsável identifica a configuração local, não comprova uma identidade global do Kaizen. Não distribua uma senha de proprietário igual em todas as instalações.

## O que falta para uma central remota exclusiva do proprietário

Uma central remota precisa de um serviço definido, login verificável do proprietário e contas separadas por pessoa/dispositivo. O pareamento deve identificar claramente o destinatário, e cada pessoa deve autorizar os escopos que quer compartilhar.

A tela, a câmera e informações do computador devem ser opções independentes, desligadas inicialmente. Cada sessão precisa de indicação visível, limite de duração, botão para encerrar e revogação pelo usuário. O servidor deve verificar quem pode receber cada sessão; ser criador do código não substitui essa autorização.

A revisão central deve receber apenas conhecimentos que a pessoa selecionar para compartilhar. Conversas pessoais e preferências não devem virar uma transmissão automática de conteúdo ao administrador.

**Nada dessa central remota foi ativado nesta etapa.** Os convites de vídeo já existentes continuam dependendo das regras do serviço de chamada; um link de reunião, sozinho, não garante que apenas o proprietário consiga participar.

## Verificação

Os testes exercitam autorização de compartilhamento, senha e sessão do painel, bloqueio de acesso por identidade declarada, revisão, retirada pelo remetente e entrada no contexto apenas após aprovação. As respostas do modelo são simuladas nos testes; o tom e a utilidade das respostas reais devem ser avaliados com o Ollama no notebook. Nenhuma captura de câmera ou tela é necessária nesses testes.
