from __future__ import annotations

import json
import zipfile
from pathlib import Path

from modpack_fixer.export import export_mrpack
from modpack_fixer.lockfile import save_lockfile
from modpack_fixer.models import Lockfile, ModSelection


def _sample_lockfile() -> Lockfile:
    return Lockfile(
        name="Pack",
        version="1.0.0",
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


def _read_index(mrpack_path: Path):
    with zipfile.ZipFile(mrpack_path) as zf:
        return json.loads(zf.read("modrinth.index.json"))


def test_export_mrpack_from_lockfile_object(tmp_path: Path):
    out = tmp_path / "pack.mrpack"
    export_mrpack(_sample_lockfile(), out)

    assert out.exists()
    index = _read_index(out)
    assert index["name"] == "Pack"
    assert index["files"][0]["projectId"] == "jei"


def test_export_mrpack_from_lockfile_path(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    lock_path = save_lockfile(_sample_lockfile(), pack_dir)

    out = tmp_path / "pack.mrpack"
    export_mrpack(str(lock_path), out)

    assert out.exists()
    index = _read_index(out)
    assert index["name"] == "Pack"
