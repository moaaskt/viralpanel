"""Database schema integrity, Alembic migration lifecycle, and drift detection tests."""

import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import UniqueConstraint, create_engine, inspect, text
from sqlalchemy.engine import make_url

from viralpanel import models  # noqa: F401
from viralpanel.database import Base

SAFE_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}
KNOWN_TABLES = {"source_videos", "scripts", "assets", "publications", "runs"}


def is_ci() -> bool:
    """Detect whether tests are running inside a Continuous Integration environment."""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


def get_verified_test_db_url() -> str:
    """Validate TEST_DATABASE_URL strictly for isolated destructive PostgreSQL testing.

    Security & Isolation Rules:
    1. Consumes ONLY TEST_DATABASE_URL (never DATABASE_URL or runtime Settings).
    2. Driver MUST be PostgreSQL.
    3. Database name MUST be strictly 'viralpanel_test'.
    4. Host MUST be in SAFE_LOCAL_HOSTS unless ALLOW_REMOTE_TEST_DATABASE == 'true'
       (enforced uniformly across both local and CI environments).
    """
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url or not raw_url.strip():
        raise ValueError("TEST_DATABASE_URL is missing or empty.")

    cleaned_url = raw_url.strip()
    parsed = make_url(cleaned_url)

    if not parsed.drivername.startswith("postgresql"):
        raise ValueError(
            f"TEST_DATABASE_URL uses invalid driver '{parsed.drivername}'. Expected PostgreSQL."
        )

    if parsed.database != "viralpanel_test":
        raise ValueError(
            f"SECURITY BLOCK: TEST_DATABASE_URL points to database '{parsed.database}'. "
            "Destructive migration tests require the dedicated 'viralpanel_test' database."
        )

    host = (urlparse(cleaned_url).hostname or parsed.host or "").lower()
    if host not in SAFE_LOCAL_HOSTS and os.getenv("ALLOW_REMOTE_TEST_DATABASE") != "true":
        raise ValueError(
            f"SECURITY BLOCK: TEST_DATABASE_URL points to non-local host '{host}'. "
            f"Allowed hosts without override: {sorted(SAFE_LOCAL_HOSTS)}. "
            "Set ALLOW_REMOTE_TEST_DATABASE='true' explicitly to allow remote hosts."
        )

    # Preserve full credentials in returned URL string (str(make_url(...)) masks passwords).
    return parsed.render_as_string(hide_password=False)


def is_postgres_available() -> bool:
    """Verify TCP reachability and active database identity exclusively for TEST_DATABASE_URL."""
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url or not raw_url.strip():
        return False

    try:
        url = get_verified_test_db_url()
        parsed = make_url(url)
        host = urlparse(url).hostname or parsed.host or "127.0.0.1"
        port = parsed.port or 5432

        with socket.create_connection((host, port), timeout=0.8):
            pass

        eng = create_engine(url, connect_args={"connect_timeout": 2})
        try:
            with eng.connect() as conn:
                db_name = conn.execute(text("SELECT current_database()")).scalar()
                if db_name != "viralpanel_test":
                    return False
        finally:
            eng.dispose()

        return True
    except Exception:
        return False


def _unwrap_diff_item(diff_item: Any) -> Any:
    """Unwrap 1-element list/tuple containers emitted by Alembic compare_metadata."""
    if isinstance(diff_item, (list, tuple)) and len(diff_item) == 1 and isinstance(diff_item[0], tuple):
        return diff_item[0]
    return diff_item


def is_allowed_sqlite_dialect_diff(diff_item: Any) -> bool:
    """Restrictive allowlist for documented SQLite dialect reflection differences only.

    Alembic 1.20+ emits:
    - modify_nullable: 7-tuple ('modify_nullable', schema, table, col, meta, existing_nullable, modify_nullable)
      where SQLite reflects PK 'id' columns as existing_nullable=True vs model nullable=False.
    - add_constraint: 2-tuple ('add_constraint', UniqueConstraint) where SQLite reflects inline
      UNIQUE constraints on source_videos.url anonymously (name is None).
    """
    item = _unwrap_diff_item(diff_item)
    if not isinstance(item, tuple) or len(item) < 2:
        return False

    diff_type = item[0]

    if diff_type == "modify_nullable" and len(item) == 7:
        table_name = item[2]
        column_name = item[3]
        existing_nullable = item[5]
        modify_nullable = item[6]

        if table_name in KNOWN_TABLES and column_name == "id":
            table = Base.metadata.tables.get(table_name)
            if table is not None and "id" in table.primary_key.columns:
                if existing_nullable is True and modify_nullable is False:
                    return True

    if diff_type == "add_constraint" and len(item) == 2:
        constraint = item[1]
        if isinstance(constraint, UniqueConstraint) and constraint.name is None:
            table_name = constraint.table.name if constraint.table is not None else None
            col_names = [col.name for col in constraint.columns]
            if table_name == "source_videos" and col_names == ["url"]:
                return True

    return False


@pytest.fixture
def alembic_config_sqlite(tmp_path):
    """Provide an isolated SQLite engine and Alembic Config pointing to a temporary file DB."""
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)

    ini_path = Path(__file__).parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

    try:
        yield cfg, engine
    finally:
        engine.dispose()


def test_alembic_env_connection_injection(alembic_config_sqlite):
    """Ensure alembic/env.py honors injected connections and avoids touching production DB."""
    cfg, engine = alembic_config_sqlite
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "001")

    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        assert KNOWN_TABLES.issubset(tables)
        mc = MigrationContext.configure(conn)
        assert mc.get_current_revision() == "001"


def test_migration_002_upgrade_and_downgrade(alembic_config_sqlite):
    """Verify incremental upgrade from 001 to 002 adds metadata_json and downgrade removes it."""
    cfg, engine = alembic_config_sqlite

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "001")

    with engine.connect() as conn:
        cols_001 = [c["name"] for c in inspect(conn).get_columns("scripts")]
        assert "metadata_json" not in cols_001

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "002")

    with engine.connect() as conn:
        cols_002 = [c["name"] for c in inspect(conn).get_columns("scripts")]
        assert "metadata_json" in cols_002
        assert MigrationContext.configure(conn).get_current_revision() == "002"

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "001")

    with engine.connect() as conn:
        cols_downgrade = [c["name"] for c in inspect(conn).get_columns("scripts")]
        assert "metadata_json" not in cols_downgrade
        assert MigrationContext.configure(conn).get_current_revision() == "001"


def test_upgrade_clean_database_to_head(alembic_config_sqlite):
    """Verify clean database upgrades straight to head with all 5 tables and metadata_json."""
    cfg, engine = alembic_config_sqlite

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        assert KNOWN_TABLES.issubset(tables)

        columns = [c["name"] for c in inspector.get_columns("scripts")]
        assert "metadata_json" in columns

        mc = MigrationContext.configure(conn)
        assert mc.get_current_revision() == "002"


def test_incremental_migration_001_to_002_and_data_integrity(alembic_config_sqlite):
    """Verify upgrading 001 -> 002 preserves existing rows (NULL metadata_json) and supports new JSON writes."""
    cfg, engine = alembic_config_sqlite

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "001")

    with engine.connect() as conn:
        cols_001 = [c["name"] for c in inspect(conn).get_columns("scripts")]
        assert "metadata_json" not in cols_001

        conn.execute(
            text(
                "INSERT INTO source_videos (id, platform, url, collected_at, status) "
                "VALUES ('sv-test-1', 'tiktok', 'https://tiktok.com/@zunto/1', '2026-11-14 00:00:00', 'pending')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO scripts (id, source_video_id, transcription, script_text, hook, version, created_at) "
                "VALUES ('sc-test-1', 'sv-test-1', 'transcricao teste', 'roteiro original', 'gancho', 1, '2026-11-14 00:00:00')"
            )
        )
        conn.commit()

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "002")

    with engine.connect() as conn:
        cols_002 = [c["name"] for c in inspect(conn).get_columns("scripts")]
        assert "metadata_json" in cols_002

        legacy_row = conn.execute(
            text("SELECT id, script_text, metadata_json FROM scripts WHERE id = 'sc-test-1'")
        ).fetchone()
        assert legacy_row is not None
        assert legacy_row[0] == "sc-test-1"
        assert legacy_row[1] == "roteiro original"
        assert legacy_row[2] is None

        payload = json.dumps(
            {
                "factual_claims": [{"claim": "Great white sharks replace teeth continuously"}],
                "closing_thought": "Nature engineering at its finest.",
                "cta": "Follow for more",
            }
        )
        conn.execute(
            text(
                "INSERT INTO scripts (id, source_video_id, transcription, script_text, hook, version, created_at, metadata_json) "
                "VALUES ('sc-test-2', 'sv-test-1', 't2', 'r2', 'h2', 2, '2026-11-14 00:01:00', :meta)"
            ),
            {"meta": payload},
        )
        conn.commit()

        new_row = conn.execute(
            text("SELECT id, metadata_json FROM scripts WHERE id = 'sc-test-2'")
        ).fetchone()
        assert new_row is not None
        parsed_meta = json.loads(new_row[1]) if isinstance(new_row[1], str) else new_row[1]
        assert "factual_claims" in parsed_meta
        assert parsed_meta["closing_thought"] == "Nature engineering at its finest."
        assert parsed_meta["cta"] == "Follow for more"


def test_migration_roundtrip_cycle(alembic_config_sqlite):
    """Verify full round-trip lifecycle: base -> head -> 001 -> base -> head leaves no orphans."""
    cfg, engine = alembic_config_sqlite

    # 1. Clean upgrade to head
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    # 2. Downgrade head -> 001
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "001")

    with engine.connect() as conn:
        cols = [c["name"] for c in inspect(conn).get_columns("scripts")]
        assert "metadata_json" not in cols
        assert MigrationContext.configure(conn).get_current_revision() == "001"

    # 3. Downgrade 001 -> base
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")

    with engine.connect() as conn:
        app_tables = [t for t in inspect(conn).get_table_names() if t != "alembic_version"]
        assert app_tables == []
        assert MigrationContext.configure(conn).get_current_revision() is None

    # 4. Re-upgrade base -> head
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        inspector = inspect(conn)
        assert KNOWN_TABLES.issubset(set(inspector.get_table_names()))
        assert "metadata_json" in [c["name"] for c in inspector.get_columns("scripts")]
        assert MigrationContext.configure(conn).get_current_revision() == "002"


def test_schema_no_drift_compare_metadata(alembic_config_sqlite):
    """Verify ORM models match migrated SQLite schema aside from documented SQLite dialect items."""
    cfg, engine = alembic_config_sqlite

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        diff = compare_metadata(mc, Base.metadata)

        unallowed_diffs = [d for d in diff if not is_allowed_sqlite_dialect_diff(d)]
        assert unallowed_diffs == [], (
            f"Unauthorized schema drift detected in SQLite! Diffs outside allowlist: {unallowed_diffs}"
        )

        metadata_json_diffs = []
        for d in diff:
            item = _unwrap_diff_item(d)
            if (
                isinstance(item, tuple)
                and len(item) >= 4
                and item[2] == "scripts"
                and getattr(item[3], "name", item[3]) == "metadata_json"
            ):
                metadata_json_diffs.append(d)
        assert metadata_json_diffs == [], f"Schema drift on scripts.metadata_json: {metadata_json_diffs}"


def test_postgres_real_migration_and_strict_zero_drift():
    """Run full destructive round-trip and strict zero-drift check against real viralpanel_test DB.

    Fail-closed locally (skips cleanly if unconfigured or unauthorized) and mandatory in CI
    (fails build via pytest.fail on any missing authorization, wrong DB, or unreachable Postgres).
    """
    raw_test_url = os.getenv("TEST_DATABASE_URL")

    # 1. Presence check (zero fallback to DATABASE_URL or Settings)
    if not raw_test_url or not raw_test_url.strip():
        msg = (
            "TEST_DATABASE_URL is not configured. Define "
            "TEST_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/viralpanel_test'."
        )
        if is_ci():
            pytest.fail(f"CI SECURITY FAILURE: {msg}")
        pytest.skip(f"Local PostgreSQL migration test skipped: {msg}")

    # 2. Strict URL, driver, database ('viralpanel_test'), and host verification
    try:
        test_url = get_verified_test_db_url()
    except ValueError as exc:
        if is_ci():
            pytest.fail(f"CI SECURITY FAILURE: Invalid TEST_DATABASE_URL: {exc}")
        pytest.skip(f"Local PostgreSQL migration test skipped due to invalid TEST_DATABASE_URL: {exc}")

    # 3. Mandatory explicit destructive authorization BEFORE opening any socket/engine
    if os.getenv("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "true":
        msg = (
            "ALLOW_DESTRUCTIVE_TEST_DATABASE='true' is required before creating an engine or running "
            "destructive operations on dedicated disposable database 'viralpanel_test'."
        )
        if is_ci():
            pytest.fail(f"CI SECURITY FAILURE: {msg}")
        pytest.skip(f"Local PostgreSQL migration test skipped: {msg}")

    # 4. Connectivity check
    if not is_postgres_available():
        msg = "PostgreSQL test server for 'viralpanel_test' is unreachable at TEST_DATABASE_URL."
        if is_ci():
            pytest.fail(f"CI CONNECTIVITY FAILURE: {msg}")
        pytest.skip(f"Local PostgreSQL migration test skipped: {msg}")

    # 5. Create isolated engine strictly from verified TEST_DATABASE_URL
    engine = create_engine(test_url)
    try:
        # 6. Runtime assertion confirming target DB before any destructive DDL
        with engine.connect() as conn:
            active_db = conn.execute(text("SELECT current_database()")).scalar()
            assert active_db == "viralpanel_test", (
                f"SECURITY VIOLATION: Connected to '{active_db}', expected 'viralpanel_test'. Aborting!"
            )

        ini_path = Path(__file__).parent.parent / "alembic.ini"
        cfg = Config(str(ini_path))
        cfg.set_main_option("sqlalchemy.url", test_url.replace("%", "%%"))

        # 7. Destructive round-trip cycle on disposable PostgreSQL test DB
        with engine.connect() as conn:
            cfg.attributes["connection"] = conn
            command.downgrade(cfg, "base")

        with engine.connect() as conn:
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "head")

        # 8. Strict zero-drift check with zero allowlist filters
        with engine.connect() as conn:
            mc = MigrationContext.configure(conn)
            diff = compare_metadata(mc, Base.metadata)
            assert diff == [], f"Schema drift detected on PostgreSQL: {diff}"
    finally:
        engine.dispose()


def test_get_verified_test_db_url_security_guards(monkeypatch):
    """Prove URL validation rejects non-test DBs, remote hosts without flag, and preserves credentials."""
    monkeypatch.delenv("ALLOW_REMOTE_TEST_DATABASE", raising=False)

    monkeypatch.setenv("TEST_DATABASE_URL", "")
    with pytest.raises(ValueError, match="missing or empty"):
        get_verified_test_db_url()

    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///local.db")
    with pytest.raises(ValueError, match="invalid driver"):
        get_verified_test_db_url()

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://postgres:secret@localhost:5432/viralpanel")
    with pytest.raises(ValueError, match="SECURITY BLOCK"):
        get_verified_test_db_url()

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://postgres:secret@prod-db.internal:5432/viralpanel_test")
    with pytest.raises(ValueError, match="non-local host"):
        get_verified_test_db_url()

    monkeypatch.setenv("ALLOW_REMOTE_TEST_DATABASE", "true")
    remote_verified = get_verified_test_db_url()
    assert remote_verified == "postgresql://postgres:secret@prod-db.internal:5432/viralpanel_test"
    assert "***" not in remote_verified

    monkeypatch.delenv("ALLOW_REMOTE_TEST_DATABASE", raising=False)
    for host in SAFE_LOCAL_HOSTS:
        formatted_host = f"[{host}]" if ":" in host else host
        monkeypatch.setenv(
            "TEST_DATABASE_URL",
            f"postgresql+psycopg2://postgres:mysecret@{formatted_host}:5432/viralpanel_test",
        )
        local_verified = get_verified_test_db_url()
        assert "mysecret" in local_verified
        assert "***" not in local_verified


def test_postgres_test_fail_closed_in_ci_and_skip_locally(monkeypatch):
    """Prove fail-closed behavior in local vs CI without ever opening engines or sockets."""

    def _forbid_engine(*args, **kwargs):
        raise AssertionError("create_engine must never be called when guards reject!")

    monkeypatch.setattr("tests.test_migrations.create_engine", _forbid_engine)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_TEST_DATABASE", raising=False)

    # Local mode without TEST_DATABASE_URL -> skip
    with pytest.raises(pytest.skip.Exception):
        test_postgres_real_migration_and_strict_zero_drift()

    # Local mode with wrong DB -> skip
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/viralpanel")
    with pytest.raises(pytest.skip.Exception):
        test_postgres_real_migration_and_strict_zero_drift()

    # Local mode with viralpanel_test but missing ALLOW_DESTRUCTIVE_TEST_DATABASE -> skip
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/viralpanel_test")
    with pytest.raises(pytest.skip.Exception):
        test_postgres_real_migration_and_strict_zero_drift()

    # CI mode fails closed via pytest.fail before creating engine
    monkeypatch.setenv("CI", "true")
    with pytest.raises(pytest.fail.Exception, match="ALLOW_DESTRUCTIVE_TEST_DATABASE"):
        test_postgres_real_migration_and_strict_zero_drift()

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/viralpanel")
    with pytest.raises(pytest.fail.Exception, match="Invalid TEST_DATABASE_URL"):
        test_postgres_real_migration_and_strict_zero_drift()

    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(pytest.fail.Exception, match="TEST_DATABASE_URL is not configured"):
        test_postgres_real_migration_and_strict_zero_drift()


def test_sqlite_dialect_diff_allowlist_is_strict():
    """Prove SQLite allowlist accepts only exact documented shapes and rejects real drift."""
    valid_pk_diff = ("modify_nullable", None, "scripts", "id", {"existing_type": "VARCHAR(36)"}, True, False)
    assert is_allowed_sqlite_dialect_diff(valid_pk_diff) is True
    assert is_allowed_sqlite_dialect_diff([valid_pk_diff]) is True

    # Non-PK column nullable mismatch must be rejected
    non_pk_diff = ("modify_nullable", None, "scripts", "hook", {}, True, False)
    assert is_allowed_sqlite_dialect_diff(non_pk_diff) is False

    # Reverse nullable direction must be rejected
    wrong_dir_diff = ("modify_nullable", None, "scripts", "id", {}, False, True)
    assert is_allowed_sqlite_dialect_diff(wrong_dir_diff) is False

    # Unknown table must be rejected
    unknown_table_diff = ("modify_nullable", None, "evil_table", "id", {}, True, False)
    assert is_allowed_sqlite_dialect_diff(unknown_table_diff) is False

    # Column drift like missing metadata_json must always be rejected
    missing_col_diff = ("add_column", None, "scripts", Base.metadata.tables["scripts"].c.metadata_json)
    assert is_allowed_sqlite_dialect_diff(missing_col_diff) is False

    # Anonymous UniqueConstraint on source_videos.url is allowed; named or other columns rejected
    sv_table = Base.metadata.tables["source_videos"]
    anon_url_uc = UniqueConstraint(sv_table.c.url)
    assert is_allowed_sqlite_dialect_diff(("add_constraint", anon_url_uc)) is True

    named_uc = UniqueConstraint(sv_table.c.url, name="uq_custom")
    assert is_allowed_sqlite_dialect_diff(("add_constraint", named_uc)) is False
