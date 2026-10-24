# Projeto Yuna · Base 0.1

Assistente pessoal local para Windows. Esta primeira etapa oferece conversa por texto no terminal e memória persistente em SQLite. **A voz será feminina, em português brasileiro, na próxima etapa. Ainda não há áudio nem microfone.**

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

Nesta base não há reconhecimento de locutor, navegação, execução de comandos, edição automática de arquivos ou integração com GitHub. Respostas que sugiram ações são apenas texto.

## Desenvolvimento e validação

```powershell
py -3 -m unittest discover -s tests -v
```

Os testes usam respostas HTTP simuladas e banco temporário: verificam persistência, contexto, exclusão e erros sem baixar um modelo. Não substituem teste real do modelo ou teste no Windows.

Referências: [API de chat](https://docs.ollama.com/api/chat), [modelo inicial](https://ollama.com/library/qwen2.5:3b).
