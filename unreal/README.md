# Yuna Unreal — C++ e Animation Blueprints (experimental)

Este projeto implementa a ponte do AvatarController Python para um ator de personagem em **Unreal Engine 5**, sem substituir o Ollama, a memória SQLite, o chat, a voz ou os renderizadores já existentes.

**Importante:** estão implementados a comunicação de estado, o ator C++ e as animações procedurais básicas (respiração, oscilações, piscadas, boca por amplitude se existir morph target e sinais de gestos). **Não acompanha modelo de anime rigado, AnimBlueprint pronto, mapa criado no editor nem build compilado do Unreal**. Esses elementos exigem o Unreal Editor e arquivos artísticos. A suíte GitHub Actions testa Python/Qt, **não compila o C++ do Unreal**.

## Arquitetura

1. **Yuna Desktop / Ollama / Python:** continua a processar a conversa, a memória e as ferramentas com as mesmas permissões.
2. **AvatarController:** publica somente eventos de pose, emoção e amplitude da reprodução real da voz.
3. **UnrealStateBridge:** ao clicar em Conectar Yuna Unreal, grava um JSON sanitizado e atômico em **data/yuna_unreal_state.json**, até aproximadamente 10 vezes por segundo durante fala.
4. **AYunaAvatarActor em C++:** lê apenas esse arquivo local, valida a versão, os campos e o horário, e aplica animações ambientes e morph targets.
5. **UYunaAnimInstance:** expõe Signals ao Animation Blueprint para controlar ossos, movimentos, olhar e gestos.
6. **Avatar VRM original:** precisa ser importado pelo usuário com rig e nomes corretos dos morph targets.

A ponte não abre portas nem envia áudio bruto, textos de conversas, tokens, vídeos, arquivos do usuário ou comandos. A Yuna remove o estado local ao desconectar/fechar. O Unreal ignora estados com mais de 3 segundos de idade e retorna ao repouso quando a Yuna desconecta.

## Yuna 0.46 — corpo articulado sem montar o AnimGraph primeiro

O ator `AYunaAvatarActor` tem agora um segundo componente
**DirectBoneMesh (Poseable Mesh)** e a opção **bDirectBonePreview**
(ativada por padrão). Depois que você vincular seu **Skeletal Mesh VRM**
em `AvatarMesh`, a Yuna tenta encontrar automaticamente os ossos
da cabeça, peito, braços, pernas, olhos e uma mecha do cabelo.
São reconhecidos vários nomes comuns do VRoid (`J_Bip_...`) e VRM.
Se o rig for diferente, escolha os nomes no painel **Yuna | Bones**.

Na execução **Play**, o Unreal copia a pose-base do personagem e
aplica diretamente as rotações dos ossos conforme `YunaMotion.h`,
**sem precisar criar um Animation Blueprint para testar os gestos**:

- Olhar espontâneo com pequenas pausas, cabeça e olhos articulados
- Respiração com movimento suave do tronco e pequenos ajustes de postura
- Aceno real do braço e alternância dos braços e pernas ao caminhar
- Timidez, curiosidade, irritação, piscadinha e descanso como sinais
- Gestos temporários: um aceno volta ao estado neutro após alguns segundos
- Campo `has_amplitude` distingue WAV com envelope real da voz
  de síntese sem envelope (animação aproximada apenas durante reprodução)

**Limitação importante:** o modo DirectBoneMesh usa `UPoseableMeshComponent`,
que oferece transformação direta dos ossos, **mas não replica
automaticamente morph targets, AnimGraph nem as físicas/spring bones
do SkeletalMesh original**. Assim, o corpo/cabeça podem se mexer
enquanto as pálpebras e a boca ainda não deformam visualmente.
Os sinais `Signals.BlinkLeft`, `BlinkRight`, `Mouth`, `EyeYaw`,
`HeadTilt`, `Wave` etc. já são calculados e expostos ao Blueprint.

Para usar expressões faciais, fala e física no modelo definitivo,
**desmarque `bDirectBonePreview`** no ator e configure um **Animation
Blueprint derivado de `UYunaAnimInstance`**. Nesse modo são aplicados
morph targets para boca, piscadas e sorriso, além de expor os movimentos
para o AnimGraph (que você ainda precisa configurar). Os nomes dos
morph targets variam conforme o VRM importado.

O modo direto é uma etapa de teste para **movimentos reais do rig**,
não substitui o trabalho artístico de uma personagem VTuber finalizada.

## Instalar no Windows

1. Instale **Unreal Engine 5.7** pelo Epic Games Launcher e as ferramentas C++ para jogos do Visual Studio. Esta é a versão de projeto configurada; não garantimos compilação em outra versão sem ajuste nem testamos o Unreal nesta máquina.
2. Mantenha a estrutura completa do repositório; o projeto está em **unreal/YunaUnreal/YunaUnreal.uproject**. O leitor busca a pasta **data/** dois níveis acima da pasta Unreal.
3. Abra o arquivo .uproject. Gere os arquivos de solução quando o Unreal solicitar e compile o módulo **YunaUnreal**.
4. Crie um nível básico no editor e salve-o no projeto.
5. Instale uma versão do **VRM4U** correspondente à sua versão do Unreal; consulte as releases oficiais: https://github.com/ruyo/VRM4U/releases . Extraia em **unreal/YunaUnreal/Plugins/VRM4U/**, de modo que o arquivo VRM4U.uplugin fique diretamente nessa pasta. A instalação e as licenças são independentes deste repositório.
6. Crie ou exporte seu próprio personagem anime como um arquivo .vrm com direitos de uso adequados. Importe-o no Unreal via VRM4U. Não fazemos download de modelos de terceiros nem os redistribuímos.
7. Crie um Blueprint derivado da classe **AYunaAvatarActor** e associe ao componente **AvatarMesh** o Skeletal Mesh da personagem. Coloque esse Blueprint no nível.
8. Confira no Skeletal Mesh os nomes dos morph targets e atualize no ator **BlinkMorphName**, **MouthMorphName** e **HappyMorphName**. Os defaults são Blink, A e Joy, mas diferentes VRMs usam nomes distintos.
9. Crie um **Animation Blueprint** com classe pai **UYunaAnimInstance**, use uma pose idle e nós **Transform (Modify) Bone** para olhar, cabeça, tronco e braços. Os sinais são **Signals.HeadYaw**, **Signals.HeadPitch**, **Signals.Breath**, **Signals.BodySway**, **Signals.Wave** e **Signals.Pose**. Os nomes e o retarget de ossos dependem da malha importada.
10. Clique **Play** no Unreal e depois, no aplicativo Yuna Desktop, clique **Conectar Yuna Unreal**. No Windows, esse clique também tenta abrir o arquivo .uproject. Teste botões de emoção e reprodução de voz na Yuna.

O ator faz pequenas oscilações enquanto está em repouso, mesmo quando a ponte Python não foi ativada. Entretanto, cabelo com física, gestos articulados e expressões faciais completas dependem de rig, spring bones e Animation Blueprints configurados, e não de uma imagem JPG/PNG.

## Testar a integração sem Unreal

Na raiz do repositório, execute estes comandos:

    py -3 -m unittest tests.test_unreal_state_bridge -v
    py -3 -m unittest tests.test_unreal_desktop -v

O segundo requer PySide6, se instalado. Os testes da ponte não abrem rede nem executam ações do Windows. O editor Unreal exige validação de compilação no Windows com o SDK instalado.

## Estrutura principal

- **unreal_state_bridge.py** — sanitização, arquivo atômico e limpeza do produtor Python.
- **unreal/YunaUnreal/** — projeto Unreal com C++ e configurações.
- **YunaAvatarActor.h/.cpp** — leitor JSON local e sinais de animação.
- **YunaAnimInstance.h/.cpp** — classe de Animation Blueprint.
- **YunaSignals.h** — estrutura de estados exposta ao Blueprint.
- **data/yuna_unreal_state.json** — estado efêmero, ignorado pelo Git.

## Web, licenças e desempenho

A prévia web existente continua em HTML/Three.js/VRM, independente da engine Unreal. Transmitir a **mesma renderização Unreal** para um navegador exigiria Pixel Streaming e uma GPU rodando uma sessão Unreal, com infraestrutura de streaming: **isso não está implementado**.

Unreal Engine segue termos/licença da Epic Games; VRM4U possui seus próprios termos e releases. Não use modelos, roupas ou texturas sem permissão. Sem custos de API obrigatórios na ponte local. O editor Unreal e seus assets costumam consumir muitos recursos: preserve o modo leve nos computadores com 8 GB de RAM.
