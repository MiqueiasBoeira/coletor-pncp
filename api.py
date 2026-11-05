"""API HTTP para o n8n orquestrar a coleta e a classificação."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from busca_api_pncp import ErroConsultaPNCP, buscar_registros_pncp
from classificador import ErroClassificacao
from main import (
    CODIGO_MODALIDADE_PREGAO_ELETRONICO,
    DATA_FINAL,
    DATA_INICIAL,
    PALAVRAS_CHAVE,
    TAMANHO_PAGINA,
    UF,
    ErroLeituraArquivoLicitacoesJSON,
    carregar_arquivo_publicacao_pncp,
)
from pipeline import CACHE_CLASSIFICACAO, processar_registros

logger = logging.getLogger(__name__)


def _chave_esperada() -> str:
    return (os.getenv("API_KEY_OPORTUNIDADES") or "").strip()


def _autorizar(x_api_key: str | None) -> None:
    esperada = _chave_esperada()
    if not esperada:
        raise HTTPException(
            status_code=500,
            detail="API_KEY_OPORTUNIDADES não está definido no ambiente",
        )
    if not x_api_key or x_api_key != esperada:
        raise HTTPException(status_code=401, detail="API key inválida")


def criar_app(
    *,
    cliente_classificador: Any | None = None,
    caminho_cache: Path | None = CACHE_CLASSIFICACAO,
) -> FastAPI:
    app = FastAPI(
        title="Oportunidades PNCP",
        description="Coleta, filtra e classifica licitações para o workflow n8n.",
    )

    @app.get("/saude")
    def saude() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/oportunidades")
    def oportunidades(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        data_inicial: str = Query(default=DATA_INICIAL),
        data_final: str = Query(default=DATA_FINAL),
        uf: str = Query(default=UF),
        modalidade: int = Query(default=CODIGO_MODALIDADE_PREGAO_ELETRONICO),
        tamanho_pagina: int = Query(default=TAMANHO_PAGINA, ge=1, le=50),
        palavras: list[str] | None = Query(default=None),
        classificar: bool = Query(default=True),
        relevancia_minima: int = Query(default=7, ge=0, le=10),
        arquivo: str | None = Query(
            default=None,
            description="Caminho local de JSON (só para desenvolvimento).",
        ),
    ) -> JSONResponse:
        _autorizar(x_api_key)
        lista_palavras = palavras if palavras else list(PALAVRAS_CHAVE)
        try:
            if arquivo:
                registros = carregar_arquivo_publicacao_pncp(Path(arquivo))
            else:
                registros = buscar_registros_pncp(
                    data_inicial,
                    data_final,
                    modalidade,
                    uf,
                    tamanho_pagina,
                )
            itens, _erros, contagem = processar_registros(
                registros,
                lista_palavras,
                classificar=classificar,
                cliente_classificador=cliente_classificador,
                caminho_cache=caminho_cache if classificar else None,
                relevancia_minima=relevancia_minima if classificar else None,
            )
        except ErroLeituraArquivoLicitacoesJSON as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except ErroConsultaPNCP as erro:
            raise HTTPException(status_code=502, detail=str(erro)) from erro
        except ErroClassificacao as erro:
            raise HTTPException(status_code=502, detail=str(erro)) from erro

        corpo: dict[str, Any] = {
            "quantidade": len(itens),
            "itens": itens,
        }
        if contagem is not None:
            corpo["tokens"] = {
                "input_tokens": contagem.input_tokens,
                "output_tokens": contagem.output_tokens,
                "chamadas": contagem.chamadas,
                "acertos_cache": contagem.acertos_cache,
            }
        return JSONResponse(corpo)

    return app


def criar_app_producao() -> FastAPI:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    return criar_app()


app = criar_app_producao()
