from pathlib import Path
from types import SimpleNamespace

import pytest

from classificador import (
    ErroClassificacao,
    carregar_cache,
    classificar_licitacoes,
    classificar_objeto,
    gravar_cache,
)


class BlocoFerramenta:
    def __init__(self, entrada: dict) -> None:
        self.type = "tool_use"
        self.name = "registrar_classificacao"
        self.input = entrada


class RespostaFalsa:
    def __init__(self, entrada: dict, input_tokens: int = 11, output_tokens: int = 22) -> None:
        self.content = [BlocoFerramenta(entrada)]
        self.usage = SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


class ClienteFalso:
    def __init__(self, entrada: dict | None = None) -> None:
        self.entrada = entrada or {
            "relevancia": 8,
            "categoria": "hardware",
            "resumo": "Compra de computadores.",
            "justificativa": "Objeto cita computadores.",
        }
        self.chamadas: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return RespostaFalsa(self.entrada)


def test_classificar_objeto_usa_tool_use() -> None:
    cliente = ClienteFalso()

    resultado = classificar_objeto("Aquisição de notebooks", cliente=cliente)

    assert resultado.relevancia == 8
    assert resultado.categoria == "hardware"
    assert resultado.resumo == "Compra de computadores."
    assert resultado.input_tokens == 11
    assert resultado.output_tokens == 22
    assert cliente.chamadas[0]["tool_choice"]["name"] == "registrar_classificacao"
    assert "registrar_classificacao" in {
        ferramenta["name"] for ferramenta in cliente.chamadas[0]["tools"]
    }


def test_objeto_vazio_falha() -> None:
    with pytest.raises(ErroClassificacao, match="vazio"):
        classificar_objeto("  ", cliente=ClienteFalso())


def test_resposta_sem_ferramenta_falha() -> None:
    class ClienteSemFerramenta:
        messages = None

        def create(self, **kwargs):
            return SimpleNamespace(content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=1))

        def __init__(self) -> None:
            self.messages = self

    with pytest.raises(ErroClassificacao, match="ferramenta"):
        classificar_objeto("cadeiras", cliente=ClienteSemFerramenta())


def test_classificar_licitacoes_preenche_campos_e_soma_tokens() -> None:
    itens = [
        {
            "numero_controle_pncp": "1/2026",
            "objeto": "Aquisição de computadores",
        }
    ]
    cliente = ClienteFalso()

    contagem = classificar_licitacoes(itens, cliente=cliente)

    assert itens[0]["relevancia"] == 8
    assert itens[0]["categoria"] == "hardware"
    assert itens[0]["resumo_ia"] == "Compra de computadores."
    assert itens[0]["justificativa"] == "Objeto cita computadores."
    assert contagem.chamadas == 1
    assert contagem.input_tokens == 11
    assert contagem.output_tokens == 22
    assert contagem.acertos_cache == 0


def test_cache_evita_segunda_chamada(tmp_path: Path) -> None:
    caminho = tmp_path / "cache.json"
    itens = [
        {"numero_controle_pncp": "1/2026", "objeto": "Notebooks"},
        {"numero_controle_pncp": "1/2026", "objeto": "Notebooks de novo"},
    ]
    cliente = ClienteFalso()

    classificar_licitacoes(itens[:1], cliente=cliente, caminho_cache=caminho)
    contagem = classificar_licitacoes(itens[1:], cliente=cliente, caminho_cache=caminho)

    assert len(cliente.chamadas) == 1
    assert contagem.chamadas == 0
    assert contagem.acertos_cache == 1
    assert itens[1]["relevancia"] == 8
    assert carregar_cache(caminho)["1/2026"]["categoria"] == "hardware"


def test_gravar_e_carregar_cache(tmp_path: Path) -> None:
    caminho = tmp_path / "sub" / "cache.json"
    gravar_cache(caminho, {"a": {"relevancia": 1, "categoria": "x", "resumo": "r", "justificativa": "j"}})

    assert carregar_cache(caminho)["a"]["relevancia"] == 1
