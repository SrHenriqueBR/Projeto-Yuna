# Yuna 0.54 — Busca semântica, memória Ollama, eventos Windows e OSV

[← README](../README.md) · [Índice de documentação](README.md)

Estas integrações são executadas **somente quando você usa os botões**
da aba **Central da Yuna → Integrações**. Não existe coleta permanente,
varredura automática de arquivos ou cobrança de APIs comerciais.

## 1. Memória inteligente: busca local em documentos (RAG)

1. Na janela completa da Yuna, escolha um documento e use o botão
   **Guardar na Biblioteca**. O arquivo precisa estar entre DOCX,
   PDF com texto, XLSX, PPTX, TXT ou Markdown e dentro dos limites
   existentes de leitura. **A Yuna não procura arquivos sozinha.**
2. Abra **Central → Integrações → Preparar EmbeddingGemma**.
   Confirme o download de aproximadamente **622 MB**, proveniente
   do catálogo público do Ollama: https://ollama.com/library/embeddinggemma.
   A instalação exige internet, mas a inferência posterior é local.
3. Clique em **Indexar documento já guardado** e selecione o arquivo.
   Confirme que deseja armazenar seus trechos e embeddings
   exclusivamente em `data/yuna_rag.sqlite`.
4. Clique em **Pesquisar nos documentos indexados**, digite a pergunta
   e leia os trechos com nomes de arquivo e pontuação aproximada.
5. Para apagar todo o índice, clique em **Apagar somente índice
   semântico**. A operação não apaga o banco de conversas/memórias
   `data/yuna.db` nem os documentos guardados.

A busca é uma primeira etapa de *retrieval*, **não treina o modelo**,
não usa internet e **não gera automaticamente resposta do LLM**
com esses dados. Só indexa o texto que os leitores de documentos
conseguem extrair (no máximo 18 mil caracteres por documento).
Trechos não são instruções operacionais, e nenhum comando dentro
dos arquivos é executado. Se a biblioteca for removida, os resultados
de arquivos ausentes deixam de ser exibidos; o índice pode ser
apagado separadamente pelo usuário.

**API local:** `POST http://127.0.0.1:11434/api/embed`, usando
`embeddinggemma`. A Yuna não faz requisições a serviços externos
para construir embeddings. Documentação:
https://docs.ollama.com/api/embed.

## 2. Memória RAM/VRAM do Ollama

Na mesma aba, use **Ver modelos carregados no Ollama**. A Yuna lê
`GET /api/ps`, mostra nomes e uso informado pelo Ollama.
Para liberar um modelo, clique **Descarregar um modelo da memória**,
digite o nome exato apresentado na lista e confirme.

A ação chama `POST /api/generate`, com `keep_alive=0`, somente
se o modelo for encontrado entre os já carregados. **Ela não remove
arquivos do disco, não altera o modelo padrão nem fecha o serviço
Ollama**. Caso haja outra aplicação usando o mesmo servidor, ela
poderá sentir a liberação e precisar recarregar o modelo.
A memória efetivamente liberada depende do Ollama e de outras tarefas.

A Yuna nunca descarrega o modelo automaticamente ao entrar em
economia na bandeja. Fontes:
https://docs.ollama.com/api/ps
e https://docs.ollama.com/api/generate.

## 3. Diagnóstico de logs do Windows

Clique **Eventos do sistema** ou **Eventos de aplicativos**.
A Yuna consulta somente `System` ou `Application`, filtrando
níveis de aviso/erro/crítico nas últimas 24 horas, no máximo
15 eventos. O relatório contém apenas **quando, provedor, código,
nível**. Não copia o campo de mensagem, nome de usuário, detalhes
de arquivos ou credenciais.

Implementação: PowerShell `Get-WinEvent`, leitura sob sua conta
atual e sem elevação automática. Alguns logs podem não estar
acessíveis ou não possuir eventos recentes; não são interpretados
como falha geral do Windows. Nenhuma correção ou comando de
reparo é executado automaticamente.

Referência: https://learn.microsoft.com/powershell/module/microsoft.powershell.diagnostics/get-winevent

## 4. Vulnerabilidades de dependências: OSV.dev

Em **Consultar vulnerabilidade de pacote PyPI / npm**, informe
ecossistema, nome público e **versão exata** de uma dependência.
A Yuna faz uma requisição a `https://api.osv.dev/v1/query`
e resume até 10 identificadores/descrições, citando a fonte.

- **Não exige chave nem pagamento** para consultas normais; há
  limites operacionais externos e eventual indisponibilidade.
- Só o nome/ecossistema/versão fornecidos são enviados ao serviço.
  **Nenhum arquivo, repositório privado, token ou lockfile** é enviado.
- Não instala ou atualiza bibliotecas nem executa scripts sugeridos
  no resultado.
- Nenhuma vulnerabilidade encontrada **não comprova** segurança.
  Confirme alertas e versões de correção nas fontes oficiais.

Documentação: https://google.github.io/osv.dev/post-v1-query/

## Controles e limites

**Custo:** Ollama e modelos locais não cobram por mensagem,
mas downloads e processamento consomem internet, RAM/VRAM,
disco e energia. O único serviço externo novo é OSV.dev, gratuito
para consultas públicas; requer conexão apenas quando utilizado.

**Privacidade:** todas as funções precisam ser chamadas explicitamente
pela pessoa. RAG guarda trechos dos documentos em uma segunda base
local, que pode conter informações privadas — mantenha a pasta
`data` protegida e fora de backups públicos. Não envie conteúdo
dos seus documentos a serviços externos sem consentimento separado.

**Limitações:** não há correções automáticas de software, navegação
na internet contínua, indexação de tela/câmera, treinamento de modelo,
consulta automática de CVEs nem monitoramento oculto de terceiros.
