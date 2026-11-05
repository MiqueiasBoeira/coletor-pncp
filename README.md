# Monitor de licitações do PNCP

Busca contratações no [Portal Nacional de Contratações Públicas](https://pncp.gov.br), filtra por palavra-chave no objeto e exporta para Excel. Opcionalmente enriquece com itens e editais, aplica um funil determinístico (`criterios.yaml`) e só então recomenda com a Anthropic — além da classificação curta do objeto e da API para o n8n.

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

# Com classificação do objeto (gasta tokens)
uv run python main.py --arquivo local/publicacaoPNCP.json --palavras computador --classificar --saida pasta_de_exportacao/com_ia.xlsx

# Funil completo: itens → docs → critérios → recomendação LLM (só nos sobreviventes)
uv run python main.py --arquivo local/publicacaoPNCP.json --palavras computador --recomendar --saida pasta_de_exportacao/funil.xlsx

# Também Google Sheets (substitui a primeira aba: clear + rewrite)
uv run python main.py --data-inicial 20261103 --data-final 20261103 --uf RS --sheets
```

Flags do funil (opt-in): `--enriquecer-itens`, `--enriquecer-docs`, `--funil`, `--recomendar`. `--funil` implica itens; `--recomendar` implica docs+funil+itens. Critérios em [`criterios.yaml`](criterios.yaml).

Entre páginas da API pública o programa espera 1 segundo.

Códigos de saída: `0` ok (lista vazia também); `1` leitura/PNCP/classificação/recomendação; `2` falha ao gravar Excel/Sheets.

## API HTTP e n8n

```bash
# Obrigatório --host 0.0.0.0 se o n8n estiver no Docker
uv run uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

| Rota | Auth | Resposta |
|---|---|---|
| `GET /saude` | não | `{"status":"ok"}` |
| `GET /oportunidades` | header `X-API-Key` = `API_KEY_OPORTUNIDADES` | `itens`, e `tokens` se classificou |

Query: `uf`, `data_inicial`, `data_final`, `palavras`, `classificar`, `relevancia_minima` (padrão 7), `enriquecer_itens`, `enriquecer_docs`, `funil`, `recomendar`, `arquivo` (JSON local, só desenvolvimento).

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
3. Validação / transformação (inclui CNPJ, ano e sequencial para o detalhe).
4. Opcional: itens (11.13) → documentos/Edital (11.8 + `pypdf`) → funil determinístico → recomendação LLM só nos aprovados.
5. Com `--classificar`: Anthropic no objeto (tool use) + cache por número de controle.
6. Excel (e Sheets, se pedido) a partir da mesma tabela.

Caches em `local/` (classificação, recomendação, PDFs). A LLM de recomendação **não** roda no lote inteiro — só no refinador após o funil.

## Limitações

O município é o da unidade compradora (`unidadeOrgao.municipioNome`), não necessariamente o município de entrega. PDF só com texto embutido (`pypdf`); sem OCR.

## Decisões

- [Uma tabela, dois destinos](docs/decisoes/001-tabela-unica.md)
- [Lista vazia e página que falha](docs/decisoes/002-falhas.md)
- [Classificação com LLM e cache](docs/decisoes/003-classificacao-llm.md)
- [Funil de itens, documentos e recomendação](docs/decisoes/004-funil-documentos.md)

## Outros projetos

- [extrator-pdf-editais](https://github.com/MiqueiasBoeira/extrator-pdf-editais)
- [robo-portal-compras](https://github.com/MiqueiasBoeira/robo-portal-compras)
- [api-licitacoes](https://github.com/MiqueiasBoeira/api-licitacoes)
- [automacao-licitacoes](https://github.com/MiqueiasBoeira/automacao-licitacoes)
- [pagina-consultoria](https://github.com/MiqueiasBoeira/pagina-consultoria)
- [painel-precos](https://github.com/MiqueiasBoeira/painel-precos)
