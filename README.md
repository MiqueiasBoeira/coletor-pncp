# Monitor de licitações do PNCP

Busca contratações publicadas no Portal Nacional de Contratações Públicas, fica só com as que citam palavras-chave no objeto da compra e exporta o resultado para Excel. Com `--sheets`, grava a mesma tabela numa planilha Google. Com `--classificar`, o Claude (Anthropic) nota relevância, categoria e um resumo de cada objeto.

## Como rodar

```bash
uv sync
uv run python main.py --arquivo local/publicacaoPNCP.json
```

Consulta direta à API. As datas vão no formato `AAAAMMDD`. O código `6` é Pregão Eletrônico.

```bash
uv run python main.py --data-inicial 20261001 --data-final 20261031 --uf RS --modalidade 6
```

Classificação com LLM (precisa de `ANTHROPIC_API_KEY` no `.env`):

```bash
uv run python main.py --arquivo local/publicacaoPNCP.json --classificar --saida pasta_de_exportacao/com_ia.xlsx
```

Google Sheets, com as variáveis do `.env`:

```bash
uv run python main.py --data-inicial 20261001 --data-final 20261031 --uf RS --sheets
```

Entre uma página e outra o programa espera 1 segundo. Um intervalo grande de datas demora de propósito: é o intervalo para não martelar a API pública.

Códigos de saída:

- `0`: a coleta fechou. Se ninguém passou no filtro, nenhum arquivo é criado.
- `1`: o JSON local, a API do PNCP ou a classificação falhou. Nada é exportado (falha de classificação) ou a coleta não fechou.
- `2`: a coleta veio, mas a gravação falhou (pasta inexistente, arquivo aberto, Sheets sem configuração).

## API para o n8n

```bash
uv run uvicorn api:app --reload --port 8000
```

- `GET /saude` → `{"status":"ok"}`
- `GET /oportunidades` → JSON com `itens` e, se classificou, `tokens`. Header obrigatório: `X-API-Key` (igual a `API_KEY_OPORTUNIDADES` no `.env`).

Query úteis: `uf`, `data_inicial`, `data_final`, `palavras`, `classificar`, `relevancia_minima` (padrão 7).

O workflow de exemplo está em [`n8n/oportunidades-diario.json`](n8n/oportunidades-diario.json). Importe no n8n, configure a credencial Header Auth com a mesma API key e aponte para `http://host.docker.internal:8000` se o n8n estiver no Docker.

```bash
docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

## Testes

```bash
uv run pytest
uv run ruff check .
```

Avaliação com a API real (gasta tokens de propósito):

```bash
RUN_AVALIACAO=1 uv run pytest -m avaliacao -q
```

## Configuração

Copie `.env.example` para `.env`. Estes itens ficam fora do git:

- `GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL`: caminho do JSON da conta de serviço
- `ID_SHEET_GOOGLE`: identificador da planilha, o trecho da URL entre `/d/` e `/edit`
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`: classificação (`claude-haiku-4-5` por padrão)
- `API_KEY_OPORTUNIDADES`: protege `GET /oportunidades`

A planilha precisa estar compartilhada com o e-mail da conta de serviço. Sem `--sheets`, o comando não usa as variáveis do Google. Sem `--classificar`, não chama a Anthropic.

O cache de classificação fica em `local/cache_classificacao.json` (pasta `local/` ignorada pelo git).

## Fluxo

1. A fonte é um JSON no formato da API (`--arquivo`) ou a própria API.
2. `filtrar_licitacoes` mantém o registro se alguma palavra aparece no objeto, sem diferenciar maiúsculas.
3. `validar_licitacoes` transforma cada registro que sobrou. O incompleto vai para uma lista de erros e o restante continua.
4. Com `--classificar`, `classificar_licitacoes` usa tool use na Anthropic e grava relevância, categoria, resumo e justificativa (com cache por número de controle).
5. `preparar_dataframe` define colunas, nomes e a data. Excel e Sheets usam essa mesma tabela.
6. A gravação no Sheets apaga a primeira aba e escreve a coleta atual no lugar.

## Limitações

O município é o da unidade que comprou (`unidadeOrgao.municipioNome`). Uma unidade pode estar comprando para outro município. Isso só aparece nos documentos do edital, e este programa não lê edital.

A classificação depende do modelo e do prompt; use o teste marcado `avaliacao` para medir acerto em amostras suas.

## Decisões

- [Uma tabela, dois destinos](docs/decisoes/001-tabela-unica.md)
- [Lista vazia e página que falha](docs/decisoes/002-falhas.md)
- [Classificação com LLM e cache](docs/decisoes/003-classificacao-llm.md)

## Outros projetos do portfólio

- [extrator-pdf-editais](https://github.com/MiqueiasBoeira/extrator-pdf-editais)
- [robo-portal-compras](https://github.com/MiqueiasBoeira/robo-portal-compras)
- [api-licitacoes](https://github.com/MiqueiasBoeira/api-licitacoes)
- [automacao-licitacoes](https://github.com/MiqueiasBoeira/automacao-licitacoes)
- [pagina-consultoria](https://github.com/MiqueiasBoeira/pagina-consultoria)
- [painel-precos](https://github.com/MiqueiasBoeira/painel-precos)
