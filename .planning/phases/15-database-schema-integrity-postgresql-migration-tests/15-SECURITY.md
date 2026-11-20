---
phase: "15"
slug: "database-schema-integrity-postgresql-migration-tests"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-20"
---

# Phase 15 — Security (`15-SECURITY.md`)

> Per-phase security contract: threat register, accepted risks, and audit trail (ASVS Level 1).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Alembic Configuration & URL Resolution Boundary (`alembic/env.py`) | Seleção dinâmica da URL de banco ou conexão injetada pelo executor/pytest | `sqlalchemy.url`, `context.config.attributes["connection"]` |
| Migration DDL Lifecycle Boundary (`alembic/versions/`) | Execução declarativa de `upgrade()` / `downgrade()` preservando histórico versionado | Esquema DDL (`scripts.metadata_json`) e tabela `alembic_version` |
| Destructive Test Isolation Boundary (`tests/test_migrations.py`) | Isolamento estrito entre bancos operacionais e banco de teste descartável `viralpanel_test` | `TEST_DATABASE_URL`, `ALLOW_DESTRUCTIVE_TEST_DATABASE`, `ALLOW_REMOTE_TEST_DATABASE`, `CI` |
| Continuous Integration Execution Boundary (`.github/workflows/ci.yml`) | Provisionamento de serviço `postgres:16` efêmero e instalação determinística de dependências | Variáveis de ambiente de CI, pacotes `pyproject.toml` `[dev]` |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation & Code Verification | Status |
|---|---|---|---|---|---|---|
| **T-15-01** | Injeção de DDL / Parâmetros não validados (ASVS 5.3.4) | `alembic/env.py`, `alembic/versions/002_add_metadata_json_to_scripts.py` | high | mitigate | `alembic/env.py#get_url` prioriza `context.config.get_main_option("sqlalchemy.url")` e `do_run_migrations` executa sob `context.begin_transaction()`. A revisão `002` utiliza exclusivamente primitivas tipadas `op.add_column`/`op.drop_column` sem SQL interpolado. Verificado por `test_alembic_env_connection_injection` e `test_migration_002_upgrade_and_downgrade`. | closed |
| **T-15-02** | Corrupção de histórico / Reversibilidade destrutiva (ASVS 1.14.1) | `alembic/versions/001_initial_schema.py`, `alembic/versions/002_add_metadata_json_to_scripts.py` | high | mitigate | `001_initial_schema.py` mantido 100% imutável (SHA-256 `74E2BA97B1A7FA72F56FEF92CFA97617B82F78EEC71A52F739BAE47744D052EF`). `002` possui `down_revision = "001"` e `downgrade()` simétrico (`op.drop_column`). Ciclo `head -> 001 -> base -> head` e integridade de registros legados comprovados em `tests/test_migrations.py`. | closed |
| **T-15-03** | Schema Drift silencioso e bypass de CI/CD (ASVS 1.14.2) | `tests/test_migrations.py`, `.github/workflows/ci.yml` | high | mitigate | `compare_metadata()` exigido com allowlist restritiva validada no SQLite (`is_allowed_sqlite_dialect_diff` testada negativamente contra `add_column` e colunas não-PK) e zero filtros (`diff == []`) no PostgreSQL. CI provisiona `postgres:16` com healthcheck `pg_isready -U postgres`, instalação determinística `pip install -e ".[dev]"` sem fallback silencioso, e falha com `pytest.fail()` se o banco não responder. | closed |
| **T-15-04** | Contaminação ou destruição do banco de aplicação por testes (ASVS 1.14.5 / 5.3.4) | `tests/test_migrations.py#test_postgres_real_migration_and_strict_zero_drift` | critical | mitigate | Consumo exclusivo de `TEST_DATABASE_URL` (zero fallback para `DATABASE_URL`/`get_settings()`), banco obrigatoriamente `viralpanel_test`, host restrito a `SAFE_LOCAL_HOSTS` (local e CI sem bypass; remoto exige `ALLOW_REMOTE_TEST_DATABASE == 'true'`), autorização explícita `ALLOW_DESTRUCTIVE_TEST_DATABASE == 'true'` antes de `create_engine`/socket, e asserção em runtime de `SELECT current_database() == 'viralpanel_test'`. Comprovado por `test_get_verified_test_db_url_security_guards` e `test_postgres_test_fail_closed_in_ci_and_skip_locally` com `create_engine` bloqueado via monkeypatch. | closed |

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

- `2026-11-20`: Auditoria de código e validação automatizada executadas na conclusão da Phase 15 (`tests/test_migrations.py`: 9 passed, 1 skipped local; suíte global: 187 passed, 1 skipped). Todas as 4 ameaças (`T-15-01` a `T-15-04`) encerradas (`threats_open: 0`).
