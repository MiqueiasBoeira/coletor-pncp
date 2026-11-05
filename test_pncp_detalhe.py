import pytest
import requests

from pncp_detalhe import (
    ErroDetalhePNCP,
    baixar_arquivo,
    listar_arquivos,
    listar_itens,
)


class RespostaFalsa:
    def __init__(
        self, payload: dict | list | None = None, status: int = 200, content: bytes = b""
    ) -> None:
        self.payload = payload
        self.status_code = status
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self) -> dict | list:
        return self.payload


class SessaoFalsa:
    def __init__(self, respostas: list) -> None:
        self._respostas = list(respostas)
        self.chamadas: list[dict] = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append({"url": url, "params": params, "timeout": timeout})
        return self._respostas.pop(0)

    def close(self) -> None:
        return None


def test_listar_itens_pagina_e_pausa() -> None:
    sessao = SessaoFalsa(
        [
            RespostaFalsa(
                {
                    "totalPaginas": 2,
                    "data": [{"numeroItem": 1, "descricao": "Notebook"}],
                }
            ),
            RespostaFalsa(
                {
                    "totalPaginas": 2,
                    "data": [{"numeroItem": 2, "descricao": "Mouse"}],
                }
            ),
        ]
    )
    pausas: list[float] = []

    resultado = listar_itens(
        "123",
        2026,
        10,
        session=sessao,
        pausa=pausas.append,
    )

    assert [item["numeroItem"] for item in resultado] == [1, 2]
    assert "itens" in sessao.chamadas[0]["url"]
    assert sessao.chamadas[0]["params"]["pagina"] == 1
    assert pausas == [1]


def test_listar_itens_lista_direta() -> None:
    sessao = SessaoFalsa(
        [RespostaFalsa([{"numeroItem": 1, "descricao": "Desktop"}])]
    )

    assert listar_itens("1", 2026, 1, session=sessao) == [
        {"numeroItem": 1, "descricao": "Desktop"}
    ]


def test_listar_itens_erro_http() -> None:
    sessao = SessaoFalsa([RespostaFalsa({}, status=500)])

    with pytest.raises(ErroDetalhePNCP, match="itens"):
        listar_itens("1", 2026, 1, session=sessao)


def test_listar_arquivos() -> None:
    sessao = SessaoFalsa(
        [
            RespostaFalsa(
                [
                    {
                        "titulo": "Edital",
                        "tipoDocumentoId": 2,
                        "url": "https://exemplo/edital.pdf",
                    }
                ]
            )
        ]
    )

    arquivos = listar_arquivos("1", 2026, 1, session=sessao)

    assert arquivos[0]["tipoDocumentoId"] == 2
    assert "arquivos" in sessao.chamadas[0]["url"]


def test_baixar_arquivo() -> None:
    sessao = SessaoFalsa([RespostaFalsa(content=b"%PDF-1.4")])

    assert baixar_arquivo("https://exemplo/a.pdf", session=sessao) == b"%PDF-1.4"
