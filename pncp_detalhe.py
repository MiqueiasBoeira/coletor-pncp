"""Cliente HTTP da API de detalhe do PNCP (itens 11.13 e arquivos 11.8)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

URL_BASE = "https://pncp.gov.br/api/pncp/v1/"
TIMEOUT = 30
TAMANHO_PAGINA_PADRAO = 50


class ErroDetalhePNCP(Exception):
    """Falha ao consultar itens ou arquivos de uma contratação."""


def _url_compra(cnpj: str, ano: int | str, sequencial: int | str, sufixo: str) -> str:
    return urljoin(
        URL_BASE,
        f"orgaos/{cnpj}/compras/{ano}/{sequencial}/{sufixo}",
    )


def listar_itens(
    cnpj: str,
    ano: int | str,
    sequencial: int | str,
    *,
    session: Any = None,
    pausa: Callable[[float], None] = time.sleep,
    tamanho_pagina: int = TAMANHO_PAGINA_PADRAO,
) -> list[dict[str, Any]]:
    """GET .../itens com paginação (manual 11.13)."""
    todos: list[dict[str, Any]] = []
    pagina_atual = 1
    total_paginas = 1
    session_propria = session is None
    if session is None:
        session = requests.Session()

    url = _url_compra(cnpj, ano, sequencial, "itens")
    try:
        while pagina_atual <= total_paginas:
            parametros = {"pagina": pagina_atual, "tamanhoPagina": tamanho_pagina}
            try:
                response = session.get(url, params=parametros, timeout=TIMEOUT)
                response.raise_for_status()
                dados = response.json()
                if isinstance(dados, list):
                    todos.extend(dados)
                    break
                total_paginas = int(dados.get("totalPaginas") or 1)
                lote = dados.get("data") or dados.get("itens") or []
                if isinstance(lote, list):
                    todos.extend(lote)
                pagina_atual += 1
                if pagina_atual <= total_paginas:
                    pausa(1)
            except (requests.RequestException, KeyError, TypeError, ValueError) as erro:
                logger.error(
                    "Erro ao listar itens %s/%s/%s página %s: %s",
                    cnpj,
                    ano,
                    sequencial,
                    pagina_atual,
                    erro,
                )
                raise ErroDetalhePNCP(
                    f"Falha ao listar itens de {cnpj}/{ano}/{sequencial} "
                    f"(página {pagina_atual})"
                ) from erro
    finally:
        if session_propria:
            session.close()

    return todos


def listar_arquivos(
    cnpj: str,
    ano: int | str,
    sequencial: int | str,
    *,
    session: Any = None,
) -> list[dict[str, Any]]:
    """GET .../arquivos (manual 11.8)."""
    session_propria = session is None
    if session is None:
        session = requests.Session()

    url = _url_compra(cnpj, ano, sequencial, "arquivos")
    try:
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            dados = response.json()
        except (requests.RequestException, ValueError) as erro:
            logger.error(
                "Erro ao listar arquivos %s/%s/%s: %s",
                cnpj,
                ano,
                sequencial,
                erro,
            )
            raise ErroDetalhePNCP(
                f"Falha ao listar arquivos de {cnpj}/{ano}/{sequencial}"
            ) from erro
    finally:
        if session_propria:
            session.close()

    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        lote = dados.get("data") or dados.get("arquivos") or []
        if isinstance(lote, list):
            return lote
    raise ErroDetalhePNCP(
        f"Resposta inesperada ao listar arquivos de {cnpj}/{ano}/{sequencial}"
    )


def baixar_arquivo(
    url: str,
    *,
    session: Any = None,
) -> bytes:
    """Baixa bytes de uma URL de documento do PNCP."""
    if not (url or "").strip():
        raise ErroDetalhePNCP("URL de arquivo vazia")
    session_propria = session is None
    if session is None:
        session = requests.Session()
    try:
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.content
        except requests.RequestException as erro:
            logger.error("Erro ao baixar arquivo %s: %s", url, erro)
            raise ErroDetalhePNCP(f"Falha ao baixar arquivo: {url}") from erro
    finally:
        if session_propria:
            session.close()
