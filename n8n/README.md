# Workflow n8n — oportunidades diárias

Importa em http://localhost:5678 → **Import from File** → `oportunidades-diario.json`.

## Antes

1. `.env` do projeto com `API_KEY_OPORTUNIDADES` e, se for classificar, `ANTHROPIC_API_KEY`.
2. API no ar (na pasta do projeto):

```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000
```

3. n8n no Docker (Linux):

```bash
docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n \
  --add-host=host.docker.internal:host-gateway \
  docker.n8n.io/n8nio/n8n
```

## Credencial

No nó **GET oportunidades**, crie Header Auth:

| Campo | Valor |
|---|---|
| Name / Header | `X-API-Key` |
| Value | o mesmo texto de `API_KEY_OPORTUNIDADES` no `.env` |

Não cole a chave dentro do JSON do workflow.

## URL

`http://host.docker.internal:8000/oportunidades`

Query do exemplo: `uf`, `classificar`, `relevancia_minima`, `palavras`.  
Para testar com JSON local (API no host), acrescente `arquivo=local/publicacaoPNCP.json`.

## Depois do Import

Execute o workflow na mão (play). Só ative o agendamento (8h) quando estiver estável.  
O sticky note do fluxo é o lugar para ligar Gmail ou Telegram — credenciais só no n8n.
