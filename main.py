import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from busca_api_pncp import ErroConsultaPNCP, buscar_registros_pncp
from exportacao import ErroExportacao, exportar_para_excel
from manipular_google_sheets import ErroGoogleSheets, exporta_grava_licitacoes_sheets
from processa_licitacoes import filtrar_e_validar

logger = logging.getLogger(__name__)

PALAVRAS_CHAVE = ["computador", "notebook"]
DATA_INICIAL = "20261001"
DATA_FINAL = "20261031"
# 6 = Pregão Eletrônico, o mesmo código que a API devolve em modalidadeId.
CODIGO_MODALIDADE_PREGAO_ELETRONICO = 6
UF = "RS"
TAMANHO_PAGINA = 50
CAMINHO_EXCEL = Path("pasta_de_exportacao/licitacoes.xlsx")


class ErroLeituraArquivoLicitacoesJSON(Exception):
    """Falha ao ler o arquivo publicacaoPNCP.json"""


def carregar_arquivo_publicacao_pncp(caminho: Path) -> list[dict[str, Any]]:
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError as erro:
        raise ErroLeituraArquivoLicitacoesJSON(
            f"Arquivo não encontrado: {caminho}"
        ) from erro
    except json.JSONDecodeError as erro:
        raise ErroLeituraArquivoLicitacoesJSON(
            f"JSON inválido em {caminho}: {erro}"
        ) from erro

    if "data" not in dados:
        raise ErroLeituraArquivoLicitacoesJSON(f"Chave 'data' ausente em {caminho}")
    return dados["data"]


def executar(
    licitacoes: list[dict[str, Any]],
    palavras_chave: list[str],
    caminho_excel: str | Path,
    *,
    gravar_sheets: bool = False,
) -> tuple[list[dict], list[dict]]:
    validadas, erros = filtrar_e_validar(licitacoes, palavras_chave)
    logger.info("Validadas: %d, descartadas: %d", len(validadas), len(erros))
    exportar_para_excel(validadas, caminho_excel)
    if gravar_sheets:
        exporta_grava_licitacoes_sheets(validadas)
    return validadas, erros


def obter_registros(argumentos: argparse.Namespace) -> list[dict[str, Any]]:
    if argumentos.arquivo is not None:
        return carregar_arquivo_publicacao_pncp(argumentos.arquivo)
    return buscar_registros_pncp(
        argumentos.data_inicial,
        argumentos.data_final,
        argumentos.modalidade,
        argumentos.uf,
        argumentos.tamanho_pagina,
    )


def construir_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Busca licitações no PNCP, filtra por palavra-chave e exporta."
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        help="JSON local no formato da API. Sem este argumento, consulta o PNCP.",
    )
    parser.add_argument("--data-inicial", default=DATA_INICIAL)
    parser.add_argument("--data-final", default=DATA_FINAL)
    parser.add_argument("--uf", default=UF)
    parser.add_argument(
        "--modalidade",
        type=int,
        default=CODIGO_MODALIDADE_PREGAO_ELETRONICO,
    )
    parser.add_argument("--tamanho-pagina", type=int, default=TAMANHO_PAGINA)
    parser.add_argument("--saida", type=Path, default=CAMINHO_EXCEL)
    parser.add_argument("--palavras", nargs="+", default=list(PALAVRAS_CHAVE))
    parser.add_argument(
        "--sheets",
        action="store_true",
        help="Também grava na planilha Google configurada no .env",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
    )
    load_dotenv()
    argumentos = construir_argumentos(argv)
    try:
        registros = obter_registros(argumentos)
        executar(
            registros,
            argumentos.palavras,
            argumentos.saida,
            gravar_sheets=argumentos.sheets,
        )
    except (ErroLeituraArquivoLicitacoesJSON, ErroConsultaPNCP) as erro:
        logger.error("%s", erro)
        return 1
    except (ErroExportacao, ErroGoogleSheets) as erro:
        logger.error("%s", erro)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
