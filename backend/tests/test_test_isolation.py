"""Safety regressions for database isolation and side-effect-free collection."""
import configparser
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from conftest import validate_test_database_url

from app.core.config import settings


MAIN_URL = "postgresql+asyncpg://user:pass@localhost:5432/resume_screening"
TEST_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/resume_screening_test"


@pytest.mark.parametrize(
    "url",
    [
        None,
        MAIN_URL,
        "postgresql+asyncpg://user:pass@localhost:5432/resume_screening_dev",
        "postgresql+asyncpg://user:pass@localhost:5432/resume_screening_test_backup",
        "not-a-url",
    ],
)
def test_test_database_url_validation_rejects_unsafe_values(url):
    with pytest.raises(RuntimeError):
        validate_test_database_url(url, MAIN_URL)


def test_test_database_url_validation_accepts_disposable_database():
    validate_test_database_url(TEST_URL, MAIN_URL)


def test_app_settings_do_not_default_test_url_to_main_database():
    assert settings.TEST_DATABASE_URL is None or settings.TEST_DATABASE_URL != settings.DATABASE_URL


def test_automated_tests_contain_no_destructive_database_statements():
    destructive_fragment = "__table__" + ".delete()"
    forbidden_terms = (
        "DELETE " + "FROM",
        "TRUNCATE " + "TABLE",
        "DROP " + "TABLE",
    )

    for path in Path(__file__).parent.glob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        assert destructive_fragment not in source, f"destructive cleanup in {path.name}"
        for term in forbidden_terms:
            assert term not in source.upper(), f"{term} in {path.name}"


def test_pytest_default_discovery_is_limited_to_tests_directory():
    parser = configparser.ConfigParser()
    parser.read(Path(__file__).parent.parent / "pytest.ini")
    assert parser["pytest"]["testpaths"].strip() == "tests"
    assert parser["pytest"]["python_files"].strip() == "test_*.py"


def test_collection_does_not_execute_http_or_database_engines():
    backend_dir = Path(__file__).parent.parent
    code = r"""
import pytest
import requests
import httpx
import sqlalchemy.ext.asyncio as sa_asyncio


def forbidden(*args, **kwargs):
    raise AssertionError("side effect during pytest collection")


requests.sessions.Session.request = forbidden
httpx.Client.request = forbidden
httpx.AsyncClient.request = forbidden
sa_asyncio.create_async_engine = forbidden

raise SystemExit(pytest.main(["--collect-only", "-q", "tests"]))
"""
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = TEST_URL

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    # Only tests under backend/tests/ may be collected. Root-level historical
    # scripts must remain outside default discovery.
    collected_nodes = [
        line for line in result.stdout.splitlines() if "::" in line
    ]
    assert collected_nodes
    assert all(line.startswith("tests") for line in collected_nodes)
    assert not any(
        line.startswith("test_phase") or line.startswith("verify_")
        for line in result.stdout.splitlines()
    )
