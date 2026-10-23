"""Solver determinístico de dependências de modpack.

Regra de arquitetura: o LLM NUNCA escolhe versão nem nome de mod. Aqui não há IA.
Quem decide compatibilidade é este solver sobre metadados da Modrinth.

Estratégia:
  1. Para cada mod raiz, escolhe a versão mais recente compatível com game_version + loader.
  2. Expande dependências `required` recursivamente (grafo).
  3. Detecta `incompatible` contra mods já selecionados.
  4. Emite lockfile com SHA-512 de cada arquivo.

Não faz backtracking complexo nesta fase (mantém o MVP simples e previsível).
Se encontrar conflito, levanta SolverError com mensagem clara para o agent de reparo
(próxima fase) tentar uma versão alternativa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .models import (
    DependencyType,
    Lockfile,
    ModSelection,
    ModVersion,
)
from .metadata import ModrinthClient


class SolverError(Exception):
    """Erro de resolução de dependências (conflito, versão ausente, etc.)."""


@dataclass
class SolverResult:
    lockfile: Lockfile
    selections: Dict[str, ModSelection]
    warnings: List[str] = field(default_factory=list)


class Solver:
    def __init__(self, client: ModrinthClient):
        self.client = client

    def resolve(
        self,
        root_mods: List[str],
        game_version: str,
        loader: str,
        pack_name: str = "Meu Pack",
    ) -> SolverResult:
        selections: Dict[str, ModSelection] = {}
        warnings: List[str] = []
        queue: List[str] = list(dict.fromkeys(root_mods))  # ordem preservada, sem duplicados
        visited: Set[str] = set()

        while queue:
            slug = queue.pop(0)
            if slug in visited:
                continue
            visited.add(slug)

            raw_versions = self.client.list_versions(
                slug, game_version=game_version, loader=loader
            )
            if not raw_versions:
                raise SolverError(
                    f"Nenhuma versão compatível para '{slug}' em "
                    f"{game_version}/{loader}"
                )

            # Escolhe a primeira versão compatível (mais recente segundo a API).
            # Esta é a única decisão de versão do solver: sempre baseada em metadados.
            version: ModVersion = self.client.version_to_model(slug, raw_versions[0])

            # Verifica incompatibilidades contra mods já selecionados.
            for dep in version.dependencies:
                if (
                    dep["dependency_type"] == DependencyType.INCOMPATIBLE
                    and dep["project_id"] in selections
                ):
                    raise SolverError(
                        f"Conflito de incompatibilidade: {slug}@{version.version_string} "
                        f"é incompatível com {dep['project_id']} já selecionado."
                    )

            if not version.files:
                raise SolverError(
                    f"Versão {version.version_string} de {slug} não possui arquivos para download."
                )

            # Pega o primeiro arquivo (geralmente o JAR principal do mod).
            file_info = version.files[0]
            selections[slug] = ModSelection(
                project_id=slug,
                version_id=version.id,
                file_url=file_info["url"],
                file_path=f"mods/{file_info['path']}",
                sha512=file_info["hashes"]["sha512"],
                size=file_info["size"],
            )

            for dep in version.dependencies:
                dtype = dep["dependency_type"]
                if dtype == DependencyType.REQUIRED:
                    if dep["project_id"] not in visited:
                        queue.append(dep["project_id"])
                elif dtype == DependencyType.INCOMPATIBLE:
                    warnings.append(
                        f"{slug}@{version.version_string} é incompatível com "
                        f"{dep['project_id']} (não está selecionado)."
                    )

        lockfile = Lockfile(
            name=pack_name,
            version="1.0.0",
            game="minecraft",
            game_version=game_version,
            loader=loader,
            mods=list(selections.values()),
        )

        return SolverResult(lockfile=lockfile, selections=selections, warnings=warnings)
