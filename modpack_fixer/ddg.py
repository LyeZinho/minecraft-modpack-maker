"""Busca na DuckDuckGo HTML (sem chave de API).

Raspa resultados da página html.duckduckgo.com para encontrar páginas da
Modrinth quando o usuário não conhece o slug exato do mod.

É intencionalmente leve: depende apenas da biblioteca padrão. O DDG pode
bloquear requisições excessivas; use com moderação e cache local.
"""

from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from typing import List, Optional

from .models import SearchResult

DDG_URL = "https://html.duckduckgo.com/html/"

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Link de resultado do DDG: <a rel="nofollow" class="result__a" href="...">Título</a>
_RESULT_RE = re.compile(
    r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)


def _clean_title(raw: str) -> str:
    text = re.sub(r"<.*?>", "", raw, flags=re.DOTALL)
    return html.unescape(text).strip()


def _decode_ddg_redirect(url: str) -> str:
    """Decodifica links de redirecionamento do DDG (uddg=...) para a URL real."""
    if "duckduckgo.com/l/" in url and "uddg=" in url:
        try:
            qs = urllib.parse.urlparse(url).query
            params = urllib.parse.parse_qs(qs)
            if "uddg" in params:
                return params["uddg"][0]
        except Exception:
            pass
    return url


def _extract_modrinth_slug(url: str) -> Optional[str]:
    """Extrai o slug do mod a partir de uma URL da Modrinth."""
    if "modrinth.com" not in url:
        return None
    # https://modrinth.com/mod/jei  ou  https://modrinth.com/mod/jei/versions
    m = re.search(r"modrinth\.com/mod/([^/?#]+)", url)
    if m:
        return m.group(1)
    return None


def search_duckduckgo(query: str, limit: int = 10) -> List[SearchResult]:
    """Busca mods na DuckDuckGo e retorna resultados com slug da Modrinth quando possível."""
    params = urllib.parse.urlencode({"q": query})
    url = f"{DDG_URL}?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception:
        # Falha na rede/DDG bloqueado: retorna vazio, não quebra o fluxo
        return []

    results: List[SearchResult] = []
    for match in _RESULT_RE.finditer(body):
        raw_url = match.group(1)
        real_url = _decode_ddg_redirect(raw_url)
        title = _clean_title(match.group(2))
        if not title:
            continue

        slug = _extract_modrinth_slug(real_url)

        results.append(
            SearchResult(
                source="duckduckgo",
                slug=slug or "",
                title=title,
                description="",
                project_type="mod",
                downloads=0,
                follows=0,
                game_versions=[],
                loaders=[],
                url=real_url,
            )
        )

        if len(results) >= limit:
            break

    return results
