# Plano Yuna VTuber — avatar vivo sem trocar o cérebro

**Status:** decisão arquitetural proposta, **não implementada**. Base existente: Yuna 0.26, Python + PySide6, Ollama, SQLite, avatar vetorial 2D, TTS Windows/Edge e medição de amplitude WAV. Data da análise: 28/10/2026.

## Repositórios estudados

| Projeto | O que aproveitar conceitualmente | Cautela |
| --- | --- | --- |
| [moeru-ai/airi](https://github.com/moeru-ai/airi) | Arquitetura com renderizadores Live2D/VRM, personagens como componentes separados, expressões, áudio e estado de sessão | Stack TypeScript/Electron maior que a Yuna; código MIT, ativos e dependências podem ter outras licenças |
| [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) | Fluxo ASR → LLM → TTS, interrupção da fala, modo pet transparente, mapeamento de emoções para gestos | Código MIT, **modelos Live2D de amostra sob termos próprios**; memória longa do projeto não deve ser confundida com SQLite da Yuna |
| [liupig/xiaokeai](https://github.com/liupig/xiaokeai) | Renderer Three.js com `@pixiv/three-vrm`, movimentos, blink, olhar, expressão e lip-sync; cena separada da IA | Código Apache-2.0, arquivos 3D/movimentos/vozes de terceiros têm direitos separados; três formatos de modelos aumentam complexidade |
| [jofizcd/Soul-of-Waifu](https://github.com/jofizcd/Soul-of-Waifu) | Experiência de companion desktop, personalidade e diferentes reações visuais | GPL-3.0: **estudar ideias, não copiar código** sem revisão de compatibilidade e obrigações |
| [heshengtao/super-agent-party](https://github.com/heshengtao/super-agent-party) | Camada de avatar como componente, ações e expressões, possibilidade de VTube Studio externo | AGPL-3.0: não transplantar código sem revisão; muitas integrações seriam excessivas para a Yuna |
| [Inochi2D](https://github.com/Inochi2D/inochi2d) | Alternativa aberta para rigging 2D com camadas, deformação e parâmetros | Seu formato é **incompatível** com Live2D; precisaria de renderer/integração própria |

**Não importar modelos, texturas, vozes, animações ou personagens de amostra** dos repositórios sem confirmar permissões para redistribuição, inclusive uso comercial. Verificar os direitos de cada ativo individual; as licenças do código-fonte não cobrem automaticamente os assets. A identidade visual da Yuna deve usar arte/modelo original licenciado adequadamente.

## Decisão principal

**Manter o backend da Yuna em Python** (Ollama, memória SQLite, ferramentas, chat PySide6). Trocar somente o modo de exibir a personagem mediante um contrato de eventos pequeno. O renderer atual continua sendo a opção padrão e **fallback obrigatório** em máquinas leves.

Arquitetura proposta:

```text
[Usuário: chat ou microfone sob comando]
             ↓
[STT / Yuna Python / Ollama / Memória / Ferramentas autorizadas]
             ↓
         [TTS e player]
             ↓ eventos verificados
 [AvatarController — máquina de estados + fila de eventos]
       ├── Qt2DRenderer atual (padrão / 8 GB)
       ├── Layered2DRenderer futuro (arte própria em camadas)
       └── VRMRenderer futuro (Three.js / @pixiv/three-vrm, opt-in)
```

Sem adicionar Electron, navegador de fundo ou outro LLM ao caminho padrão. Renderer 3D deve carregar **só quando ativado**, poder desligar sem fechar a conversa e nunca ter acesso direto às memórias, token de API, shell, câmera ou arquivos arbitrários.

## Contrato de eventos proposto

Criar camada Python separada e testável de Qt com os comandos abaixo. Somente o controlador pode solicitar eventos; o renderer não executa ferramentas.

| Evento | Dados | Resultado esperado |
| --- | --- | --- |
| `avatar.pose` | `idle, walk, sit, sleepy, wave, wink, laugh, shy, angry, surprised` + duração | Gesto temporário, retorna a idle; prioridade definida |
| `avatar.emotion` | `neutral, happy, shy, sad, surprised, annoyed` + intensidade [0..1] | Expressão ilustrativa; não inferir sentimentos reais de usuários |
| `speech.started` | identificação de segmento/reprodução | Só animar a boca quando o player iniciar de fato |
| `speech.level` | posição do áudio em ms + amplitude [0..1] | Lip-sync por intensidade com silêncios e limites, sem prometer fonemas |
| `speech.ended` | id de reprodução | Fechar boca, limpar estado e liberar próximo áudio |
| `speech.interrupted` | id de reprodução | Parar áudio, invalidar eventos atrasados e fechar boca imediatamente |
| `avatar.look_at` | coordenada local normalizada | Olhar suavizado; não gravar trajetória do cursor |
| `avatar.appearance` | referência validada a preset local | Atualizar cabelo, roupa, cores e acessórios de arquivos próprios |

**Regras:** eventos ordenados por sequência e identificador da fala; TTS antigo não deve reabrir a boca depois de interrompido. Nunca executar scripts ou ações retornados por texto do modelo. Não enviar microfone, captura de tela ou conversa a fornecedores sem opt-in explícito. Streaming por frase e cancelamento precisam ser implementados e testados antes de habilitar conversa hands-free.

## Perfil de desempenho

- **Leve (máquina com 8 GB RAM):** manter `YunaAvatar`/QPainter 2D com 15–30 FPS adaptáveis e áudio local. Não carregar QtWebEngine, VRM nem serviços de visão em segundo plano. Permitir reduzir animação e pausar render quando janela está oculta.
- **Visual 2D melhorado:** personagem **original** com desenho separado por partes (rosto, olhos, boca, cabelo, roupas, braços), interpolação e expressões; implementação pode ser QPainter em camadas inicialmente. Avaliar Inochi2D ou Live2D só depois de um protótipo e revisão das licenças/SDK.
- **3D opcional (máquina com GPU):** um renderer isolado com **Three.js + @pixiv/three-vrm**, usando arquivo `.vrm` próprio. Considerar QWebEngineView via dependência opcional **somente após medir consumo, transparência e compatibilidade Windows**. VRM não deve ser obrigatório e não deve iniciar no modo de 8 GB por padrão. Adiar MMD/PMX, física pesada e câmera.

Não há benchmarks da Yuna 3D nas máquinas reais ainda; as metas de FPS são **alvos de engenharia**, não resultados medidos.

## Como criar a aparência da Yuna

Identidade visual original sugerida: personagem anime gótica feminina, cabelos e olhos configuráveis, figurinos e acessórios salvos em `data/avatar_yuna.json`. Criar model sheet próprio antes de rigging. Para 3D, é possível criar uma base com VRoid Studio e exportar VRM, **revisando regras sobre conteúdo padrão e de terceiros**; não redistribuir modelos alheios.

O comando **“Yuna, muda o cabelo para branco”** deve editar o estado do avatar e atualizar o renderer ativo; não modificar arquivos 3D diretamente sem confirmação. Presets de roupas/cabelo devem ser compatíveis com o tipo de renderer e ter fallback amigável.

## Sequência de implementação

1. **0.27 — AvatarController:** novo contrato de eventos, estado observável, testes sem Qt, adaptação do renderer 2D atual sem mudar a aparência. Pausas, eventos antigos e cancelamento devem ter testes de regressão.
2. **0.28 — Voz realmente interativa:** botão pressionar-para-falar, áudio por segmentos, botão interromper fala e fim de áudio sincronizado; sem microfone sempre ativo por padrão. Adicionar VAD/escuta contínua apenas com opção explícita.
3. **0.29 — Arte 2D em camadas:** loader local de sprites/licenças verificadas, expressões e boca por estados, seleção de presets, fallback vetor existente.
4. **0.30+ — VRM experimental:** renderer 3D opcional com `three-vrm`, modelo original, mapeamento de blink/expressões/boca, câmera virtual, desempenho e fallback automático.
5. **Somente depois:** movimentos de caminhar mais avançados, física simples, novas roupas, editor de personagem e possivelmente distribuição empresarial.

## Critérios de aceite de cada etapa

- Testes automatizados Windows/Qt e testes para cancelamento, arquivos ausentes, fallback e memória inalterada.
- Falar sem voz escolhida **não** anima lábios; síntese sem reprodução **não** anima lábios; ao interromper, boca fecha.
- A atualização **não toca** `data/yuna.db`, `data/avatar_yuna.json` nem conteúdo da biblioteca sem ação explícita.
- O modo leve abre sem Node/Electron/QtWebEngine/modelos 3D instalados.
- A versão 3D só é anunciada como concluída **depois de testada no Windows real**; sem prometer compatibilidade com qualquer GPU.
- Manter inventário de licenças do código externo e de cada asset. Não incorporar modelos de exemplo com restrições como se fossem livres.

## Fontes e licenças verificadas

- AIRI: https://github.com/moeru-ai/airi/blob/main/LICENSE (MIT para o repositório principal)
- Open-LLM-VTuber: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/LICENSE (MIT com exclusão de amostras Live2D) e https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/LICENSE-Live2D.md
- Xiaokeai: https://github.com/liupig/xiaokeai/blob/master/NOTICE (Apache-2.0 para código; assets de terceiros separados)
- Soul-of-Waifu: https://github.com/jofizcd/Soul-of-Waifu/blob/main/LICENSE (GPL-3.0)
- Super Agent Party: https://github.com/heshengtao/super-agent-party/blob/main/LICENSE (AGPL-3.0)
- Three-VRM: https://github.com/pixiv/three-vrm (MIT)
- Inochi2D: https://github.com/Inochi2D/inochi2d
- VRoid Studio diretrizes: https://vroid.com/en/studio/guidelines

Este documento descreve uma arquitetura própria da Yuna, inspirada por funcionalidades, e não copia código dos projetos citados.
