from __future__ import annotations

import json

from modpack_fixer.ddg import (
    _decode_ddg_redirect,
    _extract_modrinth_slug,
    search_duckduckgo,
)


def test_decode_ddg_redirect_extracts_uddg_param():
    wrapped = (
        "//duckduckgo.com/l/?uddg=https%3A%2F%2Fmodrinth.com%2Fmod%2Fjei&rut=abc"
    )
    assert _decode_ddg_redirect(wrapped) == "https://modrinth.com/mod/jei"


def test_decode_ddg_redirect_passthrough_for_plain_urls():
    url = "https://example.com/page"
    assert _decode_ddg_redirect(url) == url


def test_extract_modrinth_slug_from_mod_url():
    assert _extract_modrinth_slug("https://modrinth.com/mod/jei") == "jei"
    assert _extract_modrinth_slug("https://modrinth.com/mod/jei/versions") == "jei"


def test_extract_modrinth_slug_returns_none_for_non_modrinth_url():
    assert _extract_modrinth_slug("https://example.com/mod/jei") is None


def test_search_duckduckgo_parses_results(monkeypatch):
    html = (
        '<a rel="nofollow" class="result__a" '
        'href="https://modrinth.com/mod/jei">Just Enough Items</a>'
        '<a rel="nofollow" class="result__a" '
        'href="https://example.com/other">Other result</a>'
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return html.encode("utf-8")

    def fake_urlopen(req, timeout=20):
        return FakeResponse()

    monkeypatch.setattr("modpack_fixer.ddg.urllib.request.urlopen", fake_urlopen)

    results = search_duckduckgo("jei fabric", limit=10)

    assert len(results) == 2
    assert results[0].slug == "jei"
    assert results[0].title == "Just Enough Items"
    assert results[1].slug == ""


def test_search_duckduckgo_returns_empty_on_network_error(monkeypatch):
    def fake_urlopen(req, timeout=20):
        raise OSError("blocked")

    monkeypatch.setattr("modpack_fixer.ddg.urllib.request.urlopen", fake_urlopen)

    assert search_duckduckgo("qualquer coisa") == []
