# Conversa mais natural

Yuna usa o feminino ao falar de si (obrigada, pronta, animada), sem alterar o gênero do usuário, de outras pessoas ou de citações. O estilo é gentil e natural, sem exigir bordões ou estereótipos. Isso é uma configuração de linguagem, não consciência ou sentimentos reais.

O contexto de conversa separa a identidade de Yuna da identidade do usuário. Reflexões geradas pela IA continuam salvas, mas deixam de ser exemplos para respostas comuns. Alguns erros conhecidos acionam uma única revisão; se ela falhar, Yuna pede que o usuário reformule. Essa revisão pode aumentar o tempo de resposta. O filtro é limitado e não garante a correção de todo erro do modelo.

## Atualização

Para uma instalação que já estava na versão 0.12.2, feche Yuna, baixe o ZIP atualizado e substitua `yuna.py` e `affect.py` na pasta usada para iniciar o programa. Preserve a pasta `data`. Instalações anteriores precisam dos demais arquivos atualizados também, mantendo os dados pessoais existentes.

Não é necessário apagar memórias: pares de conversa com alguns erros conhecidos são omitidos apenas do contexto enviado ao modelo, sem excluir o histórico do banco.

## Verificação no notebook

Experimente: “Quem é você e quem te criou?”, “Como você agradece uma ajuda?” e “Estou animado com o projeto; e você?”. Confira se ela distingue Yuna de Kaizen, usa o feminino para si e preserva o masculino usado pelo usuário. A voz escolhida no Windows não é alterada por esta atualização.

Os testes automatizados verificam o filtro, a revisão com respostas simuladas e a preservação dos dados. A qualidade das respostas do modelo local precisa ser avaliada no notebook com Ollama em execução.
