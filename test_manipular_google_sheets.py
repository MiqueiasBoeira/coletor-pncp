import logging
from unittest.mock import patch

import pytest

from exportacao import COLUNAS_EXPORTACAO
from manipular_google_sheets import (
    ErroGoogleSheets,
    autenticar_conta_de_serviço,
    exporta_grava_licitacoes_sheets,
)


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


def test_autenticar_conta_de_serviço(monkeypatch: pytest.MonkeyPatch) -> None:

    caminho_falso = ".config/gspread/service_account_kleviq.json"
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL", caminho_falso)

    with patch(
        "manipular_google_sheets.gspread.service_account"
    ) as mock_service_account:
        resultado = autenticar_conta_de_serviço()

        mock_service_account.assert_called_once_with(filename=caminho_falso)
        assert resultado is mock_service_account.return_value


def test_caminho_lido_na_hora_da_chamada(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch(
        "manipular_google_sheets.gspread.service_account"
    ) as mock_service_account:
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL", "primeiro.json")
        autenticar_conta_de_serviço()
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_GSPREAD_CREDENTIAL", "segundo.json")
        autenticar_conta_de_serviço()

    filenames = [
        chamada.kwargs["filename"] for chamada in mock_service_account.call_args_list
    ]
    assert filenames == ["primeiro.json", "segundo.json"]


class AbaFalsa:
    def __init__(self) -> None:
        self.limpou = False
        self.valores = None

    def clear(self) -> dict:
        self.limpou = True
        return {}

    def update(self, values, range_name=None, **kwargs) -> dict:
        self.valores = values
        return {}


class PlanilhaFalsa:
    def __init__(self) -> None:
        self.sheet1 = AbaFalsa()


class ClienteFalso:
    def __init__(self) -> None:
        self.planilha = PlanilhaFalsa()
        self.chave = None

    def open_by_key(self, chave: str) -> PlanilhaFalsa:
        self.chave = chave
        return self.planilha


def test_grava_cabecalhos_e_valores(
    monkeypatch: pytest.MonkeyPatch, licitacoes: list[dict]
) -> None:
    cliente = ClienteFalso()
    monkeypatch.setenv("ID_SHEET_GOOGLE", "planilha-xyz")

    exporta_grava_licitacoes_sheets(licitacoes, gc=cliente)

    aba = cliente.planilha.sheet1
    assert cliente.chave == "planilha-xyz"
    assert aba.limpou
    cabecalhos_esperados = [
        COLUNAS_EXPORTACAO[nome]
        for nome in COLUNAS_EXPORTACAO
        if nome in licitacoes[0]
    ]
    assert aba.valores[0] == cabecalhos_esperados
    assert len(aba.valores) == len(licitacoes) + 1
    assert aba.valores[1][0] == licitacoes[0]["numero_controle_pncp"]
    assert aba.valores[1][6] == licitacoes[0]["valor_estimado"]
    assert aba.valores[1][7] == "2026-10-15"


def test_lista_vazia_nao_abre_planilha(caplog: pytest.LogCaptureFixture) -> None:
    cliente = ClienteFalso()

    with caplog.at_level(logging.WARNING, logger="manipular_google_sheets"):
        exporta_grava_licitacoes_sheets([], gc=cliente, id_planilha="abc")

    assert cliente.chave is None
    assert "Nenhuma licitação" in caplog.text


def test_id_ausente_nao_autentica(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ID_SHEET_GOOGLE", raising=False)

    with patch(
        "manipular_google_sheets.gspread.service_account"
    ) as mock_service_account:
        with pytest.raises(ErroGoogleSheets, match="ID_SHEET_GOOGLE"):
            exporta_grava_licitacoes_sheets([{"numero_controle_pncp": "x"}])
        mock_service_account.assert_not_called()
