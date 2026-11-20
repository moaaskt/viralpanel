---
phase: "15"
plan: "01"
subsystem: "database"
type: "architecture"
status: "complete"
date: "2026-11-20"
commit: "none (per user governance constraint)"
requirements:
  - MIGR-01
  - MIGR-02
  - MIGR-03
  - MIGR-04
  - MIGR-05
key-files:
  created:
    - "alembic/versions/002_add_metadata_json_to_scripts.py"
    - "tests/test_migrations.py"
    - ".github/workflows/ci.yml"
  modified:
    - "alembic/env.py"
---

# Phase 15 Plan 01 Summary: Database Schema Integrity & PostgreSQL Migration Tests

## 1. Visão Geral

O Plano 15-01 eliminou o schema drift estrutural da coluna `scripts.metadata_json` (Finding F-01), desacoplou o ambiente de execução do Alembic para aceitar injeção de conexões e URLs dinâmicas, implementou uma suíte dual-engine de ciclo completo e detecção automática de drift (`tests/test_migrations.py`) com isolamento fail-closed, e configurou o workflow de Integração Continua no GitHub Actions (`.github/workflows/ci.yml`) com serviço obrigatório PostgreSQL 16.

## 2. Tarefas Executadas e Entregas

### Task 1: Refatoração de `alembic/env.py` para Injeção de Conexão e URLs Dinâmicas (`MIGR-02`)
- Removida a avaliação imediata no nível do módulo `url = get_settings().database_url`.
- Implementadas as funções `get_url()` (priorizando `context.config.get_main_option("sqlalchemy.url")` com fallback exclusivo em runtime normal) e `do_run_migrations(connection)` (`compare_type=True` + `context.begin_transaction()`).
- Atualizado `run_migrations_online()` para consumir conexões injetadas via `context.config.attributes.get("connection", None)` e descartar engines temporárias via `try ... finally: connectable.dispose()`.
- Atualizado `run_migrations_offline()` para utilizar `get_url()`.
- Validado com `test_alembic_env_connection_injection`: **PASSED**.

### Task 2: Criação da Migração Incremental `002_add_metadata_json_to_scripts.py` (`MIGR-01`)
- Criada revisão isolada `revision = "002"` encadeada em `down_revision = "001"`:
  - `upgrade()`: `op.add_column("scripts", sa.Column("metadata_json", sa.JSON(), nullable=True))`
  - `downgrade()`: `op.drop_column("scripts", "metadata_json")`
- **Imutabilidade de `001_initial_schema.py` comprovada:** hash SHA-256 preservado integralmente (`74E2BA97B1A7FA72F56FEF92CFA97617B82F78EEC71A52F739BAE47744D052EF`).
- Validado com `test_migration_002_upgrade_and_downgrade`: **PASSED**.

### Task 3: Suíte Dual-Engine `tests/test_migrations.py`, Round-Trip e Segurança Fail-Closed (`MIGR-03`, `MIGR-04`, `MIGR-05`)
- Implementados os 7 testes previstos no plano além de 3 testes unitários de prova dos guardas de segurança e da allowlist SQLite (total de 10 testes no módulo):
  - `test_alembic_env_connection_injection`, `test_migration_002_upgrade_and_downgrade`, `test_upgrade_clean_database_to_head`, `test_incremental_migration_001_to_002_and_data_integrity`, `test_migration_roundtrip_cycle` (`base -> head -> 001 -> base -> head`), `test_schema_no_drift_compare_metadata`.
  - `test_postgres_real_migration_and_strict_zero_drift`: validação fail-closed estrita em 4 etapas (presença exclusiva de `TEST_DATABASE_URL`, validação `viralpanel_test` + `SAFE_LOCAL_HOSTS`, autorização destrutiva explícita `ALLOW_DESTRUCTIVE_TEST_DATABASE == 'true'` antes de criar qualquer engine/socket, conectividade + asserção `SELECT current_database() == 'viralpanel_test'`), ciclo `downgrade base -> upgrade head` e `assert diff == []` sem filtros.
  - Testes unitários sem banco real: `test_get_verified_test_db_url_security_guards`, `test_postgres_test_fail_closed_in_ci_and_skip_locally`, `test_sqlite_dialect_diff_allowlist_is_strict`.

### Task 4: Workflow de CI no GitHub Actions (`.github/workflows/ci.yml`) (`MIGR-05`)
- Configurado serviço container `postgres:16` (`POSTGRES_USER: postgres`, `POSTGRES_PASSWORD: postgres`, `POSTGRES_DB: viralpanel_test`, porta `5432:5432`, healthcheck `--health-cmd "pg_isready -U postgres"`).
- Configuradas variáveis `CI: "true"`, `TEST_DATABASE_URL` apontando para `viralpanel_test` e `ALLOW_DESTRUCTIVE_TEST_DATABASE: "true"`.
- Instalação determinística única baseada em `pyproject.toml`: `python -m pip install --upgrade pip` e `pip install -e ".[dev]"` (sem fallback silencioso para `requirements.txt`).
- Execução mandatória de `pytest -vv tests/test_migrations.py` e `pytest -q`.

## 3. Correções Técnicas Aplicadas Sobre Exemplos do `15-RESEARCH.md`

Durante a implementação, foram corrigidas armadilhas reais detectadas na revisão técnica:
1. **Preservação de senha em `make_url`:** Em SQLAlchemy 2.x (`2.1.8`), `str(make_url(...))` mascara a senha como `***`, o que causaria falha de autenticação no PostgreSQL do CI. `get_verified_test_db_url()` utiliza `parsed.render_as_string(hide_password=False)` e escape `% -> %%` em `cfg.set_main_option`.
2. **Imports completos e registro ORM explícito:** Adicionado `from typing import Any` (ausente no snippet da pesquisa) e `from viralpanel import models  # noqa: F401` garantindo povoamento completo de `Base.metadata.tables`.
3. **Limpeza determinística e suporte IPv6:** Substituído `socket.socket(AF_INET)` por `with socket.create_connection((host, port), timeout=0.8):` e encapsulamento `try ... finally: engine.dispose()`.
4. **Desempacotamento de diffs no `metadata_json_diffs`:** Aplicado `_unwrap_diff_item(d)` antes de inspecionar índices de tuplas no SQLite.

## 4. Resultados Reais dos Testes

- **`tests/test_migrations.py`:** `9 passed, 1 skipped in 2.49s` (skip local esperado em `test_postgres_real_migration_and_strict_zero_drift` por ausência intencional de `TEST_DATABASE_URL` em dev local sem banco descartável).
- **Suíte Global do Repositório (`.venv\Scripts\pytest.exe -q`):** **`187 passed, 1 skipped in 73.55s`** (zero falhas; todos os 178 testes pré-existentes + 9 novos testes passando).
- **Validação YAML do CI:** Sintaxe, serviço `postgres:16`, `pg_isready -U postgres`, `ALLOW_DESTRUCTIVE_TEST_DATABASE == 'true'` e instalação determinística `.[dev]` validados com exit code 0.
- **Governança Git:** Nenhum commit automático criado (`git HEAD` preservado em `ab17255`).
