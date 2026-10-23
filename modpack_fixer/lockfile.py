"""Leitura e gravação do lockfile (modrinth.index.json + pack.toml).

O lockfile é o artefato reprodutível:
- modrinth.index.json -> usado por launchers compatíveis (.mrpack) e por nós para reconstruir o pack.
- pack.toml -> metadados legíveis por humanos e histórico de reparos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .models import Lockfile, ModSelection


def lockfile_to_index(lock: Lockfile) -> Dict[str, Any]:
    """Converte Lockfile para o dicionário compatível com modrinth.index.json."""
    deps: Dict[str, Any] = {
        "minecraft": lock.game_version,
    }
    if lock.loader:
        deps[lock.loader] = lock.loader_version or ""

    return {
        "formatVersion": lock.format_version,
        "game": lock.game,
        "name": lock.name,
        "version": lock.version,
        "files": [
            {
                "path": m.file_path,
                "downloads": [m.file_url],
                "fileSize": m.size,
                "hashes": {"sha512": m.sha512},
                "projectId": m.project_id,
                "versionId": m.version_id,
            }
            for m in lock.mods
        ],
        "dependencies": deps,
    }


def save_lockfile(lock: Lockfile, directory: Path, name: str = "lockfile.json") -> Path:
    """Salva modrinth.index.json e pack.toml no diretório indicado."""
    directory.mkdir(parents=True, exist_ok=True)

    index_path = directory / name
    index_path.write_text(
        json.dumps(lockfile_to_index(lock), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    toml = (
        f'name = "{lock.name}"\n'
        f'version = "{lock.version}"\n'
        f'game = "{lock.game}"\n'
        f'game_version = "{lock.game_version}"\n'
        f'loader = "{lock.loader}"\n'
        f'loader_version = "{lock.loader_version or ""}"\n'
        f'created_at = "{datetime.now(timezone.utc).isoformat()}"\n'
    )
    (directory / "pack.toml").write_text(toml, encoding="utf-8")
    return index_path


def load_lockfile(path: Path) -> Lockfile:
    """Carrega um lockfile salvo anteriormente (útil para diff/reparo)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    mods: List[ModSelection] = []
    for f in data.get("files", []):
        downloads = f.get("downloads") or []
        mods.append(
            ModSelection(
                project_id=f.get("projectId", ""),
                version_id=f.get("versionId", ""),
                file_url=downloads[0] if downloads else "",
                file_path=f.get("path", ""),
                sha512=(f.get("hashes") or {}).get("sha512", ""),
                size=f.get("fileSize", 0),
            )
        )

    deps = data.get("dependencies", {}) or {}
    loader = deps.get("forge") or deps.get("fabric") or deps.get("quilt") or deps.get("neoforge") or ""

    return Lockfile(
        format_version=data.get("formatVersion", 1),
        name=data.get("name", ""),
        version=data.get("version", ""),
        game=data.get("game", "minecraft"),
        game_version=deps.get("minecraft", ""),
        loader=loader,
        mods=mods,
    )
