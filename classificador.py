"""Classifica o objeto de uma licitação com a API Anthropic (tool use)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

MODELO_PADRAO = "claude-haiku-4-5"
FERRAMENTA = "registrar_classificacao"
PROMPT_SISTEMA = (
    "Você analisa o objeto de uma contratação pública brasileira. "
    "Classifique se a compra parece oportunidade para quem vende "
    "computadores, notebooks, periféricos ou TI em geral. "
    "relevancia: inteiro de 0 a 10 (10 = muito alinhado a TI/hardware). "
    "categoria: uma palavra curta em português (ex.: hardware, software, "
    "mobiliario, servicos, outro). "
    "resumo: uma frase objetiva. "
    "justificativa: uma frase dizendo por que a relevância foi essa. "
    "Use a ferramenta registrar_classificacao."
)
ESQUEMA_FERRAMENTA = {
    "name": FERRAMENTA,
    "description": "Registra a classificação da licitação.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevancia": {
                "type": "integer",
                "description": "Nota de 0 a 10 para alinhamento com TI/hardware",
            },
            "categoria": {"type": "string"},
            "resumo": {"type": "string"},
            "justificativa": {"type": "string"},
        },
        "required": ["relevancia", "categoria", "resumo", "justificativa"],
    },
}


class ErroClassificacao(Exception):
    """A API ou a resposta do modelo não produziu uma classificação válida."""


@dataclass
class Classificacao:
    relevancia: int
    categoria: str
    resumo: str
    justificativa: str
    input_tokens: int = 0
    output_tokens: int = 0
    do_cache: bool = False


@dataclass
class ContagemTokens:
    input_tokens: int = 0
    output_tokens: int = 0
    chamadas: int = 0
    acertos_cache: int = 0

    def somar(self, classificacao: Classificacao) -> None:
        if classificacao.do_cache:
            self.acertos_cache += 1
            return
        self.input_tokens += classificacao.input_tokens
        self.output_tokens += classificacao.output_tokens
        self.chamadas += 1


class ClienteMensagens(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


def criar_cliente_anthropic() -> Any:
    from anthropic import Anthropic

    return Anthropic()


def _extrair_entrada_ferramenta(resposta: Any) -> dict[str, Any]:
    for bloco in getattr(resposta, "content", []) or []:
        tipo = getattr(bloco, "type", None)
        nome = getattr(bloco, "name", None)
        if tipo == "tool_use" and nome == FERRAMENTA:
            entrada = getattr(bloco, "input", None)
            if isinstance(entrada, dict):
                return entrada
    raise ErroClassificacao("A resposta do modelo não usou a ferramenta esperada")


def _montar_classificacao(entrada: dict[str, Any], resposta: Any) -> Classificacao:
    try:
        relevancia = int(entrada["relevancia"])
        categoria = str(entrada["categoria"]).strip()
        resumo = str(entrada["resumo"]).strip()
        justificativa = str(entrada["justificativa"]).strip()
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroClassificacao(f"Campos inválidos na classificação: {erro}") from erro
    if not 0 <= relevancia <= 10:
        raise ErroClassificacao(f"relevancia fora de 0..10: {relevancia}")
    if not categoria or not resumo or not justificativa:
        raise ErroClassificacao("categoria, resumo e justificativa não podem ser vazios")
    uso = getattr(resposta, "usage", None)
    return Classificacao(
        relevancia=relevancia,
        categoria=categoria,
        resumo=resumo,
        justificativa=justificativa,
        input_tokens=int(getattr(uso, "input_tokens", 0) or 0),
        output_tokens=int(getattr(uso, "output_tokens", 0) or 0),
    )


def classificar_objeto(
    objeto: str,
    *,
    cliente: Any | None = None,
    modelo: str | None = None,
) -> Classificacao:
    if not (objeto or "").strip():
        raise ErroClassificacao("Objeto vazio não pode ser classificado")
    if cliente is None:
        cliente = criar_cliente_anthropic()
    mensagens = getattr(cliente, "messages", None)
    criar = mensagens.create if mensagens is not None else cliente.create
    nome_modelo = modelo or os.getenv("ANTHROPIC_MODEL", MODELO_PADRAO)
    try:
        resposta = criar(
            model=nome_modelo,
            max_tokens=300,
            system=PROMPT_SISTEMA,
            tools=[ESQUEMA_FERRAMENTA],
            tool_choice={"type": "tool", "name": FERRAMENTA},
            messages=[{"role": "user", "content": objeto.strip()}],
        )
    except Exception as erro:
        raise ErroClassificacao(f"Falha ao chamar a Anthropic: {erro}") from erro
    return _montar_classificacao(_extrair_entrada_ferramenta(resposta), resposta)


def carregar_cache(caminho: str | Path) -> dict[str, dict[str, Any]]:
    arquivo = Path(caminho)
    if not arquivo.exists():
        return {}
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        logger.warning("Cache de classificação ilegível (%s); começa vazio", erro)
        return {}
    if not isinstance(dados, dict):
        return {}
    return {str(chave): valor for chave, valor in dados.items() if isinstance(valor, dict)}


def gravar_cache(caminho: str | Path, cache: dict[str, dict[str, Any]]) -> None:
    arquivo = Path(caminho)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def classificar_licitacoes(
    licitacoes: list[dict[str, Any]],
    *,
    cliente: Any | None = None,
    modelo: str | None = None,
    caminho_cache: str | Path | None = None,
) -> ContagemTokens:
    """Acrescenta relevancia, categoria, resumo_ia e justificativa em cada item."""
    contagem = ContagemTokens()
    cache: dict[str, dict[str, Any]] = {}
    if caminho_cache is not None:
        cache = carregar_cache(caminho_cache)

    for item in licitacoes:
        chave = str(item.get("numero_controle_pncp") or "")
        if chave and chave in cache:
            salvo = cache[chave]
            item["relevancia"] = salvo["relevancia"]
            item["categoria"] = salvo["categoria"]
            item["resumo_ia"] = salvo["resumo"]
            item["justificativa"] = salvo["justificativa"]
            contagem.somar(
                Classificacao(
                    relevancia=salvo["relevancia"],
                    categoria=salvo["categoria"],
                    resumo=salvo["resumo"],
                    justificativa=salvo["justificativa"],
                    do_cache=True,
                )
            )
            continue

        resultado = classificar_objeto(
            str(item.get("objeto") or ""),
            cliente=cliente,
            modelo=modelo,
        )
        item["relevancia"] = resultado.relevancia
        item["categoria"] = resultado.categoria
        item["resumo_ia"] = resultado.resumo
        item["justificativa"] = resultado.justificativa
        contagem.somar(resultado)
        if chave:
            cache[chave] = {
                "relevancia": resultado.relevancia,
                "categoria": resultado.categoria,
                "resumo": resultado.resumo,
                "justificativa": resultado.justificativa,
            }

    if caminho_cache is not None:
        gravar_cache(caminho_cache, cache)

    logger.info(
        "Classificação: %d chamadas, %d do cache, tokens in=%d out=%d",
        contagem.chamadas,
        contagem.acertos_cache,
        contagem.input_tokens,
        contagem.output_tokens,
    )
    return contagem


def classificacao_para_dict(classificacao: Classificacao) -> dict[str, Any]:
    return asdict(classificacao)
