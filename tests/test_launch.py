"""Startup settings for local runs and Render (src.config.launch_settings). No server is started."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import launch_settings  # noqa: E402
from src.contracts import ConfigurationError  # noqa: E402


def test_local_defaults_without_port_or_login():
    assert launch_settings({}) == {"server_name": "127.0.0.1", "server_port": 7860, "auth": None}


def test_server_uses_all_interfaces_and_given_port():
    s = launch_settings({"PORT": "10000", "APP_USERNAME": "team", "APP_PASSWORD": "secret"})
    assert s == {"server_name": "0.0.0.0", "server_port": 10000, "auth": ("team", "secret")}


def test_both_credentials_enable_login_locally_too():
    assert launch_settings({"APP_USERNAME": "team", "APP_PASSWORD": "secret"})["auth"] == ("team", "secret")


def test_neither_credential_means_no_login_by_design():
    assert launch_settings({"PORT": "10000"})["auth"] is None


@pytest.mark.parametrize("env, missing", [
    ({"PORT": "10000", "APP_USERNAME": "team"}, "APP_PASSWORD"),
    ({"PORT": "10000", "APP_PASSWORD": "secret"}, "APP_USERNAME"),
    ({"PORT": "10000", "APP_USERNAME": "team", "APP_PASSWORD": "  "}, "APP_PASSWORD"),
    ({"APP_USERNAME": "", "APP_PASSWORD": "secret"}, "APP_USERNAME"),
])
def test_half_configured_login_stops_startup(env, missing):
    with pytest.raises(ConfigurationError, match=missing):
        launch_settings(env)


def test_invalid_port_is_a_configuration_error():
    with pytest.raises(ConfigurationError, match="PORT"):
        launch_settings({"PORT": "abc"})


def test_reads_the_process_environment_by_default(monkeypatch):
    for key in ("PORT", "APP_USERNAME", "APP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PORT", "8080")
    assert launch_settings()["server_port"] == 8080
