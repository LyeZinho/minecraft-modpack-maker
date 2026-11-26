from __future__ import annotations

import json
import urllib.parse

import pytest

from modpack_fixer.metadata import ModrinthClient, ModrinthError


def test_list_versions_encodes_filters_as_json_arrays(monkeypatch):
    """Regressão: a API da Modrinth exige game_versions/loaders como arrays
    JSON na query string. Enviar strings soltas faz a API ignorar o filtro
    silenciosamente e devolver TODAS as versões do projeto (bug real já
    observado em produção: resolve escolhia versão errada do jogo)."""
    captured_path = {}

    client = ModrinthClient()

    def fake_get(path):
        captured_path["path"] = path
        return []

    monkeypatch.setattr(client, "_get", fake_get)

    client.list_versions("jei", game_version="1.20.1", loader="fabric")

    path = captured_path["path"]
    assert path.startswith("/project/jei/version?")
    query = urllib.parse.parse_qs(path.split("?", 1)[1])
    assert json.loads(query["game_versions"][0]) == ["1.20.1"]
    assert json.loads(query["loaders"][0]) == ["fabric"]


def test_list_versions_without_filters_has_no_query_string(monkeypatch):
    client = ModrinthClient()
    captured = {}
    monkeypatch.setattr(client, "_get", lambda path: captured.setdefault("path", path) or [])

    client.list_versions("jei")

    assert captured["path"] == "/project/jei/version"


def test_version_to_model_maps_fields():
    client = ModrinthClient()
    raw = {
        "id": "v1",
        "name": "JEI 1.0",
        "version_number": "1.0.0",
        "game_versions": ["1.20.1"],
        "loaders": ["fabric"],
        "files": [
            {
                "filename": "jei.jar",
                "url": "https://cdn.modrinth.com/jei.jar",
                "size": 123,
                "hashes": {"sha512": "abc", "sha1": "def"},
            }
        ],
        "dependencies": [
            {"project_id": "fabric-api", "version": "", "dependency_type": "required"}
        ],
    }

    model = client.version_to_model("jei", raw)

    assert model.id == "v1"
    assert model.project_id == "jei"
    assert model.version_string == "1.0.0"
    assert model.files[0]["hashes"]["sha512"] == "abc"
    assert model.dependencies[0]["project_id"] == "fabric-api"


def test_get_uses_cache_within_ttl(monkeypatch):
    client = ModrinthClient(cache_ttl=300)
    calls = {"n": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            calls["n"] += 1
            return json.dumps({"hits": []}).encode("utf-8")

    monkeypatch.setattr(
        "modpack_fixer.metadata.urllib.request.urlopen", lambda req, timeout=30: FakeResponse()
    )

    client._get("/search?query=jei")
    client._get("/search?query=jei")

    assert calls["n"] == 1  # segunda chamada veio do cache


def test_get_raises_modrinth_error_on_http_error(monkeypatch):
    import urllib.error

    client = ModrinthClient()

    def fake_urlopen(req, timeout=30):
        raise urllib.error.HTTPError(req.full_url, 404, "not found", None, None)

    monkeypatch.setattr("modpack_fixer.metadata.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ModrinthError):
        client._get("/project/does-not-exist")


def test_get_project_and_get_version_build_correct_paths(monkeypatch):
    client = ModrinthClient()
    paths = []
    monkeypatch.setattr(client, "_get", lambda path: paths.append(path) or {"id": "x"})

    client.get_project("jei")
    client.get_version("v1")

    assert paths == ["/project/jei", "/version/v1"]


def test_search_projects_builds_facets_and_maps_hits(monkeypatch):
    client = ModrinthClient()
    captured = {}

    def fake_get(path):
        captured["path"] = path
        return {
            "hits": [
                {
                    "slug": "jei",
                    "title": "JEI",
                    "description": "desc",
                    "project_type": "mod",
                    "downloads": 10,
                    "follows": 5,
                }
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)

    results = client.search_projects("jei", limit=5, game_version="1.20.1", loader="fabric")

    assert len(results) == 1
    assert results[0].slug == "jei"
    assert results[0].url == "https://modrinth.com/mod/jei"
    assert "facets" in captured["path"] or "filter" in captured["path"]
