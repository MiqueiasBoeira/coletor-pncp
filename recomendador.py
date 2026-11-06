"""Recomendação com Anthropic tool-use só nos sobreviventes do funil."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from classificador import (
    ContagemTokens,
    carregar_cache,
    criar_cliente_anthropic,
    gravar_cache,
)
from criterios import carregar_criterios

logger = logging.getLogger(__name__)

MODELO_PADRAO = "claude-haiku-4-5"
FERRAMENTA = "registrar_recomendacao"
CACHE_RECOMENDACAO = Path("local/cache_recomendacao.json")
LIMITE_TEXTO_EDITAL = 6000
LIMITE_ITENS = 15

ESQUEMA_FERRAMENTA = {
    "name": FERRAMENTA,
    "description": "Registra a recomendação da oportunidade.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "recomendar": {
                "type": "boolean",
                "description": "True se vale a pena participar",
            },
            "nota": {
                "type": "integer",
                "description": "Nota de 0 a 10",
            },
            "resumo_oportunidade": {
                "type": "string",
                "description": "Uma frase objetiva sobre a oportunidade",
            },
            "riscos": {
                "type": "string",
                "description": "Uma frase com os principais riscos",
            },
            "proximos_passos": {
                "type": "string",
                "description": "Uma frase com a próxima ação recomendada",
            },
        },
        "required": [
            "recomendar",
            "nota",
            "resumo_oportunidade",
            "riscos",
            "proximos_passos",
        ],
    },
}

_ALIASES_CAMPO: dict[str, tuple[str, ...]] = {
    "recomendar": ("recomendar", "recommend"),
    "nota": ("nota", "score", "relevancia"),
    "resumo_oportunidade": (
        "resumo_oportunidade",
        "resumo",
        "resumoOportunidade",
    ),
    "riscos": ("riscos", "risco"),
    "proximos_passos": (
        "proximos_passos",
        "proximosPassos",
        "próximos_passos",
        "proximos passos",
        "next_steps",
    ),
}


class ErroRecomendacao(Exception):
    """A API ou a resposta do modelo não produziu uma recomendação válida."""


@dataclass
class Recomendacao:
    recomendar: bool
    nota: int
    resumo_oportunidade: str
    riscos: str
    proximos_passos: str
    input_tokens: int = 0
    output_tokens: int = 0
    do_cache: bool = False


def _prompt_sistema(perfil: str) -> str:
    return (
        "Você avalia se uma contratação pública brasileira é boa oportunidade "
        "para o perfil abaixo. Use apenas os dados fornecidos. "
        "recomendar: true só se fizer sentido comercialmente. "
        "nota: inteiro 0–10. "
        "resumo_oportunidade, riscos e proximos_passos: frases objetivas em português. "
        "Use a ferramenta registrar_recomendacao.\n\n"
        f"Perfil do usuário:\n{perfil.strip()}"
    )


def _montar_mensagem(licitacao: dict[str, Any]) -> str:
    itens = licitacao.get("itens_interesse") or []
    linhas_itens = []
    for item in itens[:LIMITE_ITENS]:
        linhas_itens.append(
            f"- item {item.get('numeroItem')}: {item.get('descricao')} "
            f"(qtd={item.get('quantidade')}, total={item.get('valorTotal')})"
        )
    texto = (licitacao.get("texto_edital") or "")[:LIMITE_TEXTO_EDITAL]
    return (
        f"Número: {licitacao.get('numero_controle_pncp')}\n"
        f"Órgão: {licitacao.get('orgao')}\n"
        f"Objeto: {licitacao.get('objeto')}\n"
        f"Valor estimado: {licitacao.get('valor_estimado')}\n"
        f"Valor itens interesse: {licitacao.get('valor_itens_interesse')}\n"
        f"Itens de interesse:\n"
        + ("\n".join(linhas_itens) if linhas_itens else "(nenhum)")
        + f"\n\nTrecho do edital:\n{texto or '(sem texto)'}"
    )


def _extrair_entrada_ferramenta(resposta: Any) -> dict[str, Any]:
    for bloco in getattr(resposta, "content", []) or []:
        tipo = getattr(bloco, "type", None)
        nome = getattr(bloco, "name", None)
        if tipo == "tool_use" and nome == FERRAMENTA:
            entrada = getattr(bloco, "input", None)
            if isinstance(entrada, dict):
                return entrada
    raise ErroRecomendacao("A resposta do modelo não usou a ferramenta esperada")


def _campo(entrada: dict[str, Any], nome: str) -> Any:
    for alias in _ALIASES_CAMPO.get(nome, (nome,)):
        if alias in entrada:
            return entrada[alias]
    raise KeyError(nome)


def _montar_recomendacao(entrada: dict[str, Any], resposta: Any) -> Recomendacao:
    try:
        recomendar = bool(_campo(entrada, "recomendar"))
        nota = int(_campo(entrada, "nota"))
        resumo = str(_campo(entrada, "resumo_oportunidade")).strip()
        riscos = str(_campo(entrada, "riscos")).strip()
        passos = str(_campo(entrada, "proximos_passos")).strip()
    except (KeyError, TypeError, ValueError) as erro:
        logger.warning(
            "Entrada inválida da ferramenta (chaves=%s): %s",
            sorted(entrada.keys()),
            erro,
        )
        raise ErroRecomendacao(
            f"Campos inválidos na recomendação: {erro} (chaves={sorted(entrada.keys())})"
        ) from erro
    if not 0 <= nota <= 10:
        raise ErroRecomendacao(f"nota fora de 0..10: {nota}")
    if not resumo or not riscos or not passos:
        raise ErroRecomendacao("resumo, riscos e próximos passos não podem ser vazios")
    uso = getattr(resposta, "usage", None)
    return Recomendacao(
        recomendar=recomendar,
        nota=nota,
        resumo_oportunidade=resumo,
        riscos=riscos,
        proximos_passos=passos,
        input_tokens=int(getattr(uso, "input_tokens", 0) or 0),
        output_tokens=int(getattr(uso, "output_tokens", 0) or 0),
    )


def recomendar_licitacao(
    licitacao: dict[str, Any],
    *,
    perfil: str,
    cliente: Any | None = None,
    modelo: str | None = None,
) -> Recomendacao:
    if cliente is None:
        cliente = criar_cliente_anthropic()
    mensagens = getattr(cliente, "messages", None)
    criar = mensagens.create if mensagens is not None else cliente.create
    nome_modelo = modelo or os.getenv("ANTHROPIC_MODEL", MODELO_PADRAO)
    try:
        resposta = criar(
            model=nome_modelo,
            max_tokens=1024,
            system=_prompt_sistema(perfil),
            tools=[ESQUEMA_FERRAMENTA],
            tool_choice={"type": "tool", "name": FERRAMENTA},
            messages=[{"role": "user", "content": _montar_mensagem(licitacao)}],
        )
    except Exception as erro:
        raise ErroRecomendacao(f"Falha ao chamar a Anthropic: {erro}") from erro
    return _montar_recomendacao(_extrair_entrada_ferramenta(resposta), resposta)


def recomendar_licitacoes(
    licitacoes: list[dict[str, Any]],
    *,
    criterios: dict[str, Any] | None = None,
    cliente: Any | None = None,
    modelo: str | None = None,
    caminho_cache: str | Path | None = CACHE_RECOMENDACAO,
) -> ContagemTokens:
    """Acrescenta campos de recomendação; sem dados úteis, não chama a LLM."""
    cfg = criterios if criterios is not None else carregar_criterios()
    perfil = str(cfg.get("perfil_usuario") or "").strip() or "Fornecedor de TI."
    contagem = ContagemTokens()
    cache: dict[str, dict[str, Any]] = {}
    if caminho_cache is not None:
        cache = carregar_cache(caminho_cache)

    for item in licitacoes:
        chave = str(item.get("numero_controle_pncp") or "")
        texto = (item.get("texto_edital") or "").strip()
        if not texto and not (item.get("itens_interesse") or []):
            item["recomendar"] = False
            item["nota_recomendacao"] = 0
            item["resumo_oportunidade"] = ""
            item["riscos"] = "Sem texto de edital nem itens para avaliar"
            item["proximos_passos"] = "Obter edital/TR e reavaliar"
            continue

        if chave and chave in cache:
            salvo = cache[chave]
            item["recomendar"] = bool(salvo["recomendar"])
            item["nota_recomendacao"] = int(salvo["nota"])
            item["resumo_oportunidade"] = salvo["resumo_oportunidade"]
            item["riscos"] = salvo["riscos"]
            item["proximos_passos"] = salvo["proximos_passos"]
            contagem.acertos_cache += 1
            continue

        resultado = recomendar_licitacao(
            item, perfil=perfil, cliente=cliente, modelo=modelo
        )
        item["recomendar"] = resultado.recomendar
        item["nota_recomendacao"] = resultado.nota
        item["resumo_oportunidade"] = resultado.resumo_oportunidade
        item["riscos"] = resultado.riscos
        item["proximos_passos"] = resultado.proximos_passos
        contagem.input_tokens += resultado.input_tokens
        contagem.output_tokens += resultado.output_tokens
        contagem.chamadas += 1
        if chave:
            cache[chave] = {
                "recomendar": resultado.recomendar,
                "nota": resultado.nota,
                "resumo_oportunidade": resultado.resumo_oportunidade,
                "riscos": resultado.riscos,
                "proximos_passos": resultado.proximos_passos,
            }

    if caminho_cache is not None:
        gravar_cache(caminho_cache, cache)

    logger.info(
        "Recomendação: %d chamadas, %d do cache, tokens in=%d out=%d",
        contagem.chamadas,
        contagem.acertos_cache,
        contagem.input_tokens,
        contagem.output_tokens,
    )
    return contagem
