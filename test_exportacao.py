import logging
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from exportacao import ErroExportacao, exportar_para_excel, preparar_dataframe


@pytest.fixture
def licitacoes():
    return [
        {
            "numero_controle_pncp": "87613071000148-1-000413/2026",
            "orgao": "PREFEITURA MUNICIPAL DE SANTO ÂNGELO",
            "uf": "RS",
            "municipio": "Santo Ângelo",
            "modalidade": "Pregão - Eletrônico",
            "objeto": "REGISTRO DE PREÇOS DE COMPUTADORES, NOTEBOOKS E LICENÇAS PERPÉTUAS, PARA USO DAS DIVERSAS SECRETARIAS E DEPARTAMENTOS",
            "valor_estimado": 3795370.0,
            "data_publicacao_pncp": "2026-10-15T00:10:40",
            "link_pncp": "https://pncp.gov.br/app/editais/87613071000148/2026/413",
        },
        {
            "numero_controle_pncp": "87613485000177-1-000112/2026",
            "orgao": "Prefeitura Municipal de Victor Graeff",
            "uf": "RS",
            "municipio": "Victor Graeff",
            "modalidade": "Pregão - Eletrônico",
            "objeto": "[Portal de Compras Públicas] - Aquisição de computadores e de infraestrutura completa de tecnologia da informação, para implantação de Telecentro na Escola Municipal Leonel de Moura Brizola, bem como a aquisição de computadores destinados às Secretarias Municipais, conforme condições, quantidades, exigências e especificações técnicas estabelecidas neste Termo de Referência e seus anexos.",
            "valor_estimado": 293615.54,
            "data_publicacao_pncp": "2026-10-15T07:40:29",
            "link_pncp": "https://pncp.gov.br/app/editais/87613485000177/2026/112",
        },
    ]


ORDEM_DAS_COLUNAS = [
    "Número de Controle do PNCP",
    "Órgão",
    "UF",
    "Município",
    "Modalidade",
    "Objeto",
    "Valor estimado",
    "Data de publicação no PNCP",
    "Link do PNCP",
]


def test_gera_arquivo(tmp_path: str | Path, licitacoes: list[dict[str, Any]]) -> None:
    caminho = tmp_path / "licitacoes.xlsx"

    exportar_para_excel(licitacoes, caminho)

    assert caminho.exists()


def test_cabecalhos_na_ordem(
    tmp_path: str | Path, licitacoes: list[dict[str, Any]]
) -> None:

    caminho = tmp_path / "licitacoes.xlsx"

    exportar_para_excel(licitacoes, caminho)

    df = pd.read_excel(caminho)

    lista = list(df.columns)

    assert lista == ORDEM_DAS_COLUNAS


def test_verifica_tipo_de_colunas(
    tmp_path: Path, licitacoes: list[dict[str, Any]]
) -> None:

    caminho = tmp_path / "licitacoes.xlsx"

    exportar_para_excel(licitacoes, caminho)

    df = pd.read_excel(caminho)

    assert pd.api.types.is_numeric_dtype(df["Valor estimado"]), df[
        "Valor estimado"
    ].dtype
    assert pd.api.types.is_datetime64_any_dtype(df["Data de publicação no PNCP"]), df[
        "Data de publicação no PNCP"
    ].dtype


def test_preparar_dataframe(licitacoes: list[dict[str, Any]]) -> None:

    resultado = preparar_dataframe(licitacoes)

    lista = list(resultado.columns)

    assert len(resultado) == len(licitacoes)
    assert lista == ORDEM_DAS_COLUNAS


def test_lista_vazia_nao_gera_arquivo(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caminho = tmp_path / "licitacoes.xlsx"

    with caplog.at_level(logging.WARNING, logger="exportacao"):
        exportar_para_excel([], caminho)

    assert not caminho.exists()
    assert "planilha não gerada" in caplog.text


def test_preparar_dataframe_vazio() -> None:
    resultado = preparar_dataframe([])

    assert list(resultado.columns) == ORDEM_DAS_COLUNAS
    assert len(resultado) == 0


def test_pasta_inexistente_explica_o_erro(
    tmp_path: Path, licitacoes: list[dict[str, Any]]
) -> None:
    caminho = tmp_path / "nao_existe" / "licitacoes.xlsx"

    with pytest.raises(ErroExportacao, match="não existe"):
        exportar_para_excel(licitacoes, caminho)
