# ADR 001 — Uma tabela, dois destinos

## Contexto

Excel e Google Sheets precisam das mesmas colunas, na mesma ordem. Se cada destino montar a tabela sozinho, um cabeçalho muda num lugar e esquece o outro.

## Decisão

`preparar_dataframe` monta a tabela. `exportar_para_excel` só grava o arquivo. A gravação no Sheets converte essa mesma tabela em linhas.

O Sheets substitui o conteúdo da primeira aba (`clear` e depois `update`). A planilha fica igual à última coleta.

## Consequência

Mudar um cabeçalho altera os dois destinos. Acrescentar linhas (`append`) guardaria histórico e duplicaria a coleta se o comando rodasse de novo. Histórico ficou de fora desta versão.
