"""Busca unificada de mods: Modrinth API + DuckDuckGo.

Este módulo é a ponte entre a intenção em linguagem natural do usuário
("automação para fabric 1.20.1") e os slugs exatos que o solver
determinístico precisa para resolver dependências.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .ddg import search_duckduckgo
from .metadata import ModrinthClient
from .models import SearchResult

# Palavras que não devem pesar na pontuação de relevância
_STOPWORDS = {
    "a", "o", "os", "as", "um", "ua", "uns", "umas",
    "the", "a", "an", "and", "or", "for", "with", "to", "in", "on",
    "mod", "mods", "minecraft", "fabric", "forge", "quilt", "neoforge",
    "pack", "modpack",
}


def _query_words(query: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", query) if w.lower() not in _STOPWORDS]


def _score(result: SearchResult, words: List[str]) -> float:
    """Pontua relevância simples: palavras da query aparecendo no título/descrição."""
    text = f"{result.title} {result.description}".lower()
    if not words:
        return 0.0
    matches = sum(1 for w in words if w in text)
    base = matches / len(words)
    # Resultados da API da Modrinth têm dados estruturados; priorize levemente
    source_bonus = 0.1 if result.source == "modrinth" else 0.0
    # Downloads indicam popularidade (confiança)
    popularity_bonus = min(result.downloads / 1_000_000, 0.2)
    return base + source_bonus + popularity_bonus


def unified_search(
    query: str,
    client: ModrinthClient,
    limit: int = 10,
    game_version: Optional[str] = None,
    loader: Optional[str] = None,
) -> List[SearchResult]:
    """Busca mods na Modrinth (API) e DuckDuckGo, mescla e deduplica por slug.

    Ordem de prioridade:
      1. Resultados da API da Modrinth (dados estruturados, confiáveis)
      2. DuckDuckGo (descobrir mods que a API não indexou bem por filtro)

    Se uma fonte falhar (rede, rate-limit), os resultados da outra ainda são
    retornados — a busca nunca retorna vazio por causa de um único provedor.
    """
    words = _query_words(query)

    modrinth_results: List[SearchResult] = []
    try:
        modrinth_results = client.search_projects(
            query, limit=limit, game_version=game_version, loader=loader
        )
    except Exception:
        # Falha na Modrinth: seguimos com apenas DuckDuckGo
        modrinth_results = []

    ddg_results: List[SearchResult] = []
    try:
        ddg_results = search_duckduckgo(query, limit=limit)
    except Exception:
        # Falha no DDG: seguimos com apenas Modrinth
        ddg_results = []

    # Mescla deduplicando por slug. Modrinth vence em caso de colisão.
    merged: Dict[str, SearchResult] = {}
    for r in modrinth_results:
        key = r.slug or f"modrinth:{id(r)}"
        merged[key] = r

    for r in ddg_results:
        key = r.slug if r.slug else f"ddg:{r.title}"
        if key not in merged:
            merged[key] = r

    # Pontua e ordena
    ordered = sorted(
        merged.values(),
        key=lambda r: _score(r, words),
        reverse=True,
    )
    return ordered[:limit]


def auto_select(results: List[SearchResult]) -> Optional[SearchResult]:
    """Escolhe o melhor resultado para fluxo agentico sem intervenção do usuário."""
    return results[0] if results else None
