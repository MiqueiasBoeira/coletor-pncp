import logging
import os
from datetime import date, datetime
from typing import Any

import gspread
import pandas as pd
from dotenv import load_dotenv

from exportacao import preparar_dataframe

logger = logging.getLogger(__name__)


class ErroGoogleSheets(Exception):
    """Falha ao gravar as licitações no Google Sheets."""


def autenticar_conta_de_serviço(caminho: str | None = None) -> gspread.Client:
    if caminho is None:
        load_dotenv()
        caminho = os.getenv("GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL")
    if not caminho:
        raise ErroGoogleSheets(
            "GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL não está definido"
        )
    return gspread.service_account(filename=caminho)


def exporta_grava_licitacoes_sheets(
    licitacoes: list[dict[str, Any]],
    *,
    gc: gspread.Client | None = None,
    id_planilha: str | None = None,
) -> None:
    if not licitacoes:
        logger.warning("Nenhuma licitação para gravar no Google Sheets")
        return

    if id_planilha is None:
        id_planilha = os.getenv("ID_SHEET_GOOGLE")
    if not id_planilha:
        raise ErroGoogleSheets(
            "ID_SHEET_GOOGLE não está definido. Sem ele a planilha não pode ser aberta."
        )

    if gc is None:
        gc = autenticar_conta_de_serviço()

    df = preparar_dataframe(licitacoes)
    aba = gc.open_by_key(id_planilha).sheet1
    aba.clear()
    aba.update(converter_dataframe_para_linhas(df))
    logger.info("Planilha Google atualizada com %d licitações", len(df))


def converter_dataframe_para_linhas(df: pd.DataFrame) -> list[list[Any]]:
    linhas = [list(df.columns)]
    for registro in df.itertuples(index=False, name=None):
        linhas.append([_valor_para_planilha(valor) for valor in registro])
    return linhas


def _valor_para_planilha(valor: Any) -> Any:
    if valor is None or pd.isna(valor):
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, bool | int | float | str):
        return valor
    item = getattr(valor, "item", None)
    if callable(item):
        return item()
    return str(valor)
