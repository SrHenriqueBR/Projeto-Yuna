# Uma única Yuna no Windows

## Instalação recomendada

1. Baixe **[Yuna-Setup.exe](https://github.com/SrHenriqueBR/Projeto-Yuna/releases/latest/download/Yuna-Setup.exe)**.
2. Execute o instalador e escolha se deseja um atalho na Área de Trabalho e início
   com o Windows. A instalação é na sua conta, sem exigir administrador.
3. Se já usava Yuna, feche a versão antiga e selecione a pasta anterior no campo
   de importação. Ela precisa conter `data`. A cópia inclui um snapshot consistente
   dos bancos SQLite. A origem não é apagada, e um destino com dados não é sobrescrito.
4. Abra **Yuna.app**. No chat, **••• → Central da Yuna** reúne as opções.

O pacote inclui o ambiente privado de Python, bibliotecas da interface, documentos,
voz local, voz Edge opcional e o renderizador 3D compilado. Ollama e os modelos de
texto/Whisper são separados. Em **Preparação**, abra o endereço oficial do Ollama,
deixe-o em execução e prepare o modelo leve ou padrão. O download pode usar vários
GB e só começa após confirmação. Reinicie a Yuna depois de mudar o modelo.

O instalador funciona no Windows 10/11 x64. Não tem certificado comercial de
assinatura; o Windows pode mostrar editor desconhecido. Baixe do repositório do
projeto e confira `SHA256SUMS.txt` na mesma release. Não desative o antivírus.

## Onde ficou cada recurso

| Central | Opções |
| --- | --- |
| Minha Yuna | Chat compacto/completo, personagem 2D, avatar 3D, chat web e segundo plano |
| Permissões | Escuta local, USB/energia, avisos falados, câmera, jogo e parada |
| Preparação | Diagnóstico, modelos Ollama, atalhos, início com Windows, pasta de memórias e atualização |
| Avançado | Autoteste, terminal, laboratório, revisão/restauração, gestão e interface clássica |

O app usa as autorizações que já existiam: câmera e microfone são por sessão;
jogos exigem escolha explícita. Instalar não autoriza esses recursos automaticamente.
O botão Parar continua acessível. Não há uma permissão genérica de controle total.

As ferramentas avançadas abrem uma janela própria com andamento e instruções.
O chat web e o servidor 3D permanecem ativos enquanto suas janelas estiverem abertas.
Após abrir o 3D, use **Conectar Yuna 3D** na janela completa para vincular animação e voz.
Modelos VRM pessoais e o projeto Unreal continuam opcionais e não são baixados.

## Memórias, atualização e desinstalação

A pasta padrão de dados do app instalado é
`%LOCALAPPDATA%\Programs\Yuna\app\data`. Use **Preparação → Abrir pasta das memórias**.
Feche a Yuna antes de fazer backup manual. Para atualizar ou reparar, execute o
instalador novo no mesmo local. Ele substitui os arquivos do programa, preservando
`data`. Pelo Windows, **Aplicativos instalados → Yuna → Desinstalar** remove o app e
seus atalhos; dados pessoais permanecem na pasta para permitir recuperação.

Na importação, não mesclamos bancos. Se o destino já tem dados, ele permanece
intacto e o instalador informa que a importação não foi concluída. Avatares pessoais
fora de `data` continuam na instalação anterior; faça backup deles separadamente.

## Código-fonte: somente Yuna.bat

Para desenvolver, extraia o ZIP do GitHub e abra **Yuna.bat**. É a única entrada
`.bat` do projeto. Requer Python compatível de 64 bits com `venv`; a preparação
cria `.venv`, sem modificar pacotes globais. Se não houver Python, prefira o
instalador pronto. Use a pasta inteira da versão, não misture módulos isolados.

Ao atualizar uma pasta antiga por ZIP, as 14 entradas antigas conhecidas são
movidas para `data/inicializadores-antigos`. Arquivos personalizados com outros
nomes e as memórias não são removidos. Para a cópia de desenvolvimento, o 3D requer
`npm install` e `npm run build` em `avatar3d`; no instalador ele já vem pronto.

## Empacotamento e testes

O workflow **Instalador Windows da Yuna** monta o app com Python embeddable oficial
(versão e SHA-256 fixos), dependências em diretório privado, launcher `Yuna.exe` e
Inno Setup. Executa a suíte no runtime distribuído e testa instalação silenciosa,
abertura da interface, importação, atualização e desinstalação preservando dados.
Só então publica `Yuna-Setup.exe` e sua soma SHA-256 em Releases.

Uma release existente nunca é sobrescrita pelo workflow: aumente `VERSION` em
`self_model.py` para publicar outra. Builds de uma versão já publicada ficam nos
artefatos do workflow. Microfone, câmera, carregadores e jogos reais ainda precisam
de verificação na máquina em que a Yuna será usada.
