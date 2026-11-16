Um aplicativo para abrir a Yuna e acessar seus recursos pela Central.

**Yuna 0.56.0 — caderno de ensino local**

- Tela **Central → Minha Yuna → Ensinar a Yuna** para salvar, editar e apagar exemplos revisados.
- **/ensinar PERGUNTA => RESPOSTA** e **/corrigir RESPOSTA CORRETA** no chat, com persistência no SQLite.
- Recuperação de exemplos relevantes; uma correção substitui a lição anterior e remove a resposta antiga do contexto, preservando o histórico.
- 12 guias práticos do projeto e avaliação local com 36 casos de recuperação, sem executar o modelo.
- Exportação JSONL somente das lições selecionadas, sem copiar automaticamente conversas, documentos ou memórias.
- Ensino não executa comandos, não envia dados à escola pública e não altera pesos do Qwen.
- Mantém voz por frase, seleção de microfone, Qwen3.5:4b, perfil máximo e pesquisa com fontes da versão 0.55.

Guia: [como ensinar e testar](https://github.com/SrHenriqueBR/Projeto-Yuna/blob/main/docs/ENSINAR_YUNA.md).

Baixe **Yuna-Setup.exe**, instale na sua conta do Windows e abra **Yuna.app** pelo atalho.
O instalador inclui o runtime, interface, documentos, bibliotecas de voz e renderizador 3D.
Não precisa instalar Python ou Node.js separadamente. Para conversa livre, instale/abra
o Ollama e prepare um modelo em **••• → Central da Yuna → Preparação**.

Microfone, câmera e jogos mantêm autorização por sessão. Inicialização com Windows é
opcional. O instalador oferece copiar a pasta `data` de uma instalação antiga sem
apagar a origem. Atualizar ou desinstalar preserva dados pessoais que já existam.

Windows 10/11 x64. Pacote sem certificado de assinatura de código comercial; o Windows
pode exibir editor desconhecido. `SHA256SUMS.txt` identifica o arquivo desta release.
**Novidade 0.52.0:** integração local Qwen3.5 por Ollama, com escolha explícita
de **2B (leve)**, **4B (recomendado)** e **9B (avançado)** na Central da Yuna.
Sem API Qwen paga, cadastro comercial ou cobrança por mensagens. Os modelos
Qwen2.5 anteriores continuam disponíveis; não há troca automática, e a
seleção só é salva após um download confirmado e concluído. A seleção vale na próxima resposta.

**Novidade 0.54.0:** nova aba **Integrações** com busca local de documentos
arquivados por EmbeddingGemma + Ollama, gerenciamento manual de modelos
carregados em RAM/VRAM, leitura limitada de eventos do Windows e consultas
explícitas à base pública OSV.dev por pacote/versão. Sem API de IA paga,
sem indexar pastas sem consentimento e sem iniciar reparos automaticamente.
Consulte docs/INTEGRACOES_054.md.

**Novidade 0.53.0:** ícone da Yuna na bandeja do Windows com estados
Ativa, Econômica, Acompanhamento leve (USB/energia/bateria/RAM/disco locais) e
Pausada. Clicar abre chat compacto; clicar com o botão direito abre
o controle. Fechar a janela ativa economia com pausas nas verificações
de USB e menor frequência de bateria. O modo de acompanhamento
depende de escolha explícita, não liga câmera ou microfone nem
envia dados a modelos automaticamente. "Sair da Yuna" encerra o
processo e o monitoramento. Ollama separado pode manter RAM/VRAM
ocupadas mesmo em economia.

Modelos de conversa/Whisper são downloads separados; hardware precisa ser conferido
no computador onde o aplicativo será usado.
