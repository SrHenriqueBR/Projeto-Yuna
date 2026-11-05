Um aplicativo para abrir a Yuna e acessar seus recursos pela Central.

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
seleção só é salva após um download confirmado e concluído. Reinicie a Yuna
para aplicar o novo modelo.

Modelos de conversa/Whisper são downloads separados; hardware precisa ser conferido
no computador onde o aplicativo será usado.
