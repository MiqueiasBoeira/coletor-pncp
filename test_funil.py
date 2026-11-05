from datetime import date

from funil import aplicar_funil, avaliar_licitacao

CRITERIOS = {
    "valor": {"min": 1000, "max": 100000},
    "prazo": {"dias_minimos_ate_abertura": 2},
    "edital": {
        "termos_obrigatorios": ["pregão"],
        "termos_bloqueadores": ["exclusividade"],
    },
}


def base(**overrides):
    item = {
        "numero_controle_pncp": "1/2026",
        "qtd_itens_interesse": 1,
        "valor_itens_interesse": 5000,
        "data_abertura_proposta": "2026-11-20",
        "texto_edital": "Modalidade pregão eletrônico sem restrições",
    }
    item.update(overrides)
    return item


def test_aprovada_sem_motivo() -> None:
    assert avaliar_licitacao(base(), CRITERIOS, hoje=date(2026, 11, 10)) is None


def test_sem_item_descarta() -> None:
    assert avaliar_licitacao(base(qtd_itens_interesse=0), CRITERIOS) == (
        "sem item de interesse"
    )


def test_valor_fora_da_faixa() -> None:
    motivo = avaliar_licitacao(base(valor_itens_interesse=50), CRITERIOS)
    assert "mínimo" in motivo


def test_termo_bloqueador() -> None:
    motivo = avaliar_licitacao(
        base(texto_edital="Exige exclusividade de marca"),
        CRITERIOS,
        hoje=date(2026, 11, 10),
    )
    assert "bloqueador" in motivo


def test_aplicar_funil_separa() -> None:
    aprovadas, descartadas = aplicar_funil(
        [base(), base(qtd_itens_interesse=0, numero_controle_pncp="2/2026")],
        criterios=CRITERIOS,
        hoje=date(2026, 11, 10),
    )
    assert len(aprovadas) == 1
    assert descartadas[0]["motivo_descarte"] == "sem item de interesse"
