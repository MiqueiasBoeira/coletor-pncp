"""Funil determinístico e auditável sobre metadados + texto do edital."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from criterios import carregar_criterios

logger = logging.getLogger(__name__)


def _parse_data(valor: Any) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], fmt).date()
        except ValueError:
            continue
    return None


def _texto_edital(licitacao: dict[str, Any]) -> str:
    return (licitacao.get("texto_edital") or "").lower()


def avaliar_licitacao(
    licitacao: dict[str, Any],
    criterios: dict[str, Any],
    *,
    hoje: date | None = None,
) -> str | None:
    """Devolve motivo_descarte ou None se aprovada."""
    qtd = int(licitacao.get("qtd_itens_interesse") or 0)
    if qtd < 1:
        return "sem item de interesse"

    valor_cfg = criterios.get("valor") or {}
    minimo = float(valor_cfg.get("min") or 0)
    maximo = float(valor_cfg.get("max") if valor_cfg.get("max") is not None else 1e18)
    valor = float(licitacao.get("valor_itens_interesse") or 0)
    if valor < minimo:
        return f"valor itens interesse abaixo do mínimo ({valor} < {minimo})"
    if valor > maximo:
        return f"valor itens interesse acima do máximo ({valor} > {maximo})"

    prazo_cfg = criterios.get("prazo") or {}
    dias_min = int(prazo_cfg.get("dias_minimos_ate_abertura") or 0)
    data_abertura = _parse_data(licitacao.get("data_abertura_proposta"))
    if data_abertura is not None and dias_min > 0:
        referencia = hoje or date.today()
        dias = (data_abertura - referencia).days
        if dias < dias_min:
            return (
                f"prazo insuficiente até abertura "
                f"({dias} dias < {dias_min} exigidos)"
            )

    edital_cfg = criterios.get("edital") or {}
    texto = _texto_edital(licitacao)
    for bloqueador in edital_cfg.get("termos_bloqueadores") or []:
        termo = str(bloqueador).lower().strip()
        if termo and termo in texto:
            return f"termo bloqueador no edital: {bloqueador}"
    obrigatorios = [
        str(t).lower().strip()
        for t in (edital_cfg.get("termos_obrigatorios") or [])
        if str(t).strip()
    ]
    if obrigatorios:
        if not texto:
            return "edital sem texto para verificar termos obrigatórios"
        faltando = [t for t in obrigatorios if t not in texto]
        if faltando:
            return f"termos obrigatórios ausentes: {', '.join(faltando)}"

    return None


def aplicar_funil(
    licitacoes: list[dict[str, Any]],
    *,
    criterios: dict[str, Any] | None = None,
    hoje: date | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa aprovadas e descartadas (com motivo_descarte)."""
    cfg = criterios if criterios is not None else carregar_criterios()
    aprovadas: list[dict[str, Any]] = []
    descartadas: list[dict[str, Any]] = []
    for licitacao in licitacoes:
        motivo = avaliar_licitacao(licitacao, cfg, hoje=hoje)
        if motivo is None:
            licitacao.pop("motivo_descarte", None)
            aprovadas.append(licitacao)
        else:
            licitacao["motivo_descarte"] = motivo
            descartadas.append(licitacao)
            logger.info(
                "Funil descartou %s: %s",
                licitacao.get("numero_controle_pncp"),
                motivo,
            )
    logger.info(
        "Funil: %d aprovadas, %d descartadas",
        len(aprovadas),
        len(descartadas),
    )
    return aprovadas, descartadas
