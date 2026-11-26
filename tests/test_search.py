from __future__ import annotations

from modpack_fixer.search import _strip_facet_tokens, auto_select, unified_search
from modpack_fixer.models import SearchResult
from tests.conftest import FakeModrinthClient


def test_strip_facet_tokens_removes_redundant_loader_and_version():
    stripped = _strip_facet_tokens("jei fabric 1.20.1", game_version="1.20.1", loader="fabric")
    assert stripped == "jei"


def test_strip_facet_tokens_keeps_query_when_nothing_to_strip():
    stripped = _strip_facet_tokens("melhor mod de automacao", game_version=None, loader=None)
    assert stripped == "melhor mod de automacao"


def test_strip_facet_tokens_falls_back_to_original_if_everything_removed():
    # Query é só o loader + versão: nada sobra -> mantém a query original
    stripped = _strip_facet_tokens("fabric 1.20.1", game_version="1.20.1", loader="fabric")
    assert stripped == "fabric 1.20.1"


def test_unified_search_prefers_modrinth_and_dedupes_by_slug(monkeypatch):
    modrinth_hit = SearchResult(
        source="modrinth",
        slug="jei",
        title="Just Enough Items",
        description="View recipes",
        project_type="mod",
        downloads=1_000_000,
        follows=100,
    )
    client = FakeModrinthClient({}, search_results=[modrinth_hit])

    ddg_hit_same_slug = SearchResult(
        source="duckduckgo", slug="jei", title="JEI (DDG)", description="", project_type="mod",
        downloads=0, follows=0,
    )
    ddg_hit_other = SearchResult(
        source="duckduckgo", slug="other-mod", title="Other Mod", description="", project_type="mod",
        downloads=0, follows=0,
    )

    monkeypatch.setattr(
        "modpack_fixer.search.search_duckduckgo",
        lambda query, limit=10: [ddg_hit_same_slug, ddg_hit_other],
    )

    results = unified_search("jei", client, limit=10)

    slugs = [r.slug for r in results]
    assert slugs.count("jei") == 1  # deduplicado, Modrinth venceu
    jei_result = next(r for r in results if r.slug == "jei")
    assert jei_result.source == "modrinth"
    assert "other-mod" in slugs


def test_unified_search_never_crashes_when_both_sources_fail(monkeypatch):
    class BrokenClient(FakeModrinthClient):
        def search_projects(self, *a, **kw):
            raise RuntimeError("rede fora do ar")

    client = BrokenClient({})
    monkeypatch.setattr(
        "modpack_fixer.search.search_duckduckgo",
        lambda query, limit=10: (_ for _ in ()).throw(RuntimeError("ddg bloqueado")),
    )

    results = unified_search("qualquer coisa", client, limit=5)
    assert results == []


def test_auto_select_returns_first_or_none():
    assert auto_select([]) is None
    r = SearchResult(
        source="modrinth", slug="jei", title="JEI", description="", project_type="mod",
        downloads=0, follows=0,
    )
    assert auto_select([r]) is r
