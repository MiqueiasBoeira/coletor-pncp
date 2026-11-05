# Monitor de licitações do PNCP

Busca contratações publicadas no Portal Nacional de Contratações Públicas, fica só com as que citam palavras-chave no objeto da compra e exporta o resultado para Excel. Com `--sheets`, grava a mesma tabela numa planilha Google.

## Como rodar

```bash
uv sync
uv run python main.py --arquivo local/publicacaoPNCP.json
```

Consulta direta à API. As datas vão no formato `AAAAMMDD`. O código `6` é Pregão Eletrônico.

```bash
uv run python main.py --data-inicial 20261001 --data-final 20261031 --uf RS --modalidade 6
```

Google Sheets, com as variáveis do `.env`:

```bash
uv run python main.py --data-inicial 20261001 --data-final 20261031 --uf RS --sheets
```

Entre uma página e outra o programa espera 1 segundo. Um intervalo grande de datas demora de propósito: é o intervalo para não martelar a API pública.

Códigos de saída:

- `0`: a coleta fechou. Se ninguém passou no filtro, nenhum arquivo é criado.
- `1`: o JSON local ou a API falhou. Nada é exportado.
- `2`: a coleta veio, mas a gravação falhou (pasta inexistente, arquivo aberto, Sheets sem configuração).

## Testes

```bash
uv run pytest
uv run ruff check .
```

## Configuração

Copie `.env.example` para `.env`. Estes itens ficam fora do git:

- `GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL`: caminho do JSON da conta de serviço
- `ID_SHEET_GOOGLE`: identificador da planilha, o trecho da URL entre `/d/` e `/edit`

A planilha precisa estar compartilhada com o e-mail da conta de serviço. Sem `--sheets`, o comando não usa essas variáveis e gera só o Excel.

## Fluxo

1. A fonte é um JSON no formato da API (`--arquivo`) ou a própria API.
2. `filtrar_licitacoes` mantém o registro se alguma palavra aparece no objeto, sem diferenciar maiúsculas.
3. `validar_licitacoes` transforma cada registro que sobrou. O incompleto vai para uma lista de erros e o restante continua.
4. `preparar_dataframe` define colunas, nomes e a data. Excel e Sheets usam essa mesma tabela.
5. A gravação no Sheets apaga a primeira aba e escreve a coleta atual no lugar.

## Limitações

O município é o da unidade que comprou (`unidadeOrgao.municipioNome`). Uma unidade pode estar comprando para outro município. Isso só aparece nos documentos do edital, e este programa não lê edital.

## Decisões

- [Uma tabela, dois destinos](docs/decisoes/001-tabela-unica.md)
- [Lista vazia e página que falha](docs/decisoes/002-falhas.md)

## Outros projetos do portfólio

- [extrator-pdf-editais](https://github.com/MiqueiasBoeira/extrator-pdf-editais)
- [robo-portal-compras](https://github.com/MiqueiasBoeira/robo-portal-compras)
- [api-licitacoes](https://github.com/MiqueiasBoeira/api-licitacoes)
- [automacao-licitacoes](https://github.com/MiqueiasBoeira/automacao-licitacoes)
- [pagina-consultoria](https://github.com/MiqueiasBoeira/pagina-consultoria)
- [painel-precos](https://github.com/MiqueiasBoeira/painel-precos)
