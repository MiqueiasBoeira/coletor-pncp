# ADR 003 — Classificação com LLM e cache

## Contexto

O filtro por palavra-chave deixa passar objetos longos em que a palavra aparece sem ser o foco da compra. Uma classificação do objeto (relevância, categoria, resumo) ajuda a priorizar o alerta. Chamar a API a cada execução diária no mesmo `numeroControlePNCP` gasta tokens à toa.

## Decisão

1. A classificação roda **no Python** (`classificador.py`), com cliente Anthropic injetável nos testes.
2. A resposta usa **tool use** (`registrar_classificacao`) para obrigar o JSON no schema.
3. O resultado é cacheado em `local/cache_classificacao.json` pela chave `numero_controle_pncp`.
4. Cada execução registra `input_tokens`, `output_tokens`, chamadas e acertos de cache.
5. O n8n **orquestra** (agenda + HTTP + filtro de relevância). Não classifica dentro do n8n.

## Consequência

Sem `--classificar` / sem `classificar=true` na API, o comportamento antigo permanece. Com classificação, a planilha e o JSON da API ganham colunas extras. O arquivo de cache fica fora do git (`local/`). A avaliação real fica no marcador `avaliacao` e não roda no CI local padrão.
