"""Enriquece licitações com itens da API PNCP 11.13."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from criterios import carregar_criterios
from pncp_detalhe import ErroDetalhePNCP, listar_itens

logger = logging.getLogger(__name__)

CAMPOS_ITEM = (
    "numeroItem",
    "descricao",
    "quantidade",
    "unidadeMedida",
    "valorUnitarioEstimado",
    "valorTotal",
    "materialOuServicoNome",
    "criterioJulgamentoNome",
    "situacaoCompraItemNome",
)


def _extrair_item(bruto: dict[str, Any]) -> dict[str, Any]:
    return {campo: bruto.get(campo) for campo in CAMPOS_ITEM}


def item_de_interesse(descricao: str | None, palavras: list[str]) -> bool:
    texto = (descricao or "").lower()
    if not texto or not palavras:
        return False
    return any(palavra.lower() in texto for palavra in palavras)


def _somar_valores(itens: list[dict[str, Any]]) -> float:
    total = 0.0
    for item in itens:
        valor = item.get("valorTotal")
        if valor is None:
            continue
        try:
            total += float(valor)
        except (TypeError, ValueError):
            continue
    return total


def enriquecer_com_itens(
    licitacoes: list[dict[str, Any]],
    *,
    criterios: dict[str, Any] | None = None,
    session: Any = None,
    pausa: Callable[[float], None] | None = None,
    listar: Callable[..., list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Acrescenta itens_interesse e agregados; falha por registro não cancela o lote."""
    cfg = criterios if criterios is not None else carregar_criterios()
    palavras = list((cfg.get("itens") or {}).get("palavras") or [])
    consultar = listar or listar_itens
    kwargs_extra: dict[str, Any] = {}
    if session is not None:
        kwargs_extra["session"] = session
    if pausa is not None:
        kwargs_extra["pausa"] = pausa

    for licitacao in licitacoes:
        cnpj = licitacao.get("orgao_cnpj")
        ano = licitacao.get("ano_compra")
        sequencial = licitacao.get("sequencial_compra")
        if not cnpj or ano is None or sequencial is None:
            licitacao["itens_interesse"] = []
            licitacao["qtd_itens_interesse"] = 0
            licitacao["valor_itens_interesse"] = 0.0
            licitacao["motivo_itens"] = "chaves PNCP ausentes para consultar itens"
            continue

        try:
            brutos = consultar(str(cnpj), ano, sequencial, **kwargs_extra)
        except ErroDetalhePNCP as erro:
            logger.warning(
                "Itens não obtidos para %s: %s",
                licitacao.get("numero_controle_pncp"),
                erro,
            )
            licitacao["itens_interesse"] = []
            licitacao["qtd_itens_interesse"] = 0
            licitacao["valor_itens_interesse"] = 0.0
            licitacao["motivo_itens"] = str(erro)
            continue

        extraidos = [_extrair_item(item) for item in brutos if isinstance(item, dict)]
        interesse = [
            item
            for item in extraidos
            if item_de_interesse(item.get("descricao"), palavras)
        ]
        licitacao["itens_interesse"] = interesse
        licitacao["qtd_itens_interesse"] = len(interesse)
        licitacao["valor_itens_interesse"] = _somar_valores(interesse)
        licitacao.pop("motivo_itens", None)

    return licitacoes
