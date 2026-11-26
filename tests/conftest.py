"""Fixtures compartilhadas: um ModrinthClient falso, sem rede."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from modpack_fixer.metadata import ModrinthClient
from modpack_fixer.models import SearchResult


def make_raw_version(
    version_id: str,
    project_id: str,
    version_number: str,
    game_versions: List[str],
    loaders: List[str],
    dependencies: Optional[List[Dict[str, Any]]] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": version_id,
        "name": f"{project_id} {version_number}",
        "version_number": version_number,
        "game_versions": game_versions,
        "loaders": loaders,
        "files": [
            {
                "filename": filename or f"{project_id}-{version_number}.jar",
                "url": f"https://cdn.modrinth.com/{project_id}/{version_id}.jar",
                "size": 1234,
                "hashes": {"sha512": f"sha512-{version_id}", "sha1": f"sha1-{version_id}"},
            }
        ],
        "dependencies": dependencies or [],
    }


class FakeModrinthClient(ModrinthClient):
    """Dublê de ModrinthClient: dados fixos em memória, nunca toca a rede."""

    def __init__(self, versions_by_slug: Dict[str, List[Dict[str, Any]]], search_results=None):
        self._versions_by_slug = versions_by_slug
        self._search_results = search_results or []
        self.list_versions_calls: List[tuple] = []

    def list_versions(self, slug, game_version=None, loader=None):
        self.list_versions_calls.append((slug, game_version, loader))
        versions = self._versions_by_slug.get(slug, [])
        return [
            v
            for v in versions
            if (not game_version or game_version in v.get("game_versions", []))
            and (not loader or loader in v.get("loaders", []))
        ]

    def search_projects(self, query, limit=10, game_version=None, loader=None, project_type="mod"):
        return self._search_results[:limit]

    # Reaproveita a conversão real (não há lógica de rede aqui).
    # version_to_model é herdado de ModrinthClient sem alterações (não há
    # lógica de rede nela, só mapeamento de dicionário -> dataclass).


@pytest.fixture
def fake_client_factory():
    return FakeModrinthClient
