from processa_licitacoes import (
    filtrar_e_validar,
    filtrar_licitacoes,
    transformar_licitacao,
    validar_licitacoes,
)


def registro(**overrides):
    base = {
        "orgaoEntidade": {"cnpj": "87613071000148"},
        "anoCompra": 2026,
        "sequencialCompra": 413,
        "numeroControlePNCP": "87613071000148-1-000413/2026",
        "unidadeOrgao": {
            "nomeUnidade": "PREFEITURA MUNICIPAL DE SANTO ÂNGELO",
            "ufSigla": "RS",
            "municipioNome": "Santo Ângelo",
        },
        "modalidadeNome": "Pregão - Eletrônico",
        "objetoCompra": "Aquisição de computadores e notebooks",
        "valorTotalEstimado": 3795370.0,
        "dataPublicacaoPncp": "2026-10-15T00:10:40",
    }
    base.update(overrides)
    return base


def test_palavra_em_maiusculas_entra() -> None:
    item = registro(objetoCompra="AQUISIÇÃO DE NOTEBOOKS")

    assert filtrar_licitacoes([item], ["notebook"]) == [item]


def test_sem_palavra_fica_de_fora() -> None:
    item = registro(objetoCompra="Aquisição de cadeiras")

    assert filtrar_licitacoes([item], ["computador", "notebook"]) == []


def test_objeto_ausente_ou_nulo_fica_de_fora() -> None:
    sem_objeto = registro()
    del sem_objeto["objetoCompra"]

    assert filtrar_licitacoes([sem_objeto], ["computador"]) == []
    assert filtrar_licitacoes([registro(objetoCompra=None)], ["computador"]) == []


def test_palavras_vazias_nao_deixam_passar_tudo() -> None:
    assert filtrar_licitacoes([registro()], []) == []


def test_transformar_monta_link_e_campos() -> None:
    resultado = transformar_licitacao(registro())

    assert resultado["link_pncp"] == (
        "https://pncp.gov.br/app/editais/87613071000148/2026/413"
    )
    assert resultado["orgao"] == "PREFEITURA MUNICIPAL DE SANTO ÂNGELO"
    assert resultado["municipio"] == "Santo Ângelo"
    assert resultado["valor_estimado"] == 3795370.0


def test_registro_incompleto_vai_para_erros_e_o_valido_passa() -> None:
    incompleto = {
        "objetoCompra": "notebook para o laboratório",
        "numeroControlePNCP": "sem-dados/2026",
    }

    validadas, erros = validar_licitacoes([registro(), incompleto])

    assert len(validadas) == 1
    assert erros[0]["numero_controle_pncp"] == "sem-dados/2026"
    assert "sem-dados/2026" in erros[0]["motivo_erro"]


def test_filtrar_e_validar_nao_avalia_quem_ficou_de_fora() -> None:
    fora_e_incompleto = {"objetoCompra": "cadeira"}

    validadas, erros = filtrar_e_validar(
        [registro(), fora_e_incompleto], ["computador"]
    )

    assert len(validadas) == 1
    assert erros == []
