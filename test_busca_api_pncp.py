import pytest
import requests

from busca_api_pncp import ErroConsultaPNCP, buscar_registros_pncp


class RespostaFalsa:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self) -> dict:
        return self.payload


class SessaoFalsa:
    def __init__(self, respostas: list) -> None:
        self._respostas = list(respostas)
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append({"url": url, "params": params, "timeout": timeout})
        return self._respostas.pop(0)


def consultar(sessao: SessaoFalsa, pausa=lambda _segundos: None):
    return buscar_registros_pncp(
        "20261001",
        "20261031",
        6,
        "RS",
        50,
        session=sessao,
        pausa=pausa,
    )


def test_percorre_todas_as_paginas_e_pausa_entre_elas() -> None:
    sessao = SessaoFalsa(
        [
            RespostaFalsa({"totalPaginas": 2, "data": [{"id": 1}]}),
            RespostaFalsa({"totalPaginas": 2, "data": [{"id": 2}]}),
        ]
    )
    pausas = []

    resultado = consultar(sessao, pausa=pausas.append)

    assert resultado == [{"id": 1}, {"id": 2}]
    assert [chamada["params"]["pagina"] for chamada in sessao.chamadas] == [1, 2]
    assert sessao.chamadas[0]["params"]["uf"] == "RS"
    assert "contratacoes/publicacao" in sessao.chamadas[0]["url"]
    assert pausas == [1]


def test_uma_pagina_nao_pausa() -> None:
    sessao = SessaoFalsa([RespostaFalsa({"totalPaginas": 1, "data": [{"id": 1}]})])
    pausas = []

    assert consultar(sessao, pausa=pausas.append) == [{"id": 1}]
    assert pausas == []


def test_data_vazia_devolve_lista_vazia() -> None:
    sessao = SessaoFalsa([RespostaFalsa({"totalPaginas": 1, "data": []})])

    assert consultar(sessao) == []


def test_erro_na_segunda_pagina_cancela_a_consulta() -> None:
    sessao = SessaoFalsa(
        [
            RespostaFalsa({"totalPaginas": 2, "data": [{"id": 1}]}),
            RespostaFalsa({}, status=500),
        ]
    )

    with pytest.raises(ErroConsultaPNCP, match="página 2"):
        consultar(sessao)


def test_resposta_sem_total_de_paginas_cancela_a_consulta() -> None:
    sessao = SessaoFalsa([RespostaFalsa({"data": []})])

    with pytest.raises(ErroConsultaPNCP, match="página 1"):
        consultar(sessao)
