# Revisão de estabilidade — Yuna 0.54.1

[Voltar ao projeto](../README.md) · [Instalação no Windows](INSTALACAO_WINDOWS.md)

Esta versão mantém os recursos da 0.54.0 e corrige falhas reproduzidas na revisão.
Atualize usando o instalador no mesmo local, com a Yuna fechada. Preserve seu backup
privado de `data/`; não substitua arquivos Python isolados entre versões.

| Situação | Correção |
| --- | --- |
| Clicar em Parar e depois analisar outro documento não mostrava a nova análise | Cada pedido usa seu próprio identificador de cancelamento; uma nova análise é aceita normalmente. |
| Enviar outra mensagem após Parar podia fazer a análise antiga reaparecer | Respostas, erros e progresso de pedidos cancelados são descartados. |
| Uma conversa interrompida podia ser gravada ao terminar ou iniciar uma segunda revisão de português | O cancelamento é conferido depois da inferência e antes da revisão e da gravação da resposta. |
| Qwen3.5 podia gastar os 384/768 tokens no campo de raciocínio e retornar conteúdo vazio | As requisições dessa família enviam `think: false`, inclusive em respostas estruturadas. Outros modelos manuais preservam seu comportamento. |
| O chat permitia seguir um redirecionamento retornado pelo serviço Ollama | O endpoint continua fixo em `127.0.0.1`; proxy e redirecionamentos são recusados. |
| Ollama fechado ou modelo ausente apareciam no desktop apenas como erro desconhecido | O chat preserva as instruções de recuperação da Central, sem expor o corpo de erro do serviço. |
| A cópia de um índice `.sqlite` com dados recentes no WAL perdia esses registros | A migração utiliza backup SQLite para `.db`, `.sqlite` e `.sqlite3`, mantendo a origem. |
| Indexação de um documento longo parecia cobrir o arquivo inteiro | A Central agora mostra os avisos de leitura parcial e os limites do extrator. |
| Níveis de eventos como “Crítico” podiam aparecer com acentos quebrados | O PowerShell emite UTF-8 explicitamente. Ausência de eventos tem mensagem própria. |
| As propriedades de `Yuna.exe` ainda indicavam 0.51.1 | O build gera os metadados a partir da mesma versão utilizada pelo aplicativo. |

## Limites que permanecem

- Parar cancela a fila e descarta resultados antigos. Uma chamada externa já
  iniciada pode continuar até retornar ou atingir seu timeout; não há promessa
  de interromper imediatamente o processamento do Ollama. A próxima tarefa
  aguarda essa chamada liberar a thread.
- Ações de PC já concluídas não são desfeitas. Registros de ações reais da
  interface e documentos já guardados com autorização são preservados.
- A busca semântica usa o texto extraído, com os limites de formato e de 18 mil
  caracteres. Não realiza OCR nem indexa pastas automaticamente.
- Microfone, câmera, USB, jogos e velocidade do modelo dependem de teste no
  computador de destino. Testes simulados não substituem esse teste de hardware.

## Como verificar

`tests/test_review_regressions.py` cobre os cenários de cancelamento, a requisição
Qwen3.5, a restrição de redirecionamento, a migração de WAL e o aviso de texto
parcial. No Windows, executa também o PowerShell real com eventos fictícios,
sem consultar logs pessoais. O teste do instalador verifica se a versão do
executável coincide com a do código, além de abrir a interface e conferir
instalação, migração, atualização e desinstalação com preservação de dados.

Referências do comportamento do modelo:
[Thinking na API Ollama](https://docs.ollama.com/capabilities/thinking) e
[Qwen3.5 no Ollama](https://ollama.com/library/qwen3.5).
