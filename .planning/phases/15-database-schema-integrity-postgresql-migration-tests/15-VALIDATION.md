---
phase: "15"
slug: "database-schema-integrity-postgresql-migration-tests"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-11-14"
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.2.0 / SQLAlchemy 2.0+ / Alembic 1.13+ / PyYAML |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv\Scripts\pytest.exe -q tests/test_migrations.py` |
| **Full suite command** | `.venv\Scripts\pytest.exe -q` |
| **Estimated runtime** | ~5s (migrations suite) / ~35s (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `.venv\Scripts\pytest.exe -q tests/test_migrations.py`
- **After every plan wave:** Run `.venv\Scripts\pytest.exe -q`
- **Before `/gsd-verify-work`:** Full suite must be green (117+ tests passed)
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | MIGR-02 | T-15-01 | Previne injeção não autorizada de DDL validando conexão e URL controladas | unit | `.venv\Scripts\pytest.exe tests/test_migrations.py -k "test_alembic_env_connection_injection"` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | MIGR-01 | T-15-02 | Imutabilidade da migração 001 e idempotência do downgrade 002 | migration | `.venv\Scripts\pytest.exe tests/test_migrations.py -k "test_migration_002_upgrade_and_downgrade"` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | MIGR-03, MIGR-04, MIGR-05 | T-15-03 | Ciclo round-trip completo (head->001->base->head), integridade de dados legados e novos, zero drift sem filtros no PostgreSQL e teste não-skippable em CI | integration | `.venv\Scripts\pytest.exe tests/test_migrations.py` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | MIGR-05 | T-15-03 | Configuração de CI com PostgreSQL 16 obrigatório, TEST_DATABASE_URL e execução de migrações sem bypass | config | `.venv\Scripts\python.exe -c "import yaml; data = yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); svc = data['jobs']['test']['services']['postgres']; assert 'postgres:16' in svc['image']; assert '5432:5432' in svc['ports']; assert 'TEST_DATABASE_URL' in data['jobs']['test']['env']; print('CI workflow valid')"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_migrations.py` — Stubs e harness de testes de migração e schema drift
- [ ] `alembic/versions/002_add_metadata_json_to_scripts.py` — Arquivo de migração incremental
- [ ] `.github/workflows/ci.yml` — Workflow de CI com serviço PostgreSQL 16 obrigatório

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| N/A | N/A | Todos os comportamentos da Phase 15 possuem verificação 100% automatizada | N/A |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified
