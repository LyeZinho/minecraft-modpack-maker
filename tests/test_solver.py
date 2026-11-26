from __future__ import annotations

from modpack_fixer.models import DependencyType
from modpack_fixer.solver import Solver, SolverError
from tests.conftest import FakeModrinthClient, make_raw_version


def test_resolve_single_mod_picks_matching_version():
    client = FakeModrinthClient(
        {
            "jei": [
                make_raw_version("v-old", "jei", "1.0.0", ["1.19.2"], ["fabric"]),
                make_raw_version("v-new", "jei", "2.0.0", ["1.20.1"], ["fabric"]),
            ]
        }
    )
    solver = Solver(client)

    result = solver.resolve(["jei"], game_version="1.20.1", loader="fabric", pack_name="Pack")

    assert len(result.lockfile.mods) == 1
    mod = result.lockfile.mods[0]
    assert mod.project_id == "jei"
    assert mod.version_id == "v-new"
    assert result.lockfile.game_version == "1.20.1"
    assert result.lockfile.loader == "fabric"


def test_resolve_expands_required_dependencies():
    client = FakeModrinthClient(
        {
            "create-fabric": [
                make_raw_version(
                    "create-v1",
                    "create-fabric",
                    "1.0.0",
                    ["1.20.1"],
                    ["fabric"],
                    dependencies=[
                        {
                            "project_id": "fabric-api",
                            "version": "",
                            "dependency_type": DependencyType.REQUIRED,
                        }
                    ],
                )
            ],
            "fabric-api": [
                make_raw_version("fapi-v1", "fabric-api", "0.90.0", ["1.20.1"], ["fabric"]),
            ],
        }
    )
    solver = Solver(client)

    result = solver.resolve(["create-fabric"], game_version="1.20.1", loader="fabric")

    selected_ids = {m.project_id for m in result.lockfile.mods}
    assert selected_ids == {"create-fabric", "fabric-api"}


def test_resolve_raises_when_no_compatible_version():
    client = FakeModrinthClient(
        {"create": [make_raw_version("v1", "create", "1.0.0", ["1.19.2"], ["forge"])]}
    )
    solver = Solver(client)

    try:
        solver.resolve(["create"], game_version="1.20.1", loader="fabric")
        assert False, "esperava SolverError"
    except SolverError as exc:
        assert "create" in str(exc)
        assert "1.20.1/fabric" in str(exc)


def test_resolve_raises_on_incompatible_conflict():
    client = FakeModrinthClient(
        {
            "mod-a": [
                make_raw_version(
                    "a-v1",
                    "mod-a",
                    "1.0.0",
                    ["1.20.1"],
                    ["fabric"],
                    dependencies=[
                        {
                            "project_id": "mod-b",
                            "version": "",
                            "dependency_type": DependencyType.INCOMPATIBLE,
                        }
                    ],
                )
            ],
            "mod-b": [
                make_raw_version("b-v1", "mod-b", "1.0.0", ["1.20.1"], ["fabric"]),
            ],
        }
    )
    solver = Solver(client)

    try:
        solver.resolve(["mod-b", "mod-a"], game_version="1.20.1", loader="fabric")
        assert False, "esperava SolverError de incompatibilidade"
    except SolverError as exc:
        assert "incompatibilidade" in str(exc).lower() or "incompat" in str(exc).lower()


def test_solver_never_crosses_requested_game_version_or_loader():
    """Garantia de regressão: o solver nunca deve aceitar uma versão cujo
    game_version/loader real não bata com o que foi pedido, mesmo que a API
    remota devolva itens fora do filtro (bug já visto: parâmetros ignorados
    silenciosamente pela API quando mal codificados)."""
    client = FakeModrinthClient(
        {
            "jei": [
                # Simula resposta "suja" da API: devolve versão de 1.19.2 mesmo
                # tendo sido pedido 1.20.1 (list_versions do fake já filtra,
                # mas o solver também filtra de novo como defesa extra).
                make_raw_version("wrong", "jei", "1.0.0", ["1.19.2"], ["forge"]),
                make_raw_version("right", "jei", "2.0.0", ["1.20.1"], ["fabric"]),
            ]
        }
    )
    solver = Solver(client)
    result = solver.resolve(["jei"], game_version="1.20.1", loader="fabric")
    mod = result.lockfile.mods[0]
    assert mod.version_id == "right"
