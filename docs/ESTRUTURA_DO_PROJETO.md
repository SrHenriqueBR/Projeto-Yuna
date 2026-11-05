# Mapa da estrutura do Projeto Yuna

Este documento explica **onde cada parte do código mora**, o que é entrada do
programa, o que é opcional e o que não deve ser apagado. Estado verificado na
versão **0.51.1**.

> A raiz contém módulos Python compartilhados. Eles estão nesse lugar por
> dependências de importação e pela montagem do instalador; simplesmente
> movê-los para pastas pode quebrar o desktop, a versão compacta, os testes e
> a distribuição. Esta organização **preserva os imports existentes**.

## Fluxo de inicialização

```text
USO DO INSTALADOR:
Releases/Yuna-Setup.exe → Yuna.exe → yuna_launcher.py
                                  → yuna_desktop.py
                                     ↕ yuna.py / Ollama / SQLite

USO DO CÓDIGO-FONTE:
Yuna.bat → scripts/iniciar.ps1 → .venv privado
                              → yuna_launcher.py
                              → interface e Central da Yuna
```

Há **um único arquivo BAT versionado**, `Yuna.bat`. Não abra scripts
internos de forma aleatória. Os inicializadores antigos são tratados
por `app_maintenance.retire_legacy_launchers` quando conhecido o nome;
o conteúdo de `data/` deve ser preservado.

## Pastas e responsabilidades

| Pasta/arquivo | Papel | Instalação / manutenção |
| --- | --- | --- |
| `Yuna.bat` | Entrada única do código-fonte | Não exclua |
| `scripts/iniciar.ps1` | Configura `.venv` e abre o launcher | Executado pelo BAT |
| `yuna_launcher.py` | Inicializa janela, apresenta erros, chama ferramentas autorizadas | Essencial |
| `yuna_desktop.py` | Interface Windows completa e acessos à Central | Essencial |
| `compact_chat.py`, `app_center.py` | Chat compacto e painel de preparação | Essenciais |
| `yuna.py` | Conversa, comandos de texto e memória | Essencial |
| `yuna_avatar.py`, `yuna_overlay.py`, `avatar_*.py` | Mascote 2D, animações e ponte visual | Mantidos na raiz |
| `voice.py`, `speech_input.py`, `voice_persona.py` | Voz, ditado e persona | Hardware/permissão podem ser necessários |
| `computer.py`, `app_tools.py`, `office_agent.py` | Ações permitidas, ferramentas e documentos | Não é controle irrestrito |
| `battery_life.py`, `plug_*.py`, `usb_devices.py` | Estados de alimentação e USB | Windows/hardware |
| `camera_*.py`, `remote_camera_invite.py`, `home_safety*.py` | Câmera, visualização consentida e proteção | Opt-in, não habilitar sem autorização |
| `avatar3d/` | Renderizador Three.js e importação privada de VRM | Opcional, pré-compilado no instalador |
| `unreal/` | Experimento C++ no Unreal Engine | Opcional, precisa de editor, SDK e rig |
| `docs/` | Guias, retrato oficial e demonstrações web | Material de referência |
| `packaging/` | Empacotamento/instalador e testes de distribuição | Para mantenedores |
| `scripts/` | Entrada PowerShell e ferramentas auxiliares | Não são BATs concorrentes |
| `tests/` | Testes Python e verificações | Execute antes de alterar o núcleo |
| `.github/workflows/` | CI, laboratório, escola e instalador | Algumas rotinas criam branches para revisão |
| `aprendizado/` | Escola e propostas revisáveis | Não substitui automaticamente o código |
| `data/` | SQLite, preferências, biblioteca pessoal e logs | **Privado, não versionado** |
| `.venv/`, `build/`, `dist/` | Dependências ou arquivos gerados | **Ignorados pelo Git** |

## Quais dados não devem ser publicados

- `data/`, especialmente `data/yuna.db`, imagens, anexos e históricos.
- `.env`, tokens de integrações, senhas e chaves de API.
- `avatar3d/public/yuna.vrm` e modelos VRM pessoais sem autorização
  expressa para redistribuição.
- Vídeos, capturas de câmera, gravações e dados de terceiros.

O `.gitignore` já protege as pastas principais. Mesmo assim, revise
qualquer `git add` antes de publicar.

## Organização da documentação

O [LEIA-ME principal](../README.md) serve como **porta de entrada**.
O [índice dos guias](README.md) reúne os assuntos.
O [guia completo preservado](GUIA_COMPLETO.md) retém descrições e comandos
anteriores que foram retirados do README principal para torná-lo curto.
As instruções normativas de instalação ficam em
[INSTALACAO_WINDOWS.md](INSTALACAO_WINDOWS.md).

## Como modificar sem quebrar o programa

1. Faça um branch e mantenha `data/` fora do Git.
2. Altere um componente de cada vez, sem realocar módulos Python só por
   aparência visual. Se for refatorar imports, atualize todos os pontos de
   entrada e os testes relacionados **na mesma alteração**.
3. Rode os testes do componente. Para o desktop, teste também com PySide6
   e Windows quando envolver Qt, áudio, instalador ou atalhos.
4. Para o avatar local: `cd avatar3d`, `npm install`, `npm test`
   e `npm run build`.
5. Para o Unreal: verifique o teste C++ em
   `unreal/tests/test_yuna_motion.cpp` **e compile o projeto dentro
   do Unreal Editor**. Compilar somente a matemática não valida a engine.
6. Atualize o README, a documentação do recurso e a versão **somente
   quando houver uma release de produto**. Mudanças de documentação
   não precisam recriar o instalador.
7. Use a revisão de Pull Request e os testes no GitHub antes de mesclar.

## Melhorias estruturais futuras (não aplicadas sem migração)

O projeto ainda pode ganhar pacotes Python internos (`yuna/core`,
`yuna/gui`, `yuna/integrations`) no futuro. Isso requer preservar
compatibilidade com caminhos do instalador, testes, imports, atalhos,
plugins e dados antigos; **não é uma operação segura de mover arquivos
isoladamente**. O mapeamento acima facilita essa evolução.
