"""Lista, baixa e extrai texto de documentos do PNCP (11.8)."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf.errors import PyPdfError

from criterios import carregar_criterios
from pncp_detalhe import ErroDetalhePNCP, baixar_arquivo, listar_arquivos

logger = logging.getLogger(__name__)

CACHE_DOCS = Path("local/docs")
TIPO_EDITAL = 2


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").lower()).strip()


def _eh_tr(titulo: str | None, titulos_tr: list[str]) -> bool:
    nome = _normalizar(titulo or "")
    return any(padrao.lower() in nome for padrao in titulos_tr)


def selecionar_arquivos(
    arquivos: list[dict[str, Any]],
    *,
    edital_id: int = TIPO_EDITAL,
    titulos_tr: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Prioriza Edital e, se houver, Termo de Referência / especificação."""
    titulos = titulos_tr or []
    escolhidos: list[dict[str, Any]] = []
    edital = next(
        (
            arq
            for arq in arquivos
            if arq.get("tipoDocumentoId") == edital_id and arq.get("url")
        ),
        None,
    )
    if edital is not None:
        escolhidos.append(edital)
    for arq in arquivos:
        if arq is edital:
            continue
        if _eh_tr(arq.get("titulo") or arq.get("tipoDocumentoNome"), titulos):
            if arq.get("url"):
                escolhidos.append(arq)
            break
    return escolhidos


def extrair_texto_pdf(conteudo: bytes) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(BytesIO(conteudo))
    partes: list[str] = []
    for pagina in leitor.pages:
        texto = pagina.extract_text() or ""
        if texto.strip():
            partes.append(texto)
    return "\n".join(partes).strip()


def _caminho_cache(
    base: Path, cnpj: str, ano: Any, sequencial: Any, nome: str
) -> Path:
    pasta = base / f"{cnpj}_{ano}_{sequencial}"
    pasta.mkdir(parents=True, exist_ok=True)
    seguro = re.sub(r"[^\w.\-]+", "_", nome)[:80] or "documento.pdf"
    if not seguro.lower().endswith(".pdf"):
        seguro = f"{seguro}.pdf"
    return pasta / seguro


def enriquecer_com_documentos(
    licitacoes: list[dict[str, Any]],
    *,
    criterios: dict[str, Any] | None = None,
    session: Any = None,
    cache_dir: Path | None = CACHE_DOCS,
    listar: Callable[..., list[dict[str, Any]]] | None = None,
    baixar: Callable[..., bytes] | None = None,
    extrair: Callable[[bytes], str] | None = None,
) -> list[dict[str, Any]]:
    """Baixa Edital/TR, cacheia em disco e grava texto_edital no registro."""
    cfg = criterios if criterios is not None else carregar_criterios()
    docs_cfg = (cfg.get("docs") or {}).get("tipos_prioritarios") or {}
    edital_id = int(docs_cfg.get("edital_id") or TIPO_EDITAL)
    titulos_tr = list(docs_cfg.get("titulos_tr") or [])
    consultar = listar or listar_arquivos
    download = baixar or baixar_arquivo
    extrair_pdf = extrair or extrair_texto_pdf
    base_cache = Path(cache_dir) if cache_dir is not None else None

    for licitacao in licitacoes:
        cnpj = licitacao.get("orgao_cnpj")
        ano = licitacao.get("ano_compra")
        sequencial = licitacao.get("sequencial_compra")
        if not cnpj or ano is None or sequencial is None:
            licitacao["texto_edital"] = ""
            licitacao["motivo_extracao"] = "chaves PNCP ausentes para documentos"
            continue

        kwargs: dict[str, Any] = {}
        if session is not None:
            kwargs["session"] = session

        try:
            arquivos = consultar(str(cnpj), ano, sequencial, **kwargs)
        except ErroDetalhePNCP as erro:
            logger.warning(
                "Arquivos não listados para %s: %s",
                licitacao.get("numero_controle_pncp"),
                erro,
            )
            licitacao["texto_edital"] = ""
            licitacao["motivo_extracao"] = str(erro)
            continue

        selecionados = selecionar_arquivos(
            arquivos, edital_id=edital_id, titulos_tr=titulos_tr
        )
        if not selecionados:
            licitacao["texto_edital"] = ""
            licitacao["motivo_extracao"] = "nenhum Edital/TR encontrado"
            continue

        textos: list[str] = []
        motivo: str | None = None
        for arq in selecionados:
            url = arq.get("url") or ""
            titulo = str(arq.get("titulo") or "documento")
            try:
                if base_cache is not None:
                    destino = _caminho_cache(
                        base_cache, str(cnpj), ano, sequencial, titulo
                    )
                    if destino.exists():
                        conteudo = destino.read_bytes()
                    else:
                        conteudo = download(url, **kwargs)
                        destino.write_bytes(conteudo)
                else:
                    conteudo = download(url, **kwargs)
                texto = extrair_pdf(conteudo)
                if texto:
                    textos.append(texto)
                else:
                    motivo = "PDF sem texto extraível (possível imagem/OCR)"
            except ErroDetalhePNCP as erro:
                logger.warning(
                    "Falha ao baixar %s de %s: %s",
                    titulo,
                    licitacao.get("numero_controle_pncp"),
                    erro,
                )
                motivo = str(erro)
            except (OSError, ValueError, TypeError, KeyError, PyPdfError) as erro:
                logger.warning(
                    "Falha ao extrair %s de %s: %s",
                    titulo,
                    licitacao.get("numero_controle_pncp"),
                    erro,
                )
                motivo = str(erro)

        licitacao["texto_edital"] = "\n\n".join(textos).strip()
        if licitacao["texto_edital"]:
            licitacao.pop("motivo_extracao", None)
        elif motivo:
            licitacao["motivo_extracao"] = motivo
        else:
            licitacao["motivo_extracao"] = "sem texto extraído"

    return licitacoes
