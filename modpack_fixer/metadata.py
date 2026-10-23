"""Cliente da API pública da Modrinth (sem chave, sem cadastro).

Notas de projeto:
- A API da Modrinth é aberta e expõe dependency_type (required/optional/incompatible/embedded),
  game_versions, loaders e hashes SHA-512 dos arquivos.
- Nunca baixamos nem redistribuímos JARs próprios. O lockfile guarda apenas a URL oficial
  e o cabeçalho do launcher faz o download direto.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .models import DependencyType, ModVersion, SearchResult

MODRINTH_BASE = "https://api.modrinth.com/v2"


class ModrinthError(Exception):
    pass


class ModrinthClient:
    def __init__(
        self,
        timeout: int = 30,
        user_agent: str = "modpack-fixer/0.1.0",
        cache_ttl: int = 300,
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _get(self, path: str) -> Any:
        now = time.time()
        if path in self._cache:
            ts, value = self._cache[path]
            if now - ts < self.cache_ttl:
                return value

        url = f"{MODRINTH_BASE}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # type: ignore[name-defined]
            raise ModrinthError(f"HTTP {exc.code} ao acessar {url}") from exc
        except urllib.error.URLError as exc:  # type: ignore[name-defined]
            raise ModrinthError(f"Erro de rede ao acessar {url}: {exc}") from exc

        value = json.loads(body)
        self._cache[path] = (now, value)
        return value

    def get_project(self, slug: str) -> Dict[str, Any]:
        return self._get(f"/project/{slug}")

    def get_version(self, version_id: str) -> Dict[str, Any]:
        return self._get(f"/version/{version_id}")

    def list_versions(
        self,
        slug: str,
        game_version: Optional[str] = None,
        loader: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista versões de um projeto, filtradas por versão do jogo e loader.

        A API já retorna ordenada (mais recente primeiro na prática), o que
        mantém o solver determinístico.
        """
        params: List[str] = []
        if game_version:
            params.append(f"game_versions={game_version}")
        if loader:
            params.append(f"loaders={loader}")
        query = "&".join(params)
        path = f"/project/{slug}/version" + (f"?{query}" if query else "")
        return self._get(path)

    def search_projects(
        self,
        query: str,
        limit: int = 10,
        game_version: Optional[str] = None,
        loader: Optional[str] = None,
        project_type: str = "mod",
    ) -> List[SearchResult]:
        """Busca projetos na API pública da Modrinth (/search).

        Retorna metadados de nível de projeto (slug, título, downloads, etc.).
        Versões específicas ainda são resolvidas pelo solver via list_versions.
        """
        facets: List[List[str]] = [[f"project_type:{project_type}"]]
        if game_version:
            facets.append([f"game_versions:{game_version}"])
        if loader:
            facets.append([f"loaders:{loader}"])

        params: Dict[str, str] = {"query": query, "limit": str(limit), "offset": "0"}
        params["filter"] = json.dumps(facets)

        query_string = urllib.parse.urlencode(params)
        data = self._get(f"/search?{query_string}")

        results: List[SearchResult] = []
        for hit in data.get("hits", []):
            slug = hit.get("slug", "")
            results.append(
                SearchResult(
                    source="modrinth",
                    slug=slug,
                    title=hit.get("title", ""),
                    description=hit.get("description", ""),
                    project_type=hit.get("project_type", project_type),
                    downloads=hit.get("downloads", 0) or 0,
                    follows=hit.get("follows", 0) or 0,
                    game_versions=[],
                    loaders=[],
                    url=f"https://modrinth.com/mod/{slug}" if slug else "",
                )
            )
        return results

    def version_to_model(self, project_id: str, raw: Dict[str, Any]) -> ModVersion:
        files = []
        for f in raw.get("files", []):
            hashes = f.get("hashes", {}) or {}
            files.append(
                {
                    "path": f.get("filename", ""),
                    "url": f.get("url", ""),
                    "size": f.get("size", 0),
                    "hashes": {
                        "sha512": hashes.get("sha512", ""),
                        "sha1": hashes.get("sha1", ""),
                    },
                }
            )

        dependencies = []
        for d in raw.get("dependencies", []):
            dependencies.append(
                {
                    "project_id": d.get("project_id", ""),
                    "version": d.get("version", ""),
                    "dependency_type": d.get("dependency_type", DependencyType.REQUIRED),
                }
            )

        return ModVersion(
            id=raw["id"],
            project_id=project_id,
            name=raw.get("name", ""),
            version_string=raw.get("version_number", ""),
            game_versions=raw.get("game_versions", []),
            loaders=raw.get("loaders", []),
            files=files,
            dependencies=dependencies,
        )
