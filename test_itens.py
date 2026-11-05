from itens import enriquecer_com_itens, item_de_interesse
from pncp_detalhe import ErroDetalhePNCP


def test_item_de_interesse_case_insensitive() -> None:
    assert item_de_interesse("Aquisição de NOTEBOOKS", ["notebook"])
    assert not item_de_interesse("Cadeiras", ["notebook"])


def test_enriquecer_marca_itens_e_agrega_valor() -> None:
    licitacoes = [
        {
            "numero_controle_pncp": "1/2026",
            "orgao_cnpj": "123",
            "ano_compra": 2026,
            "sequencial_compra": 1,
        }
    ]

    def listar(_cnpj, _ano, _seq, **_kwargs):
        return [
            {
                "numeroItem": 1,
                "descricao": "Notebook i5",
                "quantidade": 10,
                "unidadeMedida": "UN",
                "valorUnitarioEstimado": 3000,
                "valorTotal": 30000,
                "materialOuServicoNome": "Material",
                "criterioJulgamentoNome": "Menor Preço",
                "situacaoCompraItemNome": "Homologado",
            },
            {
                "numeroItem": 2,
                "descricao": "Cadeira giratória",
                "quantidade": 5,
                "unidadeMedida": "UN",
                "valorUnitarioEstimado": 400,
                "valorTotal": 2000,
                "materialOuServicoNome": "Material",
                "criterioJulgamentoNome": "Menor Preço",
                "situacaoCompraItemNome": "Homologado",
            },
        ]

    enriquecer_com_itens(
        licitacoes,
        criterios={"itens": {"palavras": ["notebook"]}},
        listar=listar,
    )

    assert licitacoes[0]["qtd_itens_interesse"] == 1
    assert licitacoes[0]["valor_itens_interesse"] == 30000.0
    assert licitacoes[0]["itens_interesse"][0]["numeroItem"] == 1


def test_falha_de_api_nao_cancela_lote() -> None:
    licitacoes = [
        {
            "numero_controle_pncp": "1/2026",
            "orgao_cnpj": "123",
            "ano_compra": 2026,
            "sequencial_compra": 1,
        },
        {
            "numero_controle_pncp": "2/2026",
            "orgao_cnpj": "456",
            "ano_compra": 2026,
            "sequencial_compra": 2,
        },
    ]

    def listar(cnpj, _ano, _seq, **_kwargs):
        if cnpj == "123":
            raise ErroDetalhePNCP("falha")
        return [{"numeroItem": 1, "descricao": "computador", "valorTotal": 100}]

    enriquecer_com_itens(
        licitacoes,
        criterios={"itens": {"palavras": ["computador"]}},
        listar=listar,
    )

    assert licitacoes[0]["qtd_itens_interesse"] == 0
    assert "falha" in licitacoes[0]["motivo_itens"]
    assert licitacoes[1]["qtd_itens_interesse"] == 1
