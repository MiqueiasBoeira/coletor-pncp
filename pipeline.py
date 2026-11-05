"""Filtro e classificação opcional sobre uma lista já carregada."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from classificador import ContagemTokens, classificar_licitacoes
from processa_licitacoes import filtrar_e_validar

logger = logging.getLogger(__name__)

CACHE_CLASSIFICACAO = Path("local/cache_classificacao.json")


def processar_registros(
    registros: list[dict[str, Any]],
    palavras_chave: list[str],
    *,
    classificar: bool = False,
    cliente_classificador: Any | None = None,
    caminho_cache: Path | None = CACHE_CLASSIFICACAO,
    relevancia_minima: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict], ContagemTokens | None]:
    validadas, erros = filtrar_e_validar(registros, palavras_chave)
    logger.info("Validadas: %d, descartadas: %d", len(validadas), len(erros))

    contagem: ContagemTokens | None = None
    if classificar and validadas:
        contagem = classificar_licitacoes(
            validadas,
            cliente=cliente_classificador,
            caminho_cache=caminho_cache,
        )
        if relevancia_minima is not None:
            validadas = [
                item
                for item in validadas
                if int(item.get("relevancia") or 0) >= relevancia_minima
            ]
    return validadas, erros, contagem
