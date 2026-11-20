---
phase: "15"
slug: "database-schema-integrity-postgresql-migration-tests"
verified: "2026-11-20"
status: passed
score: "5/5 requirements verified"
---

# Phase 15 Verification Report: Database Schema Integrity & PostgreSQL Migration Tests

## 1. Goal & Scope Check

**Phase Goal:** Corrigir o schema drift do banco de dados, implementar migração incremental isolada mantendo imutabilidade de `001`, refatorar `alembic/env.py` para injeção de conexão e validar migrações com PostgreSQL real e SQLite.

**Escopo estrito cumprido (D-06):** Nenhuma coluna da Phase 16 (`Asset.status`, colunas de leasing em `SourceVideo`) foi introduzida.

---

## 2. Requirements Verification Matrix (`MIGR-01` a `MIGR-05`)

| Requirement | Descrição | Evidência Diretamente Observada | Status |
|---|---|---|:---:|
| **MIGR-01** | Migração incremental `002` adicionando `scripts.metadata_json` (`JSON`, `nullable=True`) mantendo `001` imutável | `alembic/versions/002_add_metadata_json_to_scripts.py` criado (`revision = "002"`, `down_revision = "001"`); SHA-256 de `alembic/versions/001_initial_schema.py` verificado inalterado (`74E2BA97B1A7FA72F56FEF92CFA97617B82F78EEC71A52F739BAE47744D052EF`); `test_migration_002_upgrade_and_downgrade` PASSED | ✅ PASSED |
| **MIGR-02** | Refatoração de `alembic/env.py` para injeção dinâmica de conexão e URL configurável | `alembic/env.py` atualizado com `get_url()`, `do_run_migrations()`, checagem de `context.config.attributes.get("connection")` em `run_migrations_online()` e `connectable.dispose()` em `finally`; `test_alembic_env_connection_injection` PASSED | ✅ PASSED |
| **MIGR-03** | Ciclo completo de migrações (`base -> head`, `001 -> 002` com dados legados e novos, round-trip `head -> 001 -> base -> head`) | `test_upgrade_clean_database_to_head`, `test_incremental_migration_001_to_002_and_data_integrity` e `test_migration_roundtrip_cycle` executados e aprovados em `tests/test_migrations.py` | ✅ PASSED |
| **MIGR-04** | Detecção automatizada de schema drift via `compare_metadata(mc, Base.metadata)` | `test_schema_no_drift_compare_metadata` PASSED (allowlist restritiva SQLite validada negativamente em `test_sqlite_dialect_diff_allowlist_is_strict`; zero drift em `scripts.metadata_json`) e asserção estrita `diff == []` no caminho PostgreSQL em `test_postgres_real_migration_and_strict_zero_drift` | ✅ PASSED |
| **MIGR-05** | Suporte dual-engine (SQLite local isolado + PostgreSQL 16 obrigatório em CI sem skip) | `alembic_config_sqlite` (tmp_path + dispose) e `.github/workflows/ci.yml` validado (serviço `postgres:16`, healthcheck `pg_isready -U postgres`, `CI: "true"`, `TEST_DATABASE_URL`, `ALLOW_DESTRUCTIVE_TEST_DATABASE: "true"`, `pip install -e ".[dev]"`). Nota de ambiente local: `test_postgres_real_migration_and_strict_zero_drift` executou skip seguro local pois `TEST_DATABASE_URL` não foi configurada contra instância local; todos os ramos de falha no CI (`pytest.fail`) e skip local (`pytest.skip`) com isolamento pré-engine foram comprovados via `test_get_verified_test_db_url_security_guards` e `test_postgres_test_fail_closed_in_ci_and_skip_locally` | ✅ PASSED |

---

## 3. Evidências Automatizadas Executadas Após a Última Edição

- `.venv\Scripts\pytest.exe -vv tests/test_migrations.py`: **`9 passed, 1 skipped in 2.49s`** (0 falhas).
- `.venv\Scripts\pytest.exe -q`: **`187 passed, 1 skipped in 73.55s`** (0 falhas; 100% da suíte de regressão do repositório aprovada).
- Validação estática YAML de `.github/workflows/ci.yml`: **PASSED** (`postgres:16`, porta `5432:5432`, `pg_isready -U postgres`, `ALLOW_DESTRUCTIVE_TEST_DATABASE == 'true'`, `pip install -e ".[dev]"` determinístico sem fallback silencioso).
- Verificação criptográfica de imutabilidade:
  - `alembic/versions/001_initial_schema.py` SHA-256 = `74E2BA97B1A7FA72F56FEF92CFA97617B82F78EEC71A52F739BAE47744D052EF` (100% idêntico ao baseline).

---

## 4. Conclusão

Todos os requisitos (`MIGR-01` a `MIGR-05`), critérios de aceitação das 4 tarefas do plano `15-01` e requisitos de segurança ASVS Nível 1 (`15-SECURITY.md`) estão cumpridos e verificados. Status final da Phase 15: **PASSED**.
