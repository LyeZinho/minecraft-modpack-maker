"""Modelos de dados do núcleo do Modpack Fixer.

Todos os nomes de campo seguem a convenção da Modrinth para que o lockfile
seja compatível com modrinth.index.json (formato .mrpack).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class DependencyType:
    REQUIRED = "required"
    OPTIONAL = "optional"
    INCOMPATIBLE = "incompatible"
    EMBEDDED = "embedded"


@dataclass
class ModVersion:
    """Uma versão de projeto retornada pela API da Modrinth."""

    id: str                # versionId
    project_id: str        # slug do projeto
    name: str
    version_string: str    # version_number (ex: 1.0.1+mc1.20.1)
    game_versions: List[str]
    loaders: List[str]
    files: List[Dict[str, Any]]      # [{path, url, size, hashes: {sha512, sha1}}]
    dependencies: List[Dict[str, Any]]  # [{project_id, version, dependency_type}]


@dataclass
class ModSelection:
    """Um mod escolhido pelo solver, pronto para entrar no lockfile."""

    project_id: str
    version_id: str
    file_url: str            # URL oficial (Modrinth/CurseForge) — nunca redistribuímos o JAR
    file_path: str           # Caminho dentro do pack (ex: mods/jei.jar)
    sha512: str              # Hash SHA-512 do arquivo (identifica o JAR mesmo renomeado)
    size: int                # Tamanho em bytes


@dataclass
class SearchResult:
    """Resultado de busca (Modrinth API ou DuckDuckGo)."""

    source: str              # "modrinth" ou "duckduckgo"
    slug: str                # slug do projeto (pode estar vazio em resultados DDG genéricos)
    title: str
    description: str
    project_type: str        # "mod", "modpack", etc.
    downloads: int
    follows: int
    game_versions: List[str] = field(default_factory=list)
    loaders: List[str] = field(default_factory=list)
    url: str = ""
    relevance_score: float = 0.0


@dataclass
class Lockfile:
    """Estado versão-do-pack. Reproduzível byte a byte."""

    format_version: int = 1
    name: str = ""
    version: str = "1.0.0"
    game: str = "minecraft"
    game_version: str = ""
    loader: str = ""
    loader_version: Optional[str] = None
    mods: List[ModSelection] = field(default_factory=list)
    repairs: List[Dict[str, Any]] = field(default_factory=list)  # histórico de correções automáticas
    created_at: str = ""
