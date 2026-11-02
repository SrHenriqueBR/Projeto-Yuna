# Escola da Yuna

Esta é a caixa pública de estudos, perguntas e respostas da Yuna. Um modelo
aberto roda no **GitHub Actions**, sem depender do notebook ligado. A Yuna pode
estudar, formular dúvidas, tentar uma melhoria e criar um commit em uma branch
de revisão. O código em `main` só muda após revisão e merge por uma pessoa.

**[Ver a escola em execução](https://github.com/SrHenriqueBR/Projeto-Yuna/actions/workflows/escola-yuna.yml)**
· **[Ver estudos aguardando revisão](https://github.com/SrHenriqueBR/Projeto-Yuna/pulls?q=is%3Aopen+head%3Ayuna%2Festudo-)**
· **[Responder à Yuna](respostas.json)**

## Onde ficam as perguntas

Cada execução que conclui um estudo cria uma branch `yuna/estudo-ID-TENTATIVA`.
Nela, abra **`aprendizado/ciclos/ID-TENTATIVA/README.md`**. Você encontrará:

- Uma nota de estudo produzida pelo modelo, ainda sujeita a erros.
- Até três perguntas, cada uma com ID e o motivo de estar sendo feita.
- O resultado real do experimento: passou, falhou, não foi executado etc.
- As fontes consultadas e quais ficaram indisponíveis.

O ciclo também guarda `perguntas.json` e `relatorio.json`. Se uma melhoria passar
pelos testes isolados, a branch inclui a mudança no módulo e `teste_gerado.txt`
para inspeção. Se falhar, publica o estudo e as dúvidas, sem trocar o módulo.
Os testes novos ficam em `.txt` para não serem executados automaticamente no
Windows pela descoberta de testes do projeto.

Quando permitido pelas configurações do repositório, a automação também abre
um **pull request em rascunho**. Se o GitHub recusar essa abertura, o commit e a
caixa de perguntas continuam na branch. O resumo da execução fornece o link
para abrir a revisão manualmente. Não é necessário criar nem informar um PAT.

## Como ensinar

1. Abra o estudo, leia as perguntas e confira a proposta na aba **Files changed**.
2. Revise o código. Faça merge se estiver adequado ou feche o PR se não estiver.
   Se só houver uma branch, use o link de comparação para abrir o PR. Nenhum
   merge é feito pela Yuna. O GitHub pode pedir **Approve workflows to run**
   antes dos demais testes de um PR criado pelo bot; confira o código primeiro.
3. Em **`main`**, abra [`respostas.json`](respostas.json), clique no lápis e
   acrescente um objeto para cada pergunta, copiando o **ID e a pergunta exatos**:

```json
[
  {
    "id": "COPIE_O_ID_DA_PERGUNTA",
    "pergunta": "COPIE_A_PERGUNTA_EXATA",
    "resposta": "Escreva a orientação e um exemplo do resultado esperado."
  }
]
```

4. Faça o commit da resposta. Isso solicita outra rodada. A Yuna usa as respostas
   não vazias como referências nos próximos estudos e evita repetir a mesma
   pergunta. Um ID incorreto, duplicado ou JSON inválido interrompe a rodada com
   erro explícito; não vira conhecimento silenciosamente.

Só há **um estudo pendente por vez**. Enquanto seu PR estiver aberto, ou houver
uma branch de estudo sem PR, a escola aguarda revisão. PRs fechados ou mesclados
liberam a próxima rodada. Se desistir de uma branch sem PR, remova apenas essa
branch de estudo pelo GitHub ou crie e feche sua revisão.

Tudo nesta pasta é **público**. Ensine regras do projeto, exemplos e preferências
que queira publicar. Não coloque senhas, tokens, documentos ou dados pessoais.
O programa não importa conversas locais, câmera, tela ou `data/` do notebook.
As respostas são referências de trabalho; não alteram pesos do modelo, não
concedem permissões e não são memórias privadas dos usuários da versão PC.

## Quando ela estuda

O workflow roda por agenda **diariamente às 09:17 de Brasília (12:17 UTC)**,
ao mudar as respostas/configuração e pelo botão **Actions → Escola da Yuna →
Run workflow**. O GitHub pode atrasar execuções agendadas; não é um processo
permanentemente ligado. A primeira publicação da escola também solicita uma
rodada real, não apenas um teste com respostas simuladas.

O ciclo usa `qwen2.5-coder:1.5b` com Ollama em CPU, dentro do executor do GitHub.
Nenhuma API de IA paga é configurada. A consulta pública inicial é restrita à
documentação oficial de Python sobre expressões regulares e testes, com leitura
limitada por tamanho e tempo. A lista de destinos é fixa: o modelo não escolhe
URLs arbitrárias. A nota produzida é uma hipótese de estudo, não uma fonte nova
automaticamente validada.

Para pausar, edite [`config.json`](config.json):

```json
{
  "ativo": false,
  "propor_codigo": true
}
```

Para manter apenas estudo e perguntas, use `ativo: true` e `propor_codigo: false`.
Isso afeta as próximas rodadas; uma execução já iniciada pode ser cancelada pela
aba Actions. Não é necessário desinstalar a Yuna do computador.

## Limites desta versão

- Alvos de código: `language_quality.py` e `natural_interaction.py`.
- Uma melhoria por ciclo, com no máximo duas tentativas no laboratório.
- Modelo sem ferramentas de execução e sem credencial de escrita no GitHub.
- Testes gerados somente em Docker sem rede, com montagem mínima somente leitura.
- Job separado de publicação, que valida os dados e **não executa o código gerado**.
- Cria branch nova e PR rascunho; nunca força refs, aprova PRs, altera workflows,
  faz merge ou amplia a própria lista de arquivos/permissões.
- Pausa ao atingir 12 perguntas pendentes; até 50 respostas públicas, 12000
  caracteres de respostas no contexto e 100 ciclos aceitos no histórico do main.
- Até 25 minutos para estudo e 5 minutos para publicação; sem repetição ilimitada.

Passar nos contratos isolados não prova ausência de bugs. Revise o código e
rode a suíte completa antes do merge. Depois do merge, as instalações PC ainda
precisam receber a atualização normalmente, preservando `data/`.

O executor padrão Linux de um repositório público é gratuito segundo a
[documentação do GitHub](https://docs.github.com/en/actions/concepts/billing-and-usage).
Este workflow se recusa a estudar/publicar se o repositório se tornar privado,
não usa runners pagos e transfere apenas um resultado pequeno entre jobs,
sem armazenar modelos em caches ou artifacts. Limites e disponibilidade do
GitHub continuam aplicáveis; o programa não consulta sua fatura.

Referências: [Ollama em Docker](https://docs.ollama.com/docker),
[permissões do GitHub Actions](https://docs.github.com/en/actions/concepts/security/github_token)
e [configuração de criação de PRs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).
