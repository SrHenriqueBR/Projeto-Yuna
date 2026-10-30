# Criar a Yuna como personagem anime 3D

A prévia feita de esferas e cilindros é somente uma ferramenta de demonstração.
Para ter aparência profissional de anime, olhos expressivos, cabelo com física
e esqueleto articulado, a opção recomendada é criar uma personagem original
no **VRoid Studio** e exportá-la em **.vrm**. Não precisamos instalar no Python
um gerador de personagens realistas nem contratar uma API paga.

## Criar a personagem

1. Instale o VRoid Studio pelo site oficial: https://vroid.com/en/studio
2. Crie uma personagem anime original. Personalize rosto, olhos, cabelo,
   figurino e acessórios. Salve também o projeto editável **.vroid** em
   uma pasta privada para continuar a edição no VRoid Studio.
3. Use **Export VRM** (VRM 1.0), revise as informações e licenças
   dos elementos que usou e exporte **yuna.vrm**.
4. Na Yuna 3D em `http://127.0.0.1:5173`, clique **Importar minha
   Yuna .VRM**, escolha seu arquivo e teste os gestos.
5. Para que o avatar seja carregado automaticamente na inicialização,
   feche a prévia, crie a pasta **avatar3d/public** (se necessário),
   coloque uma cópia do seu **yuna.vrm** lá e abra novamente o
   `iniciar_yuna_3d.bat`. O servidor Vite local serve somente esse
   arquivo para sua própria prévia; não buscamos modelos na nuvem.
6. Abra o aplicativo desktop com `iniciar_yuna.bat` e clique
   **Conectar Yuna 3D** para sincronizar fala e gestos. A conexão
   permanece opcional e local.

**Atualizações:** preserve sua cópia de `avatar3d/public/yuna.vrm`,
seu `data/` e `assets/`. O ZIP do GitHub não inclui o arquivo de
personagem. Não o publique no GitHub sem avaliar os direitos do conteúdo.
O `.gitignore` já exclui arquivos `.vrm` dentro de avatar3d.

## Como deixar a personagem mais viva

- Pisca em tempos variados e às vezes duas vezes.
- Respira e muda discretamente a postura, braços, cabeça e cabelo.
- Olha ao redor mesmo sem o mouse se mover.
- Acompanha o cursor quando ele passa sobre a prévia.
- Reage a expressões e aos estados enviados pela Yuna Desktop.
- Quando o VRM oferece **Spring Bones**, o motor VRM atualiza a física
  durante a animação. A aparência e a qualidade dependem do modelo.
- A sincronização da boca ocorre durante a reprodução autorizada;
  continua aproximada e não é análise de fonemas.

A opção **Reduzir animações** desativa movimentos de repouso
para quem prefere menos movimento, incluindo a preferência do sistema.

## Sobre os repositórios GitHub enviados

- https://github.com/topics/3d-character — catálogo de projetos variados;
  é útil como inspiração, mas não é um modelo anime específico.
- https://github.com/Human3DAIGC/Make-A-Character — pesquisa de
  geração de personagens **realistas**. No repositório consultado
  encontram-se README e imagens de demonstração, não uma implementação
  completa de geração 3D para copiar para Yuna. Não importamos
  material nem código desse projeto, cuja licença para reutilização
  não está especificada no repositório.
- Para a Yuna, mantemos a arquitetura já existente: **Three.js +
  @pixiv/three-vrm**, com avatar humanoide anime VRM criado pelo usuário.

## Limitações honestas

O projeto **não acompanha um modelo anime profissional pronto**.
Sem `yuna.vrm` o estúdio mostra a prévia geométrica. O motor
não cria sozinho um arquivo VRM texturizado e rigado; usar o
VRoid Studio é a etapa artística necessária para conseguir esse visual.
Também não há caminhada livre sobre o desktop, captura de movimento,
animação profissional de dança ou sincronia labial por fonemas.
Esses recursos exigem desenvolvimento e testes adicionais.

O VRoid Studio é gratuito, mas itens customizados podem ter licenças
próprias. Não baixe ou redistribua modelos alheios sem permissão.
