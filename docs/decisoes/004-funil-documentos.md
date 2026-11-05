# ADR 004 — Funil de itens, documentos e recomendação

## Contexto

O filtro por palavra no objeto e a classificação do texto curto ainda deixam passar compras em que o item relevante é residual, o valor está fora do perfil ou o edital traz restrição dura. Baixar edital e chamar LLM em todas as publicações explode custo e tempo. A API de detalhe do PNCP já expõe itens (11.13) e arquivos (11.8).

## Decisão

1. Persistir `orgao_cnpj`, `ano_compra` e `sequencial_compra` na transformação para consultar o detalhe.
2. Critérios versionados em `criterios.yaml` (palavras de item, faixa de valor, prazo, termos do edital, perfil).
3. Funil **determinístico** barato: itens de interesse → documentos (Edital/TR + `pypdf`) → regras auditáveis com `motivo_descarte`.
4. LLM (**tool use**, Haiku, cache em `local/cache_recomendacao.json`) **só** nos sobreviventes (`--recomendar`).
5. Flags opt-in: `--enriquecer-itens`, `--enriquecer-docs`, `--funil`, `--recomendar` (com encadeamento). A classificação de objeto (`--classificar`) permanece independente.

## Consequência

Sem as flags novas, o comportamento antigo permanece. Com o funil, a exportação/API mostram só aprovadas; descartes entram em erros com motivo. Tokens de recomendação aparecem à parte (`tokens_recomendacao`). Cache de PDFs em `local/docs/` fica fora do git. OCR e parsing jurídico completo ficam fora de escopo.
