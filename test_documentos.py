from pathlib import Path

from documentos import enriquecer_com_documentos, selecionar_arquivos


def test_selecionar_edital_e_tr() -> None:
    arquivos = [
        {"titulo": "Aviso", "tipoDocumentoId": 1, "url": "https://x/a.pdf"},
        {"titulo": "Edital", "tipoDocumentoId": 2, "url": "https://x/e.pdf"},
        {
            "titulo": "Termo de Referência",
            "tipoDocumentoId": 9,
            "url": "https://x/tr.pdf",
        },
    ]

    escolhidos = selecionar_arquivos(
        arquivos,
        edital_id=2,
        titulos_tr=["termo de referência"],
    )

    assert [a["titulo"] for a in escolhidos] == ["Edital", "Termo de Referência"]


def test_enriquecer_usa_cache_e_extracao(tmp_path: Path) -> None:
    licitacoes = [
        {
            "numero_controle_pncp": "1/2026",
            "orgao_cnpj": "123",
            "ano_compra": 2026,
            "sequencial_compra": 1,
        }
    ]
    downloads: list[str] = []

    def listar(*_a, **_k):
        return [
            {"titulo": "Edital", "tipoDocumentoId": 2, "url": "https://x/e.pdf"},
        ]

    def baixar(url, **_k):
        downloads.append(url)
        return b"pdf-bytes"

    def extrair(_conteudo: bytes) -> str:
        return "Texto do edital com notebook"

    enriquecer_com_documentos(
        licitacoes,
        criterios={
            "docs": {"tipos_prioritarios": {"edital_id": 2, "titulos_tr": []}}
        },
        cache_dir=tmp_path,
        listar=listar,
        baixar=baixar,
        extrair=extrair,
    )

    assert licitacoes[0]["texto_edital"] == "Texto do edital com notebook"
    assert downloads == ["https://x/e.pdf"]
    assert (tmp_path / "123_2026_1" / "Edital.pdf").exists()

    downloads.clear()
    enriquecer_com_documentos(
        licitacoes,
        criterios={
            "docs": {"tipos_prioritarios": {"edital_id": 2, "titulos_tr": []}}
        },
        cache_dir=tmp_path,
        listar=listar,
        baixar=baixar,
        extrair=extrair,
    )
    assert downloads == []


def test_falha_extracao_registra_motivo() -> None:
    licitacoes = [
        {
            "numero_controle_pncp": "1/2026",
            "orgao_cnpj": "123",
            "ano_compra": 2026,
            "sequencial_compra": 1,
        }
    ]

    enriquecer_com_documentos(
        licitacoes,
        criterios={
            "docs": {"tipos_prioritarios": {"edital_id": 2, "titulos_tr": []}}
        },
        cache_dir=None,
        listar=lambda *_a, **_k: [
            {"titulo": "Edital", "tipoDocumentoId": 2, "url": "https://x/e.pdf"}
        ],
        baixar=lambda *_a, **_k: b"x",
        extrair=lambda _c: (_ for _ in ()).throw(ValueError("pdf quebrado")),
    )

    assert licitacoes[0]["texto_edital"] == ""
    assert "pdf quebrado" in licitacoes[0]["motivo_extracao"]
