"""Prüft die Leitplanken aus CLAUDE.md (Abschnitt Docker) an den Konfigurationsdateien."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    data = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def services(compose: dict[str, Any]) -> dict[str, Any]:
    result = compose["services"]
    assert isinstance(result, dict)
    return result


def test_expected_services_exist(services: dict[str, Any]) -> None:
    assert {"db", "app", "web"} <= services.keys()
    assert services["db"]["image"].startswith("pgvector/pgvector:pg16")


def test_ports_are_bound_to_localhost(services: dict[str, Any]) -> None:
    for name, service in services.items():
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name}: {port}"


def test_every_service_has_a_healthcheck(services: dict[str, Any]) -> None:
    for name, service in services.items():
        assert "healthcheck" in service, name


def test_app_waits_for_healthy_db(services: dict[str, Any]) -> None:
    assert services["app"]["depends_on"]["db"]["condition"] == "service_healthy"


def test_no_literal_secrets_in_compose(services: dict[str, Any]) -> None:
    secret_keys = re.compile(r"PASSWORD|API_KEY|SECRET|TOKEN", re.IGNORECASE)
    for name, service in services.items():
        environment = service.get("environment", {})
        assert isinstance(environment, dict), f"{name}: environment als Mapping schreiben"
        for key, value in environment.items():
            if secret_keys.search(key):
                assert str(value).startswith("${"), f"{name}.{key} enthält einen Klartextwert"


def test_db_does_not_receive_the_full_env_file(services: dict[str, Any]) -> None:
    assert "env_file" not in services["db"]


def test_pgdata_volume_is_declared(compose: dict[str, Any], services: dict[str, Any]) -> None:
    assert "pgdata" in compose["volumes"]
    assert any(v.startswith("pgdata:") for v in services["db"]["volumes"])


def test_raw_cache_is_bind_mounted_for_app(services: dict[str, Any]) -> None:
    app = services["app"]
    assert "./data/raw:/app/data/raw" in app["volumes"]
    assert app["environment"]["RAW_CACHE_DIR"] == "/app/data/raw"


def test_model_cache_is_a_volume_not_part_of_the_image(
    compose: dict[str, Any], services: dict[str, Any]
) -> None:
    assert "hf-cache" in compose["volumes"]
    assert "hf-cache:/home/app/.cache/huggingface" in services["app"]["volumes"]
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "HF_HOME=/home/app/.cache/huggingface" in dockerfile
    assert "chown -R app:app /home/app/.cache" in dockerfile


def test_torch_comes_from_the_cpu_index() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'torch = [{ index = "pytorch-cpu" }]' in pyproject
    assert 'url = "https://download.pytorch.org/whl/cpu"' in pyproject
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "nvidia-' not in lock
    assert 'name = "triton"' not in lock


def test_dockerfile_runs_as_non_root_without_uv() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    final_stage = dockerfile.rsplit("\nFROM ", 1)[1]
    users = re.findall(r"^USER\s+(\S+)", final_stage, flags=re.MULTILINE)
    assert users, "finale Stage ohne USER"
    assert users[-1] not in {"root", "0"}
    assert "uv" not in re.findall(r"^COPY --from=(\S+)", final_stage, flags=re.MULTILINE)
    assert "uv sync --frozen --no-dev" in dockerfile


def test_entrypoint_runs_migrations_before_command() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    final_stage = dockerfile.rsplit("\nFROM ", 1)[1]
    assert 'ENTRYPOINT ["docker-entrypoint.sh"]' in final_stage

    script = (ROOT / "docker-entrypoint.sh").read_bytes()
    assert b"\r" not in script, "CRLF bricht das Skript im Linux-Container"
    lines = script.decode("utf-8").splitlines()
    assert lines[0] == "#!/bin/sh"
    assert "set -e" in lines
    migrate = lines.index("python -m parlrag.db.migrate")
    assert lines.index('exec "$@"') > migrate


@pytest.mark.parametrize("entry", [".git", ".venv", "data/", "node_modules", "__pycache__", ".env"])
def test_dockerignore_contains_required_entries(entry: str) -> None:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert entry in lines


# --- Service web (Task 5.3) ---------------------------------------------------------------

WEB = ROOT / "web"


def test_web_waits_for_healthy_app_and_sees_no_secrets(services: dict[str, Any]) -> None:
    web = services["web"]
    assert web["build"] == "./web"
    assert web["depends_on"]["app"]["condition"] == "service_healthy"
    assert web["ports"] == ["127.0.0.1:8080:8080"]
    assert "env_file" not in web and "environment" not in web
    assert "/healthz" in " ".join(web["healthcheck"]["test"])


def test_web_image_builds_with_node_and_runs_unprivileged_nginx() -> None:
    dockerfile = (WEB / "Dockerfile").read_text(encoding="utf-8")
    stages = re.findall(r"^FROM (\S+) AS (\w+)", dockerfile, re.MULTILINE)
    assert [stage for _, stage in stages] == ["build", "runtime"]
    assert stages[0][0].startswith("node:24")
    assert stages[1][0].startswith("nginxinc/nginx-unprivileged:")  # Non-Root, Port 8080
    runtime = dockerfile.split("AS runtime", 1)[1]
    assert "npm" not in runtime and "node" not in runtime.lower().replace("nginx", "")
    assert "npm ci" in dockerfile and "npm run build" in dockerfile


def test_nginx_proxies_api_to_app_and_serves_spa() -> None:
    conf = (WEB / "nginx.conf").read_text(encoding="utf-8")
    assert re.search(r"location /api/ \{[^}]*proxy_pass http://app:8000/;", conf)
    assert "proxy_read_timeout 180s;" in conf
    assert "try_files $uri $uri/ /index.html;" in conf
    assert "location = /healthz" in conf and "listen 8080;" in conf


def test_web_dockerignore_excludes_build_artifacts() -> None:
    entries = (WEB / ".dockerignore").read_text(encoding="utf-8").split()
    assert {"node_modules", "dist"} <= set(entries)


# --- Produktion der Demo (Task 6.3a) -------------------------------------------------------


class ComposeLoader(yaml.SafeLoader):
    """Kennt die Compose-Tags !reset und !override (Wert bleibt, Tag wird vermerkt)."""


def _tagged(loader: yaml.SafeLoader, node: yaml.Node) -> Any:
    if isinstance(node, yaml.SequenceNode):
        return {"tag": node.tag, "value": loader.construct_sequence(node)}
    return {"tag": node.tag, "value": loader.construct_object(node)}


for _tag in ("!reset", "!override"):
    ComposeLoader.add_constructor(_tag, _tagged)


@pytest.fixture(scope="module")
def prod() -> dict[str, Any]:
    data = yaml.load(  # SafeLoader mit zwei zusätzlichen Tags
        (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8"), Loader=ComposeLoader
    )
    assert isinstance(data, dict)
    services: dict[str, Any] = data["services"]
    return services


def test_prod_only_caddy_is_public(prod: dict[str, Any]) -> None:
    for name in ("db", "app", "web"):
        assert prod[name]["ports"] == {"tag": "!reset", "value": []}, name
    assert prod["caddy"]["ports"] == ["80:80", "443:443", "443:443/udp"]
    for name, service in prod.items():
        assert service["restart"] == "unless-stopped", name


def test_prod_uses_haiku_over_api_key_with_limits(prod: dict[str, Any]) -> None:
    environment = prod["app"]["environment"]
    assert environment["LLM_BACKEND"] == "api"  # nie das Abo (AK-6.3)
    assert environment["ANTHROPIC_MODEL"] == "claude-haiku-5-5"
    # Feste Werte: eine aus .env.example kopierte 0 darf die Grenzen nicht ausschalten.
    assert float(environment["DEMO_MONTHLY_BUDGET_USD"]) > 0
    assert int(environment["RATE_LIMIT_PER_HOUR"]) > 0
    assert environment["TRUST_PROXY_HEADERS"] == "true"
    for name, service in prod.items():
        for key in service.get("environment", {}):
            assert not re.search(r"PASSWORD|API_KEY|SECRET|TOKEN", key), f"{name}.{key}"


def test_prod_raw_cache_is_a_named_volume(prod: dict[str, Any]) -> None:
    volumes = prod["app"]["volumes"]
    assert volumes["tag"] == "!override"
    assert "raw-cache:/app/data/raw" in volumes["value"]
    assert not any(volume.startswith("./data") for volume in volumes["value"])


def test_prod_caddy_is_pinned_healthy_and_waits_for_web(prod: dict[str, Any]) -> None:
    caddy = prod["caddy"]
    assert re.fullmatch(r"caddy:2\.\d+-alpine", caddy["image"])
    assert caddy["depends_on"]["web"]["condition"] == "service_healthy"
    assert "healthcheck" in caddy
    assert "./deploy/Caddyfile:/etc/caddy/Caddyfile:ro" in caddy["volumes"]
    assert caddy["environment"]["DEMO_DOMAIN"].startswith("${DEMO_DOMAIN:?")


def test_caddyfile_sets_real_client_ip_and_keeps_no_access_log() -> None:
    caddyfile = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    assert "{$DEMO_DOMAIN}" in caddyfile
    assert "reverse_proxy web:8080" in caddyfile
    assert "header_up X-Forwarded-For {remote_host}" in caddyfile
    assert not re.search(r"^\s*log", caddyfile, re.MULTILINE)  # keine Zugriffslogs mit IPs
