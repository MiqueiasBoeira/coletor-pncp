import json
from pathlib import Path

from fastapi.testclient import TestClient

from api import criar_app
from test_classificador import ClienteFalso


def _app(tmp_path: Path) -> TestClient:
    return TestClient(
        criar_app(
            cliente_classificador=ClienteFalso(),
            caminho_cache=tmp_path / "cache.json",
        )
    )


def test_saude() -> None:
    resposta = TestClient(criar_app(cliente_classificador=ClienteFalso())).get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_sem_api_key_devolve_401(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("API_KEY_OPORTUNIDADES", "segredo")
    cliente = _app(tmp_path)

    resposta = cliente.get("/oportunidades", params={"arquivo": str(tmp_path / "x.json")})

    assert resposta.status_code == 401


def test_oportunidades_com_arquivo_e_classificacao(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("API_KEY_OPORTUNIDADES", "segredo")
    arquivo = tmp_path / "pub.json"
    arquivo.write_text(
        json.dumps(
            {
                "data": [
                    {
                        "orgaoEntidade": {"cnpj": "1"},
                        "anoCompra": 2026,
                        "sequencialCompra": 1,
                        "numeroControlePNCP": "1-1-000001/2026",
                        "unidadeOrgao": {
                            "nomeUnidade": "Pref",
                            "ufSigla": "RS",
                            "municipioNome": "POA",
                        },
                        "modalidadeNome": "Pregão",
                        "objetoCompra": "Aquisição de computadores",
                        "valorTotalEstimado": 10,
                        "dataPublicacaoPncp": "2026-10-15T00:00:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cliente = _app(tmp_path)

    resposta = cliente.get(
        "/oportunidades",
        headers={"X-API-Key": "segredo"},
        params={
            "arquivo": str(arquivo),
            "palavras": ["computador"],
            "relevancia_minima": 7,
            "classificar": True,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["quantidade"] == 1
    assert corpo["itens"][0]["relevancia"] == 8
    assert corpo["tokens"]["chamadas"] == 1
