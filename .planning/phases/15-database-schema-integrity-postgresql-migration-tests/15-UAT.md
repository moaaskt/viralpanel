---
status: complete
phase: 15-database-schema-integrity-postgresql-migration-tests
source: 15-01-SUMMARY.md
started: 2026-11-20T03:27:00Z
updated: 2026-11-20T04:14:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Migração Limpa, Injeção de Conexão e Imutabilidade da Revisão 001
expected: Em `alembic/env.py` e `alembic/versions/002_add_metadata_json_to_scripts.py`, a migração inicial `001_initial_schema.py` permanece 100% imutável (SHA-256 `74E2BA97B1A7FA72F56FEF92CFA97617B82F78EEC71A52F739BAE47744D052EF`), `alembic/env.py` aceita conexões/URLs injetadas sem tocar no banco de produção, e a migração `002` cria e remove `scripts.metadata_json` (`JSON`, `nullable=True`) em banco limpo (`test_alembic_env_connection_injection`, `test_migration_002_upgrade_and_downgrade` e `test_upgrade_clean_database_to_head` passando).
result: pass

### 2. Integridade de Dados Legados, Round-Trip Completo e Zero Drift
expected: A subida incremental `001 -> 002` preserva registros legados em `scripts` com `metadata_json = None` e grava/lê novos payloads JSON, o ciclo round-trip completo (`base -> head -> 001 -> base -> head`) não deixa tabelas órfãs e `compare_metadata()` aprova sem divergências fora da allowlist restritiva do SQLite (`test_incremental_migration_001_to_002_and_data_integrity`, `test_migration_roundtrip_cycle`, `test_schema_no_drift_compare_metadata` e `test_sqlite_dialect_diff_allowlist_is_strict` passando).
result: pass

### 3. Isolamento Fail-Closed de Banco de Teste PostgreSQL
expected: Sem `TEST_DATABASE_URL` local, `test_postgres_real_migration_and_strict_zero_drift` emite skip informativo sem abrir conexão ou tocar no banco `viralpanel`; os guardas de segurança rejeitam qualquer banco diferente de `viralpanel_test`, bloqueiam hosts remotos sem `ALLOW_REMOTE_TEST_DATABASE=true`, preservam a senha sem mascarar com `***`, e falham o build (`pytest.fail`) em modo `CI=true` caso falte `ALLOW_DESTRUCTIVE_TEST_DATABASE=true` antes de criar engine (`test_get_verified_test_db_url_security_guards` e `test_postgres_test_fail_closed_in_ci_and_skip_locally` passando).
result: pass

### 4. Workflow de CI GitHub Actions e Regressão Global
expected: O arquivo `.github/workflows/ci.yml` provisiona o serviço `postgres:16` com healthcheck `pg_isready -U postgres`, define `CI: "true"`, `TEST_DATABASE_URL` para `viralpanel_test` e `ALLOW_DESTRUCTIVE_TEST_DATABASE: "true"`, instala dependências de forma determinística única via `pip install -e ".[dev]"` (sem fallback silencioso para `requirements.txt`), executa obrigatoriamente `pytest -vv tests/test_migrations.py` e `pytest -q`, e a suíte global do repositório passa sem regressões (`187 passed, 1 skipped`).
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
