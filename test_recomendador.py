from pathlib import Path
from types import SimpleNamespace

from recomendador import (
    _montar_recomendacao,
    recomendar_licitacao,
    recomendar_licitacoes,
)


class BlocoFerramenta:
    def __init__(self, entrada: dict) -> None:
        self.type = "tool_use"
        self.name = "registrar_recomendacao"
        self.input = entrada


class RespostaFalsa:
    def __init__(self, entrada: dict) -> None:
        self.content = [BlocoFerramenta(entrada)]
        self.usage = SimpleNamespace(input_tokens=5, output_tokens=7)


class ClienteFalso:
    def __init__(self) -> None:
        self.chamadas: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return RespostaFalsa(
            {
                "recomendar": True,
                "nota": 9,
                "resumo_oportunidade": "Boa compra de notebooks.",
                "riscos": "Prazo curto.",
                "proximos_passos": "Ler TR e montar proposta.",
            }
        )


def test_montar_aceita_alias_de_proximos_passos() -> None:
    resposta = RespostaFalsa({})
    resultado = _montar_recomendacao(
        {
            "recomendar": False,
            "nota": 3,
            "resumo_oportunidade": "Fora do perfil.",
            "riscos": "Objeto residual.",
            "proximosPassos": "Ignorar e seguir.",
        },
        resposta,
    )
    assert resultado.proximos_passos == "Ignorar e seguir."
    assert resultado.recomendar is False


def test_recomendar_usa_tool_use() -> None:
    cliente = ClienteFalso()
    resultado = recomendar_licitacao(
        {
            "objeto": "notebooks",
            "itens_interesse": [{"numeroItem": 1, "descricao": "Notebook"}],
            "texto_edital": "Edital de pregão",
        },
        perfil="Vendo hardware",
        cliente=cliente,
    )
    assert resultado.recomendar is True
    assert resultado.nota == 9
    assert cliente.chamadas[0]["tool_choice"]["name"] == "registrar_recomendacao"


def test_recomendar_licitacoes_cache(tmp_path: Path) -> None:
    itens = [
        {
            "numero_controle_pncp": "1/2026",
            "objeto": "notebooks",
            "itens_interesse": [{"numeroItem": 1, "descricao": "Notebook", "valorTotal": 1}],
            "texto_edital": "texto",
        }
    ]
    cliente = ClienteFalso()
    cache = tmp_path / "rec.json"

    c1 = recomendar_licitacoes(
        itens,
        criterios={"perfil_usuario": "TI"},
        cliente=cliente,
        caminho_cache=cache,
    )
    assert c1.chamadas == 1
    assert itens[0]["nota_recomendacao"] == 9

    c2 = recomendar_licitacoes(
        itens,
        criterios={"perfil_usuario": "TI"},
        cliente=cliente,
        caminho_cache=cache,
    )
    assert c2.chamadas == 0
    assert c2.acertos_cache == 1
