from __future__ import annotations

import json
from pathlib import Path

from modpack_fixer.lockfile import load_lockfile, lockfile_to_index, save_lockfile
from modpack_fixer.models import Lockfile, ModSelection


def _sample_lockfile() -> Lockfile:
    return Lockfile(
        name="Meu Pack",
        version="1.0.0",
        game="minecraft",
        game_version="1.20.1",
        loader="fabric",
        mods=[
            ModSelection(
                project_id="jei",
                version_id="v1",
                file_url="https://cdn.modrinth.com/jei/v1.jar",
                file_path="mods/jei.jar",
                sha512="abc123",
                size=1000,
            )
        ],
    )


def test_lockfile_to_index_shape():
    index = lockfile_to_index(_sample_lockfile())

    assert index["formatVersion"] == 1
    assert index["game"] == "minecraft"
    assert index["dependencies"] == {"minecraft": "1.20.1", "fabric": ""}
    assert len(index["files"]) == 1
    f = index["files"][0]
    assert f["path"] == "mods/jei.jar"
    assert f["downloads"] == ["https://cdn.modrinth.com/jei/v1.jar"]
    assert f["hashes"]["sha512"] == "abc123"
    assert f["projectId"] == "jei"
    assert f["versionId"] == "v1"


def test_save_and_load_lockfile_roundtrip(tmp_path: Path):
    lock = _sample_lockfile()

    index_path = save_lockfile(lock, tmp_path)
    assert index_path.exists()
    assert (tmp_path / "pack.toml").exists()

    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data["name"] == "Meu Pack"

    loaded = load_lockfile(index_path)
    assert loaded.name == "Meu Pack"
    assert loaded.game_version == "1.20.1"
    assert loaded.loader == "fabric"
    assert len(loaded.mods) == 1
    assert loaded.mods[0].project_id == "jei"
    assert loaded.mods[0].sha512 == "abc123"
    assert loaded.mods[0].file_url == "https://cdn.modrinth.com/jei/v1.jar"
