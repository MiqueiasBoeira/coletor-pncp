import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class ErroExportacao(Exception):
    """Falha ao gerar a planilha de licitações"""


COLUNAS_EXPORTACAO: dict[str, str] = {
    "numero_controle_pncp": "Número de Controle do PNCP",
    "orgao": "Órgão",
    "uf": "UF",
    "municipio": "Município",
    "modalidade": "Modalidade",
    "objeto": "Objeto",
    "valor_estimado": "Valor estimado",
    "data_publicacao_pncp": "Data de publicação no PNCP",
    "link_pncp": "Link do PNCP",
}


def preparar_dataframe(licitacoes: list[dict[str, Any]]) -> pd.DataFrame:
    if not licitacoes:
        df = pd.DataFrame(columns=list(COLUNAS_EXPORTACAO))
    else:
        df = pd.DataFrame(licitacoes)
        df = df[list(COLUNAS_EXPORTACAO)]
    df["data_publicacao_pncp"] = pd.to_datetime(df["data_publicacao_pncp"]).dt.date
    df = df.rename(columns=COLUNAS_EXPORTACAO)

    return df


def exportar_para_excel(licitacoes: list[dict[str, Any]], caminho: str | Path) -> None:
    if not licitacoes:
        logger.warning("Nenhuma licitação para exportar; planilha não gerada")
        return

    df = preparar_dataframe(licitacoes)

    try:
        df.to_excel(caminho, index=False)
    except PermissionError as erro:
        raise ErroExportacao(
            f"Sem permissão para gravar {caminho}. O arquivo está aberto no Excel?"
        ) from erro
    except OSError as erro:
        raise ErroExportacao(f"A pasta de destino de {caminho} não existe") from erro

    logger.info("Planilha gerada em %s com %d licitações", caminho, len(df))
