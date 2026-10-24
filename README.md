# Projeto Yuna · Base 0.4

Assistente pessoal local para Windows. **Atualização 0.4: copie `yuna.py` e `computer.py` juntos para a pasta antiga e preserve `data/`.** Esta primeira etapa oferece conversa por texto no terminal e memória persistente em SQLite. **A voz será feminina, em português brasileiro, na próxima etapa. Ainda não há áudio nem microfone.**

## Começar no Windows

1. Instale [Python 3.10 ou superior](https://www.python.org/downloads/windows/) com o Python Launcher (`py`).
2. Instale e abra o [Ollama](https://ollama.com/download/windows).
3. Abra o PowerShell e baixe o modelo local:

   ```powershell
   ollama pull qwen2.5:3b
   ```

4. Baixe este repositório em **Code → Download ZIP** e extraia a pasta (ou use `git clone`).
5. Abra `iniciar_yuna.bat`. Alternativamente, no PowerShell dentro da pasta:

   ```powershell
   py -3 yuna.py
   ```

Não é necessário instalar pacotes com pip. O modelo inicial tem download de aproximadamente 1,9 GB e suporte a português. Foi escolhido como ponto de partida leve; desempenho e qualidade ainda precisam ser avaliados no Alienware. A licença do modelo é a Qwen Research License, independente do código deste projeto.

O aplicativo usa exclusivamente o Ollama em `127.0.0.1:11434`, sem chave de API. A instalação e o download precisam de internet; depois, o modelo local permite conversar offline. O modelo não tem as mesmas capacidades ou memórias do ChatGPT.

## Usar a memória

```text
/lembrar Meu nome é Henrique.
/lembrar Prefiro respostas em português brasileiro.
/memorias
/esquecer 1
/nova
/ajuda
/sair
```

- Conversas completas ficam em `data/yuna.db`; os últimos seis pares de mensagens entram no contexto de cada resposta, inclusive após reabrir o programa.
- Fatos importantes devem ser salvos com `/lembrar TEXTO`. Até 20 memórias de 500 caracteres são incluídas nas respostas. Isso é memória de contexto, não treinamento do modelo.
- `/nova` apaga o histórico de conversa, mas preserva as memórias explícitas.
- `/apagar CONFIRMAR` apaga histórico e memórias do banco. Não é apagamento forense do disco ou de backups.
- O banco é local, sem criptografia, e a pasta `data/` está no `.gitignore`. Não publique esse arquivo. Para backup, feche a Yuna e copie a pasta `data/` para um local privado.

## Configuração

Modelo padrão: `qwen2.5:3b`. Para experimentar outro modelo local já baixado, na mesma janela do PowerShell:

```powershell
$env:YUNA_MODEL = "nome-do-modelo-local"
py -3 yuna.py
```

Use modelos locais, não variantes cloud, para manter a conversa no computador. A primeira resposta pode demorar ao carregar o modelo. Em caso de erro de conexão, abra o Ollama; se necessário, execute `ollama serve`. Se o modelo não existir, execute o comando `ollama pull` indicado pelo programa.

Fechar o terminal encerra a Yuna. Ela não instala inicialização automática nem tarefa agendada. O aplicativo Ollama pode continuar aberto; o modelo recebe um tempo de permanência de dois minutos após cada solicitação. Para interrompê-lo imediatamente: `ollama stop qwen2.5:3b`.

## Etapas

- [x] Conversa local por texto e tratamento de erros.
- [x] Histórico persistente e memórias explícitas com exclusão.
- [ ] Voz feminina em português brasileiro: escolher timbre e motor de síntese.
- [ ] Entrada por microfone e ativação por voz.
- [ ] Pesquisa na internet e integração com projetos.
- [ ] Monitoramento de hardware e ações autorizadas no computador.

Nesta base não há reconhecimento de locutor, navegação web, edição automática de arquivos ou integração com GitHub. Há ações locais limitadas para abrir pastas; respostas do modelo são apenas texto e nunca são executadas.

## Desenvolvimento e validação

```powershell
py -3 -m unittest discover -s tests -v
```

Os testes usam respostas HTTP simuladas e banco temporário: verificam persistência, contexto, exclusão e erros sem baixar um modelo. Não substituem teste real do modelo ou teste no Windows.

Referências: [API de chat](https://docs.ollama.com/api/chat), [modelo inicial](https://ollama.com/library/qwen2.5:3b).


## Atualização 0.2 — conhecimentos em arquivo

`data/conhecimentos.json` é criado automaticamente e atualizado após cada conversa concluída ou mudança de memória. É uma cópia legível das memórias explícitas e do histórico completo; pode ser aberto no Bloco de Notas. O banco `data/yuna.db` continua sendo a fonte principal, carregada ao iniciar. Não edite o JSON para alterar memórias: use `/lembrar` e `/esquecer`. A cópia é regenerada a partir do banco.

Além das últimas seis trocas, a Yuna agora busca até quatro falas antigas do usuário com palavras em comum com a pergunta. Isso funciona após reiniciar e ajuda a recuperar assuntos antigos, mas é uma busca simples: paráfrases sem palavras em comum podem não ser encontradas. Use `/lembrar` para fatos que devem sempre entrar no contexto. Respostas do modelo ficam no histórico, sem virarem fatos confirmados automaticamente. Não há treinamento automático do modelo.

**Para atualizar sem perder memória:** feche a Yuna, faça backup privado da pasta `data`, baixe e extraia o ZIP novo em outra pasta e copie os arquivos de código para a pasta antiga da Yuna, substituindo-os. Preserve a pasta `data` antiga. Abra `iniciar_yuna.bat` na mesma pasta de sempre. O JSON será gerado com o banco existente. Abrir uma cópia nova sem a pasta `data` cria uma memória vazia.

O arquivo contém suas conversas: não publique `data` no GitHub. `/nova` apaga histórico e as falas recuperáveis, preservando memórias explícitas; `/apagar CONFIRMAR` remove ambos também da cópia JSON. Mensagens interrompidas antes de uma resposta concluída não são salvas nesta versão.


## Versão 0.3 — primeiras ações no notebook

Digite na janela da Yuna:

```text
Yuna, abra o explorador
Yuna, abra meus downloads
Yuna, abra o explorador e vá até a pasta downloads
Yuna, verifica o explorador abra ele e va ate a aba download
Yuna, abra meus documentos
```

Também há atalhos exatos: `/abrir downloads`, `/abrir explorador` e `/abrir documentos`. Os pedidos reconhecidos funcionam sem precisar do modelo carregado. O Windows resolve as pastas especiais, inclusive quando redirecionadas. A aplicação solicita a abertura e você confere a janela; ela ainda não observa a tela nem confirma visualmente que abriu. Não depende de cliques em coordenadas ou da posição da aba.

A interpretação dessas ações usa frases predefinidas, não raciocínio autônomo. Outras formas de pedir podem cair no chat: nesse caso use `/abrir downloads`. Nenhum texto gerado pela IA vira comando do sistema. Não há permissão administrativa necessária nem execução de comandos livres. Na versão 0.4 há busca por nomes e abertura de documentos selecionados; a busca não lê o conteúdo dos arquivos.

**Atualizar:** feche a Yuna e substitua `yuna.py` e `computer.py` na pasta antiga pelas versões novas. Preserve `data/`. Abra `iniciar_yuna.bat` normalmente. Não precisa baixar o modelo novamente nem instalar pacotes adicionais.

O chamado pelo microfone e a resposta com voz feminina ainda não estão implementados. Digitar “Yuna” é opcional. Os testes automatizados simulam a abertura do Explorador: a integração real precisa ser validada no seu Windows.


## Versão 0.4 — busca no computador

**Para instalar esta atualização, copie os dois arquivos `yuna.py` e `computer.py` para a mesma pasta antiga. Preserve `data/`.** Não há novos pacotes para instalar.

Exemplos digitados:

```text
Yuna, procure meu currículo
Yuna, procure Kaizen em todo o computador
Yuna, abra meu currículo
Yuna, abra o resultado 2
Yuna, abra o primeiro
/buscar relatório
/buscar tudo Kaizen
/abrir 1
/localizar 1
```

- A busca compara palavras com **nomes**, ignorando maiúsculas e acentos. Não lê conteúdo de PDFs, documentos ou imagens, nem entende descrições sem palavras presentes no nome.
- A busca padrão cobre a pasta do usuário e suas subpastas. `tudo` ou `em todo o computador` amplia para as unidades que o Windows identifica como discos fixos, priorizando a pasta do usuário. Unidades de rede e removíveis não entram nessa opção.
- Uma solicitação para abrir um nome desconhecido primeiro apresenta uma busca; você escolhe o resultado pelo número. Resultados ficam em memória apenas até a próxima busca ou até fechar a Yuna. `/nova` também limpa essa seleção.
- `/abrir NUMERO` abre pastas ou documentos, imagens e mídias de extensões permitidas no aplicativo padrão do Windows. Arquivos executáveis, scripts, atalhos e outros tipos não são executados. `/localizar NUMERO` abre a pasta que contém qualquer resultado.
- A busca percorre até 100 mil entradas, 50 resultados ou aproximadamente 20 segundos (uma chamada de disco lenta pode demorar mais). Ela informa quando o resultado é parcial. Ctrl+C interrompe a busca e preserva os resultados já encontrados. Não há índice nem retomada automática; a próxima busca inicia de novo.
- Pastas de sistema (`Windows`, `Program Files`, `Program Files (x86)`, `ProgramData`, lixeira, `System Volume Information`), `AppData`, caches (`.cache`) e dependências (`node_modules`, `.git`, `.venv`, `venv`, `__pycache__`) são ignoradas. Links e pontos de redirecionamento também são ignorados, inclusive alguns itens do OneDrive. Locais sem permissão são pulados. Portanto a busca ampla **não garante cobrir todos os arquivos**.
- Esta busca é feita localmente pelo código. As listas de caminhos não são enviadas ao modelo nem armazenadas nas memórias. O programa não apaga, move ou edita resultados.
- Ctrl+C durante uma resposta agora retorna ao prompt, sem fechar a Yuna. O Ollama pode continuar a geração em segundo plano; para interrompê-lo, use `ollama stop qwen2.5:3b` em outra janela. `/sair` fecha o aplicativo.

Esta etapa usa reconhecimento de pedidos e ferramentas locais, não consciência ou controle visual autônomo. Ainda não há microfone. APIs de referência: [tipos de unidade do Windows](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdrivetypew) e [abertura de arquivos no Python](https://docs.python.org/3/library/os.html#os.startfile).

Os testes incluem busca em pastas temporárias, acentos, exclusões, limites, cancelamento, itens removidos e seleção de resultados. A abertura de aplicativos e descoberta de unidades no Windows ainda precisam de validação no notebook real.
