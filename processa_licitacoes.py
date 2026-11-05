import logging
from typing import Any

logger = logging.getLogger(__name__)


def transformar_licitacao(licitacao: dict) -> dict:

    try:
        cnpj = licitacao["orgaoEntidade"]["cnpj"]
        ano = licitacao["anoCompra"]
        sequencial = licitacao["sequencialCompra"]

        numero_controle_pncp = licitacao["numeroControlePNCP"]
        orgao = licitacao["unidadeOrgao"]["nomeUnidade"]
        uf = licitacao["unidadeOrgao"]["ufSigla"]
        # funciona como protótipo. Ler README.md - Melhorias futuras
        municipio = licitacao["unidadeOrgao"]["municipioNome"]
        modalidade = licitacao["modalidadeNome"]
        objeto = licitacao["objetoCompra"]
        valor_estimado = licitacao["valorTotalEstimado"]
        data_publicacao_pncp = licitacao["dataPublicacaoPncp"]

        link_pncp = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"

        return {
            "numero_controle_pncp": numero_controle_pncp,
            "orgao": orgao,
            "uf": uf,
            "municipio": municipio,
            "modalidade": modalidade,
            "objeto": objeto,
            "valor_estimado": valor_estimado,
            "data_publicacao_pncp": data_publicacao_pncp,
            "link_pncp": link_pncp,
        }

    except (KeyError, TypeError) as e:
        numero = licitacao.get("numeroControlePNCP", "sem número")
        raise ValueError(f"Registro inválido ({numero}): {e!r}") from e


def filtrar_licitacoes(licitacoes: list[dict], palavras_chave: list[str]) -> list[dict]:

    filtradas = []

    for licitacao in licitacoes:
        objeto_compra = licitacao.get("objetoCompra") or ""

        objeto_compra_texto = objeto_compra.lower()

        if any(palavra.lower() in objeto_compra_texto for palavra in palavras_chave):
            filtradas.append(licitacao)

    return filtradas


def validar_licitacoes(
    licitacoes: list[dict[str, Any]],
) -> tuple[list[dict], list[dict]]:

    validadas = []
    erros = []

    for licitacao in licitacoes:
        try:
            validadas.append(transformar_licitacao(licitacao))
        except ValueError as erro:
            logger.warning("Licitação %s descartada", erro)
            erros.append(
                {
                    "numero_controle_pncp": licitacao.get("numeroControlePNCP"),
                    "motivo_erro": str(erro),
                }
            )

    return validadas, erros


def filtrar_e_validar(
    licitacoes: list[dict[str, Any]],
    palavras_chave: list[str],
) -> tuple[list[dict], list[dict]]:
    filtradas = filtrar_licitacoes(licitacoes, palavras_chave)
    return validar_licitacoes(filtradas)
