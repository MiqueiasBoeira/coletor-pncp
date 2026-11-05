"""Carrega criterios.yaml com defaults seguros."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CAMINHO_PADRAO = Path("criterios.yaml")

_DEFAULTS: dict[str, Any] = {
    "itens": {
        "palavras": [
            "computador",
            "notebook",
            "laptop",
            "desktop",
            "monitor",
            "mouse",
            "teclado",
            "impressora",
            "periférico",
            "perifericos",
        ]
    },
    "valor": {"min": 0, "max": 5_000_000},
    "prazo": {"dias_minimos_ate_abertura": 1},
    "edital": {"termos_obrigatorios": [], "termos_bloqueadores": []},
    "docs": {
        "tipos_prioritarios": {
            "edital_id": 2,
            "titulos_tr": [
                "termo de referência",
                "termo de referencia",
                "especificação",
                "especificacao",
            ],
        }
    },
    "perfil_usuario": (
        "Fornecedor de hardware e TI interessado em pregões eletrônicos."
    ),
}


def _mesclar(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    resultado = dict(base)
    for chave, valor in overlay.items():
        if (
            chave in resultado
            and isinstance(resultado[chave], dict)
            and isinstance(valor, dict)
        ):
            resultado[chave] = _mesclar(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado


def carregar_criterios(caminho: str | Path | None = None) -> dict[str, Any]:
    arquivo = Path(caminho) if caminho is not None else CAMINHO_PADRAO
    if not arquivo.exists():
        return dict(_DEFAULTS)
    with open(arquivo, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    if not isinstance(dados, dict):
        return dict(_DEFAULTS)
    return _mesclar(_DEFAULTS, dados)
