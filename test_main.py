import json
from pathlib import Path

import pandas as pd

from busca_api_pncp import ErroConsultaPNCP
from main import main
from manipular_google_sheets import ErroGoogleSheets


def completo(objeto: str, sequencial: int) -> dict:
    return {
        "orgaoEntidade": {"cnpj": "87613071000148"},
        "anoCompra": 2026,
        "sequencialCompra": sequencial,
        "numeroControlePNCP": f"87613071000148-1-{sequencial:06d}/2026",
        "unidadeOrgao": {
            "nomeUnidade": "PREFEITURA",
            "ufSigla": "RS",
            "municipioNome": "Santo Ângelo",
        },
        "modalidadeNome": "Pregão - Eletrônico",
        "objetoCompra": objeto,
        "valorTotalEstimado": 10.0,
        "dataPublicacaoPncp": "2026-10-15T00:10:40",
    }


def salvar(tmp_path: Path, registros: list[dict]) -> Path:
    arquivo = tmp_path / "pub.json"
    arquivo.write_text(json.dumps({"data": registros}), encoding="utf-8")
    return arquivo


def test_main_exporta_so_quem_tem_a_palavra(tmp_path: Path) -> None:
    arquivo = salvar(
        tmp_path,
        [
            completo("Aquisição de computadores", 1),
            completo("Aquisição de cadeiras", 2),
        ],
    )
    saida = tmp_path / "out.xlsx"

    codigo = main(
        ["--arquivo", str(arquivo), "--saida", str(saida), "--palavras", "computador"]
    )

    assert codigo == 0
    df = pd.read_excel(saida)
    assert len(df) == 1
    assert "computador" in df.loc[0, "Objeto"].lower()


def test_arquivo_nao_consulta_a_api(monkeypatch, tmp_path: Path) -> None:
    def boom(*args, **kwargs):
        raise AssertionError("consultou a API")

    monkeypatch.setattr("main.buscar_registros_pncp", boom)
    arquivo = salvar(tmp_path, [completo("Aquisição de computadores", 1)])

    codigo = main(["--arquivo", str(arquivo), "--saida", str(tmp_path / "out.xlsx")])

    assert codigo == 0


def test_arquivo_ausente_devolve_1(tmp_path: Path) -> None:
    saida = tmp_path / "out.xlsx"

    codigo = main(["--arquivo", str(tmp_path / "nao.json"), "--saida", str(saida)])

    assert codigo == 1
    assert not saida.exists()


def test_json_invalido_devolve_1(tmp_path: Path) -> None:
    arquivo = tmp_path / "pub.json"
    arquivo.write_text("{", encoding="utf-8")

    codigo = main(["--arquivo", str(arquivo), "--saida", str(tmp_path / "out.xlsx")])

    assert codigo == 1


def test_falha_na_api_nao_exporta(monkeypatch, tmp_path: Path) -> None:
    def boom(*args, **kwargs):
        raise ErroConsultaPNCP("página 2")

    monkeypatch.setattr("main.buscar_registros_pncp", boom)
    saida = tmp_path / "out.xlsx"

    assert main(["--saida", str(saida)]) == 1
    assert not saida.exists()


def test_repassa_os_parametros_da_consulta(monkeypatch, tmp_path: Path) -> None:
    capturado = {}

    def fake(data_inicial, data_final, codigo, uf, tamanho, **kwargs):
        capturado.update(
            data_inicial=data_inicial,
            data_final=data_final,
            codigo=codigo,
            uf=uf,
        )
        return []

    monkeypatch.setattr("main.buscar_registros_pncp", fake)
    saida = tmp_path / "out.xlsx"

    codigo = main(
        [
            "--data-inicial",
            "20261001",
            "--data-final",
            "20261015",
            "--uf",
            "SC",
            "--modalidade",
            "6",
            "--saida",
            str(saida),
        ]
    )

    assert codigo == 0
    assert capturado == {
        "data_inicial": "20261001",
        "data_final": "20261015",
        "codigo": 6,
        "uf": "SC",
    }
    assert not saida.exists()


def test_falha_no_sheets_devolve_2_e_deixa_o_excel(monkeypatch, tmp_path: Path) -> None:
    def falha(licitacoes, **kwargs):
        raise ErroGoogleSheets("sem planilha")

    monkeypatch.setattr("main.exporta_grava_licitacoes_sheets", falha)
    arquivo = salvar(tmp_path, [completo("Aquisição de computadores", 1)])
    saida = tmp_path / "out.xlsx"

    codigo = main(
        [
            "--arquivo",
            str(arquivo),
            "--saida",
            str(saida),
            "--palavras",
            "computador",
            "--sheets",
        ]
    )

    assert codigo == 2
    assert saida.exists()
