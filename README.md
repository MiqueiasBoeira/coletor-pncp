# Monitor de licitações do PNCP

Busca contratações no [Portal Nacional de Contratações Públicas](https://pncp.gov.br), filtra por palavra-chave no objeto e exporta para Excel. Opcionalmente classifica cada objeto com a Anthropic (relevância, categoria, resumo) e serve o resultado numa API para o n8n agendar alertas.

## Início rápido

```bash
git clone https://github.com/MiqueiasBoeira/coletor-pncp.git
cd coletor-pncp
uv sync
cp .env.example .env
mkdir -p pasta_de_exportacao local
```

Coloque um JSON no formato da API em `local/publicacaoPNCP.json` **ou** use a consulta ao PNCP (seção abaixo). Sem `.env` preenchido, o coletor ainda roda só com filtro + Excel.

```bash
uv run python main.py --arquivo local/publicacaoPNCP.json --palavras computador --saida pasta_de_exportacao/saida.xlsx
uv run pytest -q -m "not avaliacao"
```

## Configuração (`.env`)

Copie `.env.example` → `.env`. **Nunca** versionar o `.env`.

| Variável | Quando precisa | O que é |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--classificar` ou `classificar=true` na API | Chave em [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) (`sk-ant-...`). Expiração sugerida: Never. |
| `ANTHROPIC_MODEL` | opcional | Padrão `claude-haiku-4-5` |
| `API_KEY_OPORTUNIDADES` | `uvicorn` / n8n | Senha que **você inventa** (ex.: `openssl rand -hex 24`). O n8n manda no header `X-API-Key`. |
| `GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL` | `--sheets` | Caminho do JSON da conta de serviço |
| `ID_SHEET_GOOGLE` | `--sheets` | ID na URL da planilha (`/d/` … `/edit`). Compartilhe a aba com o e-mail da conta de serviço. |

Sem `--classificar`, a Anthropic não é chamada. Sem `--sheets`, o Google não é usado. Sem `API_KEY_OPORTUNIDADES`, a rota `/oportunidades` responde erro de configuração.

Cache da classificação: `local/cache_classificacao.json` (pasta `local/` fora do git).

## Linha de comando

Datas no formato `AAAAMMDD`. Modalidade `6` = Pregão Eletrônico.

```bash
# PNCP (um intervalo pequeno demora menos)
uv run python main.py --data-inicial 20261103 --data-final 20261103 --uf RS --palavras aquisição --saida pasta_de_exportacao/pncp.xlsx

# Com classificação (gasta tokens)
uv run python main.py --arquivo local/publicacaoPNCP.json --palavras computador --classificar --saida pasta_de_exportacao/com_ia.xlsx

# Também Google Sheets (substitui a primeira aba: clear + rewrite)
uv run python main.py --data-inicial 20261103 --data-final 20261103 --uf RS --sheets
```

Entre páginas da API pública o programa espera 1 segundo.

Códigos de saída: `0` ok (lista vazia também); `1` leitura/PNCP/classificação; `2` falha ao gravar Excel/Sheets.

## API HTTP e n8n

```bash
# Obrigatório --host 0.0.0.0 se o n8n estiver no Docker
uv run uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

| Rota | Auth | Resposta |
|---|---|---|
| `GET /saude` | não | `{"status":"ok"}` |
| `GET /oportunidades` | header `X-API-Key` = `API_KEY_OPORTUNIDADES` | `itens`, e `tokens` se classificou |

Query: `uf`, `data_inicial`, `data_final`, `palavras`, `classificar`, `relevancia_minima` (padrão 7), `arquivo` (JSON local, só desenvolvimento).

Passo a passo do workflow: [`n8n/README.md`](n8n/README.md). Arquivo para importar: [`n8n/oportunidades-diario.json`](n8n/oportunidades-diario.json).

```bash
docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n \
  --add-host=host.docker.internal:host-gateway \
  docker.n8n.io/n8nio/n8n
```

URL típica no n8n: `http://host.docker.internal:8000/oportunidades`.

## Testes

```bash
uv run pytest -q -m "not avaliacao"
uv run ruff check .
```

Chamada real à Anthropic (opcional, gasta créditos):

```bash
RUN_AVALIACAO=1 uv run pytest -m avaliacao -q
```

## Fluxo

1. Fonte: JSON (`--arquivo`) ou API do PNCP.
2. Filtro por palavra no objeto.
3. Validação / transformação dos campos.
4. Com `--classificar`: Anthropic (tool use) + cache por número de controle.
5. Excel (e Sheets, se pedido) a partir da mesma tabela.

## Limitações

O município é o da unidade compradora (`unidadeOrgao.municipioNome`), não necessariamente o município de entrega. Este programa não lê edital em PDF.

## Decisões

- [Uma tabela, dois destinos](docs/decisoes/001-tabela-unica.md)
- [Lista vazia e página que falha](docs/decisoes/002-falhas.md)
- [Classificação com LLM e cache](docs/decisoes/003-classificacao-llm.md)

## Outros projetos

- [extrator-pdf-editais](https://github.com/MiqueiasBoeira/extrator-pdf-editais)
- [robo-portal-compras](https://github.com/MiqueiasBoeira/robo-portal-compras)
- [api-licitacoes](https://github.com/MiqueiasBoeira/api-licitacoes)
- [automacao-licitacoes](https://github.com/MiqueiasBoeira/automacao-licitacoes)
- [pagina-consultoria](https://github.com/MiqueiasBoeira/pagina-consultoria)
- [painel-precos](https://github.com/MiqueiasBoeira/painel-precos)
