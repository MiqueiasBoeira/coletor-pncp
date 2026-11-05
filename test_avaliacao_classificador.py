"""Avaliação com API real. Não roda no pytest padrão.

Marque objetos com a categoria que você considera correta e meça o acerto.

    RUN_AVALIACAO=1 ANTHROPIC_API_KEY=... uv run pytest -m avaliacao -q
"""

from __future__ import annotations

import os

import pytest

from classificador import classificar_objeto

# Você, que conhece licitação, define a categoria esperada.
AMOSTRAS = [
    ("Aquisição de notebooks e monitores para laboratório de informática", "hardware"),
    ("Contratação de serviço de limpeza predial", "servicos"),
    ("Aquisição de cadeiras escolares empilháveis", "mobiliario"),
    ("Licenças de software de escritório por 12 meses", "software"),
    ("Registro de preços de computadores desktop", "hardware"),
]


@pytest.mark.avaliacao
def test_categorias_bate_com_o_gabarito() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY ausente")
    if os.getenv("RUN_AVALIACAO") != "1":
        pytest.skip("Defina RUN_AVALIACAO=1 para gastar tokens de propósito")

    acertos = 0
    for objeto, esperada in AMOSTRAS:
        resultado = classificar_objeto(objeto)
        if resultado.categoria.lower() == esperada.lower():
            acertos += 1

    taxa = acertos / len(AMOSTRAS)
    assert taxa >= 0.6, f"acertou {acertos}/{len(AMOSTRAS)} ({taxa:.0%})"
