"""Django serves the built React app at every address the app handles (design §2)."""

from pathlib import Path

import pytest
from django.test import Client
from pytest_django.fixtures import Settings

PAGE = "<!doctype html><title>Salary Insights</title><div id=root></div>"


@pytest.fixture
def built(tmp_path: Path, settings: Settings) -> Path:
    (tmp_path / "index.html").write_text(PAGE)
    settings.SPA_DIR = tmp_path
    return tmp_path


@pytest.mark.parametrize("path", ["/", "/insights", "/employees/42", "/employees?q=ana"])
def test_each_page_of_the_app_gets_its_html(client: Client, built: Path, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.content.decode() == PAGE
    assert "no-cache" in response["Cache-Control"]  # a deploy is picked up on the next load
    assert "Content-Security-Policy" in response


@pytest.mark.parametrize("path", ["/api/v1/nothing-here/", "/static/nothing-here.js"])
def test_unknown_api_and_static_addresses_are_not_the_app(
    client: Client, built: Path, path: str
) -> None:
    assert client.get(path).status_code == 404


def test_without_a_build_it_says_how_to_make_one(
    client: Client, settings: Settings, tmp_path: Path
) -> None:
    settings.SPA_DIR = tmp_path / "not-built"

    response = client.get("/employees")

    assert response.status_code == 404
    assert "npm run build" in response.content.decode()


def test_its_hashed_files_are_cached_for_good(
    client: Client, built: Path, settings: Settings
) -> None:
    (built / "assets").mkdir()
    (built / "assets" / "index-CakGX8yk.js").write_text("export {};")
    (built / "favicon.svg").write_text("<svg/>")
    settings.STATICFILES_DIRS = [built]
    settings.WHITENOISE_USE_FINDERS = True

    hashed = client.get("/static/assets/index-CakGX8yk.js")
    plain = client.get("/static/favicon.svg")

    assert hashed["Cache-Control"] == "max-age=315360000, public, immutable"
    assert "immutable" not in plain["Cache-Control"]  # its name stays the same when it changes
