"""Filtro, enriquecimento, funil e classificação/recomendação opcionais."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from classificador import ContagemTokens, classificar_licitacoes
from criterios import carregar_criterios
from documentos import enriquecer_com_documentos
from funil import aplicar_funil
from itens import enriquecer_com_itens
from processa_licitacoes import filtrar_e_validar
from recomendador import CACHE_RECOMENDACAO, recomendar_licitacoes

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
    enriquecer_itens: bool = False,
    enriquecer_docs: bool = False,
    aplicar_funil_flag: bool = False,
    recomendar: bool = False,
    cliente_recomendador: Any | None = None,
    caminho_cache_recomendacao: Path | None = CACHE_RECOMENDACAO,
    caminho_criterios: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict], ContagemTokens | None, ContagemTokens | None]:
    """Retorna (validadas, erros, tokens_classificacao, tokens_recomendacao)."""
    # Encadeamento: recomendar implica docs+funil+itens; funil implica itens.
    if recomendar:
        enriquecer_docs = True
        aplicar_funil_flag = True
    if aplicar_funil_flag or enriquecer_docs:
        enriquecer_itens = True

    criterios = None
    if enriquecer_itens or enriquecer_docs or aplicar_funil_flag or recomendar:
        criterios = carregar_criterios(caminho_criterios)

    validadas, erros = filtrar_e_validar(registros, palavras_chave)
    logger.info("Validadas: %d, descartadas: %d", len(validadas), len(erros))

    if enriquecer_itens and validadas:
        enriquecer_com_itens(validadas, criterios=criterios)

    if enriquecer_docs and validadas:
        enriquecer_com_documentos(validadas, criterios=criterios)

    if aplicar_funil_flag and validadas:
        validadas, descartadas_funil = aplicar_funil(validadas, criterios=criterios)
        for item in descartadas_funil:
            erros.append(
                {
                    "numero_controle_pncp": item.get("numero_controle_pncp"),
                    "motivo_erro": item.get("motivo_descarte"),
                }
            )

    contagem_recomendacao: ContagemTokens | None = None
    if recomendar and validadas:
        contagem_recomendacao = recomendar_licitacoes(
            validadas,
            criterios=criterios,
            cliente=cliente_recomendador,
            caminho_cache=caminho_cache_recomendacao,
        )

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
    return validadas, erros, contagem, contagem_recomendacao
