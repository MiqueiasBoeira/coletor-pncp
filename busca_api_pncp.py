import logging
import time
from collections.abc import Callable
from typing import Any

import requests

logger = logging.getLogger(__name__)

URL_PUBLICACAO = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"


class ErroConsultaPNCP(Exception):
    """A consulta ao PNCP não fechou todas as páginas."""


def buscar_registros_pncp(
    data_inicial: str,
    data_final: str,
    codigo_modalidade_licitacao: int,
    uf: str,
    tamanho_da_pagina: int,
    *,
    session: Any = None,
    pausa: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    todos_os_registros: list[dict[str, Any]] = []
    pagina_atual = 1
    total_paginas = 1
    session_propria = session is None
    if session is None:
        session = requests.Session()

    try:
        while pagina_atual <= total_paginas:
            parametros = {
                "dataInicial": data_inicial,
                "dataFinal": data_final,
                "codigoModalidadeContratacao": codigo_modalidade_licitacao,
                "pagina": pagina_atual,
                "tamanhoPagina": tamanho_da_pagina,
                "uf": uf,
            }

            try:
                response = session.get(URL_PUBLICACAO, params=parametros, timeout=30)
                response.raise_for_status()
                dados_resposta = response.json()
                total_paginas = dados_resposta["totalPaginas"]
                todos_os_registros.extend(dados_resposta.get("data") or [])
                pagina_atual += 1
                if pagina_atual <= total_paginas:
                    pausa(1)
            except (requests.RequestException, KeyError, TypeError) as erro:
                logger.error("Erro na página %s: %s", pagina_atual, erro)
                raise ErroConsultaPNCP(
                    f"Falha ao consultar a página {pagina_atual} do PNCP"
                ) from erro
    finally:
        if session_propria:
            session.close()

    return todos_os_registros
