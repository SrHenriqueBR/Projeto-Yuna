# Voz e capacidade — Yuna 0.55.0

## Ativar o Qwen3.5:4b

1. Instale a atualização da Yuna na mesma pasta e abra o Ollama.
2. Em **••• → Central da Yuna → Preparação**, clique em **Ativar Qwen3.5:4b + capacidade máxima**.
3. Confirme o download de aproximadamente 3,3–4 GB e espere a mensagem de conclusão. Se já estiver baixado, o Ollama verifica os arquivos.
4. Digite `/modelo` para conferir a seleção e `/desempenho` para conferir o perfil. Vale para a próxima resposta, sem reiniciar.

Uma preferência antiga em `data/modelo_yuna.txt` é preservada durante a atualização. O botão acima atualiza essa preferência quando o download termina; não apaga memórias. A variável avançada `YUNA_MODEL` tem prioridade. Se ela fixa outro modelo, a Central avisa que é necessário removê-la e reabrir o programa.

O novo padrão sem configuração é `qwen3.5:4b`, perfil `maximo`. Isso não inclui os pesos no instalador: o Ollama precisa baixá-los. Não há API paga ou cobrança por tokens nessa integração.

| Perfil | Contexto de conversa | Limite de resposta | Código |
| --- | ---: | ---: | --- |
| Máximo | 16.384 tokens | 4.096 tokens | 16.384 de contexto / 8.192 de saída; raciocínio Qwen3.5 em pedidos de código livre |
| Equilibrado | 8.192 tokens | 768 tokens | 12.288 de contexto / 3.072 de saída |
| Rápido | 8.192 tokens | 384 tokens | 12.288 de contexto / 3.072 de saída |

O limite de saída também inclui o raciocínio interno quando ativado. A conversa comum e JSON de ferramentas usam resposta direta. Se o raciocínio terminar sem resposta, há uma tentativa adicional com resposta direta; o raciocínio interno não é mostrado. Saídas cortadas são sinalizadas; JSON cortado é rejeitado.

Exemplos: “Crie um script Python que organize uma lista em ordem alfabética”, “Corrija este código…” e “Explique recursão com exemplos”. Pedidos de programação no chat recebem o orçamento de código. Gerar código não significa executá-lo ou testar automaticamente no computador.

Máximo favorece capacidade, e pode ser mais lento. RAM/VRAM, CPU/GPU, contexto e outros aplicativos influenciam o resultado. Não é promessa de QI, consciência ou acerto garantido. Se houver falta de memória, use **Perfil equilibrado** ou **Perfil rápido**, e considere o Qwen3.5:2b nas máquinas menores. O 9b permanece uma escolha manual.

## Fazer o microfone escutar

1. Abra **Central → Permissões → Escolher microfone** e selecione o headset/USB correto. O padrão do Windows acompanha a entrada padrão do sistema.
2. Clique em **Falar**. Autorize o microfone na primeira utilização da sessão.
3. Espere **Ouvindo • nome do dispositivo**. A barra deve se mover com sua voz.
4. Fale uma frase de até 20 segundos e faça uma pausa. A captura termina após cerca de 1,2 segundo de silêncio. Sem fala, o ditado avisa após cerca de 8 segundos.
5. A etapa **Entendendo sua fala** transcreve em português no computador. Na primeira utilização o Whisper base pode ser baixado; depois, o modelo é reutilizado na sessão.

**Enviar fala automaticamente** vem marcado nesta sessão. Desmarque na Central para revisar antes de enviar. Se já houver um rascunho, a fala é acrescentada a ele e aguarda envio manual, para não perder seu texto.

Para escuta contínua, marque **Escutar “Olá Yuna”**. Diga “Yuna, qual a diferença entre lista e tupla?” numa frase. Durante a resposta da Yuna ou o processamento de outro pedido, a escuta fica pausada para não captar a própria voz. Comece cada novo pedido com Yuna. O reconhecimento não autentica quem falou.

O novo capturador usa a frequência nativa do microfone (por exemplo, 48 kHz), converte o áudio para o Whisper e espera o fim da frase, em vez de cortar a cada quatro segundos. A seleção salva usa nome e API de áudio, pois índices podem mudar após reconectar USB. Um dispositivo selecionado que desapareceu gera orientação para escolher outro; não troca secretamente de entrada.

**Se a barra ficar parada:** confira o botão mudo, o nível de entrada e a permissão de microfone para aplicativos da área de trabalho nas configurações do Windows. **Se a barra se mover mas não reconhecer:** aproxime o microfone, reduza ruído e confira se selecionou a entrada correta. **Parar** cancela a captura e descarta transcrições atrasadas. Gravações ficam só em memória, sem arquivo ou envio à web.

## Pesquisar dentro do chat desktop

- “Yuna, pesquise na web sobre documentação de Python”: consulta os resumos públicos do buscador e responde com links das fontes.
- “Qual a versão mais recente do Python?”: pode consultar a web automaticamente por ser uma pergunta pública sobre informação atual.
- `/web Python` e pedidos explícitos “no Google” / “no YouTube” continuam abrindo o navegador.

Somente o assunto atual da pesquisa vai ao buscador. Histórico, memórias, documentos e áudio não são acrescentados à consulta. Buscas com padrões de dados privados são recusadas. Os resumos são dados não confiáveis e não viram comandos; páginas completas não são baixadas por essa função. A busca não exige conta ou chave, mas depende da disponibilidade do DuckDuckGo. Se houver bloqueio, CAPTCHA ou mudança de formato, a Yuna informa a falha e oferece uma consulta à Wikipédia, sem alegar ter confirmado notícias atuais.

O chat web local no navegador mantém o modo de conversa sem ferramentas de pesquisa. Não há pesquisa contínua em segundo plano. `YUNA_AUTO_RESEARCH=0` desliga pesquisas automáticas; pedidos explícitos de pesquisa continuam disponíveis.

## Verificação e limites

Os testes usam áudio sintético, entradas simuladas, respostas Ollama simuladas e amostras HTML. Cobrem frases longas/baixas, silêncio, frequência nativa, USB, cancelamento, envio/revisão, troca de modelo, limite de geração, fontes e falha de busca. O pipeline Windows também testa instalação, atualização e preservação dos dados. O microfone físico, a velocidade do Qwen3.5:4b e a qualidade das respostas precisam ser conferidos no notebook de uso.

Uma inferência Ollama já iniciada ainda pode precisar terminar depois de **Parar**; a resposta antiga é descartada. O perfil máximo admite tempo maior para código (até dez minutos por tentativa). Não se trata de controle ilimitado do PC ou desativação das permissões existentes.
