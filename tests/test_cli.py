from __future__ import annotations

from pathlib import Path

from modpack_fixer import cli
from modpack_fixer.lockfile import save_lockfile
from modpack_fixer.models import Lockfile, ModSelection
from tests.conftest import FakeModrinthClient, make_raw_version


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
                sha512="abc",
                size=10,
            )
        ],
    )


def test_cmd_resolve_success(monkeypatch, tmp_path: Path, capsys):
    client = FakeModrinthClient(
        {"jei": [make_raw_version("v1", "jei", "1.0.0", ["1.20.1"], ["fabric"])]}
    )
    monkeypatch.setattr(cli, "ModrinthClient", lambda: client)

    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "resolve",
            "--mods",
            "jei",
            "--game-version",
            "1.20.1",
            "--loader",
            "fabric",
            "--name",
            "Pack",
            "--output",
            str(tmp_path / "pack"),
        ]
    )
    rc = args.func(args)

    assert rc == 0
    assert (tmp_path / "pack" / "lockfile.json").exists()
    out = capsys.readouterr().out
    assert "resolvidos" in out


def test_cmd_resolve_solver_error_returns_nonzero(monkeypatch, tmp_path: Path, capsys):
    client = FakeModrinthClient({})  # nenhum mod conhecido -> SolverError
    monkeypatch.setattr(cli, "ModrinthClient", lambda: client)

    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "resolve",
            "--mods",
            "inexistente",
            "--game-version",
            "1.20.1",
            "--loader",
            "fabric",
            "--output",
            str(tmp_path / "pack"),
        ]
    )
    rc = args.func(args)

    assert rc == 1
    err = capsys.readouterr().err
    assert "ERRO" in err


def test_cmd_export_writes_mrpack(tmp_path: Path, capsys):
    pack_dir = tmp_path / "pack"
    lock_path = save_lockfile(_sample_lockfile(), pack_dir)
    out_path = tmp_path / "out.mrpack"

    parser = cli.build_parser()
    args = parser.parse_args(
        ["export", "--lockfile", str(lock_path), "--output", str(out_path)]
    )
    rc = args.func(args)

    assert rc == 0
    assert out_path.exists()


def test_cmd_search_reports_no_results(monkeypatch, capsys):
    monkeypatch.setattr(cli, "ModrinthClient", lambda: FakeModrinthClient({}))

    import modpack_fixer.search as search_mod

    monkeypatch.setattr(search_mod, "search_duckduckgo", lambda query, limit=10: [])

    parser = cli.build_parser()
    args = parser.parse_args(["search", "--query", "nada disso existe"])
    rc = args.func(args)

    assert rc == 1
    assert "Nenhum resultado" in capsys.readouterr().out


def test_main_dispatches_to_subcommand(monkeypatch, tmp_path: Path):
    client = FakeModrinthClient(
        {"jei": [make_raw_version("v1", "jei", "1.0.0", ["1.20.1"], ["fabric"])]}
    )
    monkeypatch.setattr(cli, "ModrinthClient", lambda: client)

    rc = cli.main(
        [
            "resolve",
            "--mods",
            "jei",
            "--game-version",
            "1.20.1",
            "--loader",
            "fabric",
            "--output",
            str(tmp_path / "pack"),
        ]
    )
    assert rc == 0
