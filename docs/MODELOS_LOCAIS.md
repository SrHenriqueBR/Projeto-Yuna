# Modelos de IA da Yuna — Qwen3.5 local, sem cobrança de API

[← Voltar ao LEIA-ME](../README.md) · [Instalação Windows](INSTALACAO_WINDOWS.md)

## Qual é a opção gratuita?

**Ollama LOCAL**, instalado no mesmo computador onde roda a Yuna.

A Yuna se comunica somente com o Ollama em
`http://127.0.0.1:11434/api/chat`. Para instalar um modelo,
usa `http://127.0.0.1:11434/api/pull`. A Central não recebe,
armazena ou cadastra chave de `qwen.ai`, `dashscope` ou Alibaba
Cloud Model Studio. A lista de modelos permitidos pela Central exclui
explicitamente tags `:cloud`.

Um modelo open-weight executado localmente pode responder a **quantas
mensagens seu computador suportar**, sem cobrança por tokens de API.
Não há período experimental oculto, contador de conversas ou assinatura
da Yuna. Você continua pagando apenas recursos normais da máquina
(energia, eventual acesso à internet e armazenamento).

## Opções Qwen3.5 verificadas no Ollama

| Modelo | Indicado para | Tamanho aproximado do download |
| --- | --- | --- |
| `qwen3.5:2b` | Máquina Windows com 8 GB de RAM, melhor leveza | 2,7–3,1 GB |
| `qwen3.5:4b` | **Recomendado** para desktop com 16 GB RAM e GPU dedicada | 3,3–4 GB |
| `qwen3.5:9b` | Mais exigente, para testar somente com memória disponível | 6,6–7,6 GB |

Fonte: [catálogo oficial Qwen3.5 do Ollama](https://ollama.com/library/qwen3.5).
A memória necessária durante a execução pode exceder o download, por
causa de contexto, cache KV, modelos de voz e outras aplicações. Uma
RTX 3070 Laptop com 8 GB VRAM pode não comportar `9b` mais um contexto
grande inteiramente na GPU: o processamento pode passar parcialmente
para a RAM e ficar mais lento. Os modelos funcionam para texto; recursos
de visão exigem interface/fluxo multimodal compatível, não são
automaticamente ativados por escolher um modelo novo.

## Como instalar na Central

1. Instale/abra [Ollama para Windows](https://ollama.com/download/windows).
2. Abra **Yuna.app → ••• → Central da Yuna → Preparação**.
3. Clique em **Qwen3.5 Recomendado 4B** (ou Leve 2B / Avançado 9B).
4. Confirme que aceita baixar vários gigabytes. A Central usa a API
   **Ollama em loopback**, não uma API Qwen comercial.
5. Aguarde a mensagem de **download concluído**. Em caso de erro,
   o modelo atual e suas memórias permanecem intactos.
6. **Feche a Yuna pelo menu Sair e abra novamente.**
7. Digite `/modelo` para conferir qual modelo foi carregado.

A seleção é gravada em `data/modelo_yuna.txt`. Seu
`data/yuna.db`, o histórico e a aparência da Yuna **não são
reescritos durante a troca**. Quem já usa Qwen2.5 mantém o modelo
anterior até optar por baixar o novo.

### Uso pelo terminal (opcional)

Se preferir usar o Ollama manualmente, os comandos para Windows são:

```powershell
ollama pull qwen3.5:2b
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama list
```

Depois de fazer `ollama pull` pelo terminal, a Yuna ainda precisa que
você **selecione o modelo na Central** para salvar sua preferência. A
seleção da Central verifica o download e persiste a escolha.

## E a API paga do site qwen.ai/apiplatform?

**É um serviço diferente.** Em plataformas de inferência comercial,
as chamadas são geralmente contabilizadas por **tokens de entrada e
saída**. Não é que depois de 100 conversas haja uma cobrança fixa:
a quantidade de texto, o tamanho do histórico, o contexto de código
e as respostas alteram o consumo.

A [documentação de cota do Alibaba Cloud Model Studio](https://help.aliyun.com/en/model-studio/new-free-quota),
consultada em **05/11/2026**, informa:
- Cotas gratuitas para novos usuários elegíveis em alguns modelos da
  região **China (Pequim)**, conforme verificação de identidade e
  elegibilidade; não presumir gratuidade em outras regiões.
- Cotas de 90 dias para novos usuários na regra geral.
- Se a cota acabar ou expirar, pode haver faturamento por uso de tokens,
  **inclusive sem um aviso por conversa**, no serviço habilitado.
- O controle **Free Quota Only**, quando disponível e ativado, impede
  chamadas pagas ao esgotar a cota.

A [documentação de custos](https://help.aliyun.com/en/model-studio/bill-query-and-cost-management)
também explica que o pagamento por uso é padrão no Model Studio.
Essas políticas podem mudar; confira novamente no console antes de
contratar qualquer API.

**Decisão deste projeto:** não usar Qwen API, DashScope nem Alibaba
Cloud; não solicitar cartão ou chave; não inserir modo de faturamento.
Toda opção Qwen3.5 integrada à Central é um modelo de download local.

## Observações de segurança

A ausência de cobrança por API **não significa uso sem custo de
hardware**. A IA pode usar CPU/GPU intensamente, memória, energia
e gigabytes de disco. Não instale automaticamente modelos pesados em
computadores de terceiros e não envie arquivos pessoais a APIs externas
sem consentimento separado.

Nenhum modelo fornece por si só controle total do computador,
consciência, ou um avatar 3D com rigging. A Yuna continua a executar
somente as ações e permissões que o código local implementa.
