# ADR 002 — Lista vazia e página que falha

## Contexto

O filtro pode não achar nada. A API pode falhar na segunda página, depois de a primeira ter vindo certa.

## Decisão

Lista vazia é um resultado válido. O comando termina com código 0, registra um aviso e não cria arquivo. Uma planilha só com cabeçalho pareceria uma coleta bem-sucedida.

Falha de rede ou de resposta no meio da paginação interrompe a consulta. O comando termina com código 1 e o que já tinha sido baixado não é exportado.

Código 2 fica para falha ao gravar: pasta inexistente, arquivo aberto, ou Google Sheets sem o identificador da planilha.

## Consequência

Quem lê a planilha não recebe uma coleta pela metade. Quem quiser o parcial precisa mudar esta decisão: a função hoje descarta o que já baixou quando uma página falha.
