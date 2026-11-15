# Phase 15: Database Schema Integrity & PostgreSQL Migration Tests - Research
**Researched:** 2026-11-14  
**Domain:** Database Schema Integrity, Alembic Migrations, PostgreSQL 16 & SQLite Dual-Engine Testing, Schema Drift Detection via `compare_metadata`  
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from ANALYZER 04/05/06 & Blueprint)

### Locked Decisions
- **D-01 (Imutabilidade da Revisão 001):** A migração inicial `alembic/versions/001_initial_schema.py` é estritamente imutável. Quaisquer alterações de schema devem ser aplicadas através de migrações incrementais versionadas. [VERIFIED: ANALYZER-04:67-70]
- **D-02 (Migração Incremental 002):** A resolução do schema drift identificado no Finding F-01 (`scripts.metadata_json`) deve ser realizada criando a migração `alembic/versions/002_add_metadata_json_to_scripts.py`, com `down_revision = '001'`, implementando `upgrade()` com `op.add_column` e `downgrade()` com `op.drop_column`. [VERIFIED: ANALYZER-04:49,69]
- **D-03 (Desacoplamento do Alembic env.py):** `alembic/env.py` deve ser refatorado cirurgicamente para suportar conexões injetadas via `context.config.attributes.get('connection')` e URL configurável via `context.config.get_main_option('sqlalchemy.url')` ou `TEST_DATABASE_URL`, eliminando a dependência rígida de `create_engine(get_settings().database_url)` em tempo de importação e execução. [VERIFIED: alembic/env.py:9,19]
- **D-04 (Harness de Testes e Ciclo Completo de Migração):** Criação de `tests/test_migrations.py` cobrindo o ciclo completo de migrações:
  1. Subida limpa da base até `head` (`upgrade head`).
  2. Subida incremental de `001` até `head` (`002`), com asserção estrita de preservação e integridade de dados legados (registros pré-existentes mantêm `metadata_json = None`) e inserção de novos registros com JSON estruturado.
  3. Ciclo completo round-trip: `head → 001 → base → head`, assegurando que o downgrade não deixa tabelas ou versões órfãs e que re-aplicar o upgrade do zero restaura o schema completo sem erros.
  4. Detecção automatizada de schema drift: no SQLite, filtros estritamente documentados apenas para divergências conhecidas de dialeto; no PostgreSQL, asserção estrita `assert diff == []` sem nenhum filtro que mascare divergências. [VERIFIED: ANALYZER-04:70,196-200]
- **D-05 (Estratégia Dual-Engine e PostgreSQL Obrigatório no CI):** 
  1. No ambiente de CI (`CI=true` ou `GITHUB_ACTIONS=true`), o PostgreSQL 16 é OBRIGATÓRIO. O teste contra PostgreSQL real NUNCA pode ser ignorado ou pulado (skip proibido no CI; falha obrigatória do build com `pytest.fail()` se o PostgreSQL não estiver disponível).
  2. A execução condicional com skip de PostgreSQL é restrita exclusivamente ao ambiente local de desenvolvimento quando não houver instância respondendo na porta 5432.
  3. Configuração de workflow formal de CI (`.github/workflows/ci.yml`) com serviço `postgres:16`, container healthcheck (`pg_isready`), porta 5432 mapeada, variável `TEST_DATABASE_URL` e execução obrigatória dos testes de migração e da suíte completa. [VERIFIED: user_instructions]
- **D-06 (Fronteira Estrita de Escopo da Phase 15):** A migração `003` (`Asset.status`) e os campos de concorrência/lease de `SourceVideo` pertencem exclusivamente à Phase 16 (Concorrência, Fencing & Lifecycle). A Phase 15 mantém foco estrito e cirúrgico na resolução do drift de `Script.metadata_json`, na homologação da infraestrutura de testes de migração e no workflow de CI com PostgreSQL 16. [VERIFIED: user_instructions, ANALYZER-04:195-200]

### the agent's Discretion
- Tratamento de divergências de reflexão de tipos do SQLite (ex: nullability de chaves primárias e constraints anônimas) no teste de `compare_metadata()`.
- Estrutura de fixtures de isolamento e detecção automática de conectividade PostgreSQL em `tests/test_migrations.py`.
- Formatação dos tipos DDL para máxima portabilidade PostgreSQL 16 / SQLite 3.35+.

### Deferred Ideas (OUT OF SCOPE)
- Migração `003_add_status_to_assets.py` e colunas de leasing (`reservation_token`, `lease_expires_at`) → Phase 16.
- Atualização do schema da API REST (`ScriptSchema`) para expor `factual_claims` → Phase 18.
- Criação de containers Docker ephemeral via testcontainers → Fora do escopo (usar PostgreSQL local se ativo ou SQLite isolado).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Apoio da Pesquisa / Implementação |
|----|-----------|-----------------------------------|
| **MIGR-01** | Resolução do Schema Drift `scripts.metadata_json` no Alembic sem alterar a migração 001. | Criação de `alembic/versions/002_add_metadata_json_to_scripts.py` (`down_revision = "001"`). [VERIFIED: models.py:43, 001_initial_schema.py:32-40] |
| **MIGR-02** | Refatoração de `alembic/env.py` para permitir injeção de conexão e URL dinâmica de testes. | Adição de leitura de `attributes["connection"]` e `config.get_main_option("sqlalchemy.url")` em `run_migrations_online()` e `run_migrations_offline()`. [VERIFIED: alembic/env.py:9,19] |
| **MIGR-03** | Ciclo completo de testes de migração (Clean Upgrade, Incremental Upgrade, Downgrade e Integridade de Dados). | Implementação de testes automatizados em `tests/test_migrations.py` usando `alembic.command`. [VERIFIED: tests/test_models.py:10] |
| **MIGR-04** | Detecção automatizada de Schema Drift via `compare_metadata()`. | Verificação programática com `alembic.autogenerate.compare_metadata` garantindo paridade total entre `Base.metadata` e o banco migrado. [VERIFIED: alembic.autogenerate] |
| **MIGR-05** | Suporte transparente a execução local (SQLite isolado) e homologação PostgreSQL real (quando disponível). | Fixture de detecção de PostgreSQL com fallback para banco SQLite temporário em disco (`tmp_path`), garantindo CI/CD verde em qualquer ambiente. [VERIFIED: pytest suite] |
</phase_requirements>

---

<architectural_responsibility_map>
## Architectural Responsibility Map

| Componente | Responsabilidade Primária | Dependências Críticas |
|---|---|---|
| `alembic/versions/002_add_metadata_json_to_scripts.py` | Adicionar a coluna `metadata_json` (JSON, nullable=True) na tabela `scripts` no `upgrade()` e removê-la no `downgrade()`. | `001_initial_schema.py` |
| `alembic/env.py` | Orquestrar o runtime do Alembic, respeitando conexões injetadas em memória/transação por testes e URLs configuradas. | `viralpanel.config.get_settings`, `viralpanel.database.Base` |
| `tests/test_migrations.py` | Suíte de testes automatizados de ciclo de vida de migrações, rollback e verificação de schema drift. | `alembic.command`, `alembic.autogenerate.compare_metadata`, `viralpanel.models` |
| `src/viralpanel/models.py` | Modelo de dados declarativo SQLAlchemy 2.0 (`Script.metadata_json: Mapped[dict | None]`). | `viralpanel.database.Base` |
| `src/viralpanel/scripting/service.py` | Consumidor da coluna `metadata_json` para persistir `factual_claims`, `closing_thought` e `cta`. | `viralpanel.models.Script` |
</architectural_responsibility_map>

---

<research_summary>
## Summary

A Phase 15 resolve a vulnerabilidade crítica **F-01** (P0 - Schema Drift Bloqueante no PostgreSQL) identificada no Blueprint de Remediação. 

Atualmente, o modelo `Script` em `src/viralpanel/models.py` declara a coluna `metadata_json` [VERIFIED: src/viralpanel/models.py:43], e o serviço `ScriptingService` grava nela assiduamente os metadados editoriais gerados pelo Gemini 2.5 Flash [VERIFIED: src/viralpanel/scripting/service.py:79]. No entanto, a migração inicial `001_initial_schema.py` do Alembic **não possui** essa coluna [VERIFIED: alembic/versions/001_initial_schema.py:32-40]. 

Essa discrepância nunca foi detectada pelos testes automatizados existentes porque toda a suíte de testes do repositório utiliza SQLite com `Base.metadata.create_all()` [VERIFIED: tests/test_models.py:10], ignorando totalmente as migrações do Alembic. Como consequência, qualquer tentativa de subir o banco em produção via `alembic upgrade head` contra um PostgreSQL limpo resulta em uma tabela `scripts` defasada, causando falha imediata em tempo de execução ao tentar inserir ou consultar roteiros (`UndefinedColumn: column scripts.metadata_json does not exist`).

Adicionalmente, `alembic/env.py` possui acoplamento rígido com a URL de produção retornada por `get_settings().database_url` [VERIFIED: alembic/env.py:9,19], impedindo a injeção de conexões de teste e inviabilizando testes automatizados de migração em ambientes isolados.

A estratégia estabelecida para a Phase 15 abrange:
1. **Preservar a imutabilidade de `001_initial_schema.py`** e introduzir a migração incremental `002_add_metadata_json_to_scripts.py`.
2. **Refatorar cirurgicamente `alembic/env.py`** para aceitar conexões pré-estabelecidas via `context.config.attributes['connection']` e URL dinâmica via `context.config.get_main_option('sqlalchemy.url')`.
3. **Construir `tests/test_migrations.py`**, executando testes exaustivos de subida limpa, subida incremental com verificação de persistência de dados, downgrade e drift detection com `compare_metadata()`.
4. **Viabilizar execução dual:** testes rápidos e isolados rodando via SQLite em qualquer máquina local, com suporte a testes estritos contra PostgreSQL quando uma instância estiver disponível.
</research_summary>

---

## Standard Stack

| Camada / Tecnologia | Versão Homologada | Função no Projeto |
|---|---|---|
| **SQLAlchemy** | `2.1.8` (SQLAlchemy 2.0+) [VERIFIED: pip list] | ORM e Core relacional, mapeamento declarativo (`Mapped`, `mapped_column`) e reflexão de metadados. |
| **Alembic** | `1.20.1` (Alembic 1.13+) [VERIFIED: pip list] | Ferramenta de migrações DDL versionadas, suporte a `op.batch_alter_table` e inspeção de drift via `compare_metadata`. |
| **PostgreSQL Driver** | `psycopg2-binary 2.9.13` [VERIFIED: pip list] | Conector binário para PostgreSQL 16 (produção e testes de integração). |
| **SQLite** | `3.50.4` (embutido no Python 3.12/3.14) [VERIFIED: sqlite3.sqlite_version] | Motor relacional local para testes rápidos, isolados e sem dependências de infraestrutura de rede. |
| **pytest** | `9.2.0` [VERIFIED: pytest execution] | Framework de asserção e orquestração de testes automatizados. |

---

## Architecture Patterns

### 1. Injeção de Conexão no `alembic/env.py` (IoC Pattern)
Por padrão, o arquivo `env.py` do Alembic cria sua própria engine conectando-se à URL do banco. Para permitir que o framework de testes controle a transação e o ciclo de vida do banco (por exemplo, usando uma conexão isolada ou banco SQLite temporário), `env.py` deve consultar `context.config.attributes.get("connection")`.

```
[Pytest Fixture] ──(cria engine/conexão)──> [Config.attributes['connection']]
                                                          │
                                                          ▼
                                            [alembic/env.py: run_migrations_online]
                                                          │
                                           (utiliza conexão injetada diretamente,
                                            sem abrir novas conexões de rede)
```

### 2. Migração Incremental Imutável (001 -> 002)
Seguindo as melhores práticas de engenharia de banco de dados, migrações já versionadas ou executadas em outros ambientes nunca devem ser alteradas retrospectivamente. A migração `002_add_metadata_json_to_scripts.py` conecta-se à cadeia:
- `revision: str = "002"`
- `down_revision: Union[str, None] = "001"`
- `upgrade()`: `op.add_column("scripts", sa.Column("metadata_json", sa.JSON(), nullable=True))`
- `downgrade()`: `op.drop_column("scripts", "metadata_json")`

### 3. Detecção Automatizada de Schema Drift via `compare_metadata()`
Em vez de inspecionar tabelas manualmente ou escrever verificações ad-hoc, utiliza-se a API nativa do Alembic:
```python
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

mc = MigrationContext.configure(connection)
diff = compare_metadata(mc, Base.metadata)
```
Essa chamada reflete o catálogo do banco real através da conexão ativa e compara cada tabela, coluna, tipo, índice e constraint contra o `Base.metadata` declarado nos modelos Python.

### 4. Estratégia Dual de Ambientes (Local Resiliente + CI/PostgreSQL Estrito)
- **Local (SQLite Temporário via `tmp_path`):** Permite que qualquer desenvolvedor execute `pytest tests/test_migrations.py` sem exigir Docker ou serviços ativos. Valida o fluxo DDL completo (001 -> 002 -> downgrade -> base).
- **PostgreSQL Real (localhost:5432 ou CI):** Detecta dinamicamente a presença de uma instância PostgreSQL. Se ativa, executa a suíte contra PostgreSQL, validando JSON nativo, triggers, índices e garantindo `diff == []` estrito.

---

## Don't Hand-Roll

| O que NÃO fazer | O que usar em vez disso | Por que? |
|---|---|---|
| **NÃO fazer diff manual de colunas via queries SQL customizadas** (`SELECT column_name FROM information_schema.columns...`) | `alembic.autogenerate.compare_metadata(mc, Base.metadata)` | A função nativa do Alembic inspeciona tipos, chaves estrangeiras, índices e nulabilidade automaticamente para qualquer dialeto suportado. |
| **NÃO alterar a migração 001_initial_schema.py** | Criar migração incremental `002_add_metadata_json_to_scripts.py` | Modificar revisões históricas quebra o hash/ID de ambientes que já aplicaram a versão 001, causando erro de inconsistência no `alembic_version`. |
| **NÃO criar tabelas nos testes usando `Base.metadata.create_all()`** na suíte de migração | `alembic.command.upgrade(cfg, "head")` | `create_all()` ignora as migrações e mascara discrepâncias entre o ORM e os scripts DDL (a causa exata do bug F-01). |
| **NÃO hardcodar URLs de conexão no `alembic/env.py`** | Resolver dinamicamente via `context.config.attributes.get("connection")` -> `config.get_main_option("sqlalchemy.url")` -> `get_settings().database_url` | Permite que testes injetem bancos isolados sem sujar ou depender da base de desenvolvimento/produção. |
| **NÃO omitir o método `downgrade()`** na migração 002 | Implementar `op.drop_column("scripts", "metadata_json")` | Sem `downgrade()`, é impossível realizar rollbacks seguros em caso de falha de deployment ou testes de rollback. |

---

## Common Pitfalls

### 1. Hardcoded URL em `alembic/env.py`
- **Sintoma:** Executar `command.upgrade(cfg, "head")` em testes sempre falha com `psycopg2.OperationalError: connection to localhost:5432 failed`, mesmo configurando `cfg.set_main_option("sqlalchemy.url", "sqlite:///...")`. [VERIFIED: in-repo test]
- **Causa:** Linha 9 e 19 de `alembic/env.py` executavam `url = get_settings().database_url` e `engine = create_engine(url)` ignorando as opções passadas na `Config`.
- **Mitigação:** Implementar a função `get_url()` com fallback em cascata e checar `context.config.attributes.get("connection")`.

### 2. Lock de Arquivo SQLite no Windows (`PermissionError: [WinError 32]`)
- **Sintoma:** Pytest falha na limpeza da fixture temporária com `PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo`. [VERIFIED: in-repo test]
- **Causa:** Conexões SQLite abertas mantêm um file lock no Windows até que o engine seja explicitamente descartado via `engine.dispose()`.
- **Mitigação:** Na fixture de teste, sempre encapsular o fechamento com `connection.close()` e `engine.dispose()` no bloco `finally` ou pós-`yield`.

### 3. Peculiaridades de Reflexão do SQLite em `compare_metadata()`
- **Sintoma:** `compare_metadata()` acusa diferenças espúrias em bancos SQLite migrados (como `modify_nullable` em colunas `id` chave primária e `add_constraint` de constraints anônimas `unique`), mesmo quando o schema está perfeitamente alinhado. [VERIFIED: in-repo test]
- **Causa:** O dialeto de reflexão do SQLite não reflete com 100% de fidelidade a nulabilidade de chaves primárias sem declaração explícita de `NOT NULL`, e não reflete nomes de constraints únicas geradas inline.
- **Mitigação:** No teste rodando contra SQLite, filtrar essas idiossincrasias conhecidas de reflexão do SQLite, focando estritamente em divergências estruturais (`add_column`, `remove_column`, `add_table`, `remove_table`). No PostgreSQL, a asserção é `diff == []` estrito.

### 4. Vazamento Prematuro de Alterações da Phase 16
- **Sintoma:** Tentar adicionar `Asset.status` ou colunas de lease de `SourceVideo` na migração `002`.
- **Causa:** Confusão de escopo entre o Blueprint de Remediação (onde a Phase 15 originalmente agrupava 002 e 003) e as decisões consolidadas pelo Tech Lead.
- **Mitigação:** Manter a Phase 15 focada **exclusivamente** na coluna `scripts.metadata_json` e no harness de testes de migração. `Asset.status` será tratado na Phase 16.

---

## Code Examples

### 1. Refatoração Cirúrgica de `alembic/env.py`

```python
"""Alembic environment configuration with connection injection support."""
from alembic import context
from sqlalchemy import create_engine

from viralpanel import models  # noqa: F401
from viralpanel.config import get_settings
from viralpanel.database import Base

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve a URL do banco em ordem de prioridade:
    1. Opção 'sqlalchemy.url' definida dinamicamente no config
    2. Settings da aplicação (database_url padrão)
    """
    url = context.config.get_main_option("sqlalchemy.url")
    if not url:
        url = get_settings().database_url
    return str(url)


def run_migrations_offline() -> None:
    """Executa migrações no modo offline."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Executa as migrações sobre uma conexão ativa."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações no modo online.
    Prioriza conexão injetada no context.config.attributes (usada por testes).
    Caso contrário, abre uma nova engine a partir da URL resolvida.
    """
    connection = context.config.attributes.get("connection", None)
    if connection is not None:
        do_run_migrations(connection)
    else:
        connectable = create_engine(get_url())
        with connectable.connect() as conn:
            do_run_migrations(conn)
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 2. Migração Incremental `alembic/versions/002_add_metadata_json_to_scripts.py`

```python
"""add metadata_json to scripts

Revision ID: 002
Revises: 001
Create Date: 2026-11-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de revisão do Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona a coluna metadata_json à tabela scripts."""
    op.add_column("scripts", sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove a coluna metadata_json da tabela scripts."""
    op.drop_column("scripts", "metadata_json")
```

### 3. Harness de Testes `tests/test_migrations.py`

```python
"""Testes de integridade de schema e ciclo de migrações Alembic."""
import json
import socket
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from viralpanel.config import get_settings
from viralpanel.database import Base


def is_postgres_available() -> bool:
    """Verifica se há um servidor PostgreSQL respondendo na porta configurada."""
    try:
        url = get_settings().database_url
        # Tenta conectar via socket no host/porta padrão 5432
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.8)
        result = sock.connect_ex(("127.0.0.1", 5432))
        sock.close()
        if result != 0:
            return False
        
        # Valida autenticação rápida
        eng = create_engine(url, connect_args={"connect_timeout": 2})
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


@pytest.fixture
def alembic_config_sqlite(tmp_path):
    """Fixture que fornece configuração Alembic e engine isolada SQLite em disco."""
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)

    ini_path = Path(__file__).parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)

    yield cfg, engine

    engine.dispose()


def test_upgrade_clean_database_to_head(alembic_config_sqlite):
    """Garante que uma base zerada sobe limpa até head e cria todas as colunas."""
    cfg, engine = alembic_config_sqlite

    # Executa upgrade head
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        assert {"source_videos", "scripts", "assets", "publications", "runs"}.issubset(tables)

        # Verifica presença de metadata_json em scripts
        columns = [c["name"] for c in inspector.get_columns("scripts")]
        assert "metadata_json" in columns

        # Valida versão final
        mc = MigrationContext.configure(conn)
        assert mc.get_current_revision() == "002"


def test_incremental_migration_001_to_002_and_data_integrity(alembic_config_sqlite):
    """Valida subida incremental preservando registros pré-existentes."""
    cfg, engine = alembic_config_sqlite

    # 1. Sobe até 001
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "001")

    with engine.connect() as conn:
        inspector = inspect(conn)
        cols_001 = [c["name"] for c in inspector.get_columns("scripts")]
        assert "metadata_json" not in cols_001

        # Insere dados representativos da versão 001
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

    # 2. Aplica migração 002
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "002")

    with engine.connect() as conn:
        inspector = inspect(conn)
        cols_002 = [c["name"] for c in inspector.get_columns("scripts")]
        assert "metadata_json" in cols_002

        # 3. Garante que registro antigo permaneceu intacto com metadata_json nulo
        row = conn.execute(text("SELECT id, script_text, metadata_json FROM scripts WHERE id = 'sc-test-1'")).fetchone()
        assert row is not None
        assert row[0] == "sc-test-1"
        assert row[1] == "roteiro original"
        assert row[2] is None

        # 4. Grava novo script já utilizando metadata_json
        payload = json.dumps({"factual_claims": [{"claim": "Fato testado"}], "closing_thought": "Impacto", "cta": "Siga"})
        conn.execute(
            text(
                "INSERT INTO scripts (id, source_video_id, transcription, script_text, hook, version, created_at, metadata_json) "
                "VALUES ('sc-test-2', 'sv-test-1', 't2', 'r2', 'h2', 2, '2026-11-14 00:01:00', :meta)"
            ),
            {"meta": payload},
        )
        conn.commit()

        row_new = conn.execute(text("SELECT id, metadata_json FROM scripts WHERE id = 'sc-test-2'")).fetchone()
        assert row_new is not None
        assert "factual_claims" in (json.loads(row_new[1]) if isinstance(row_new[1], str) else row_new[1])


def test_migration_roundtrip_cycle(alembic_config_sqlite):
    """Garante que o ciclo completo round-trip (head -> 001 -> base -> head) executa sem resíduos."""
    cfg, engine = alembic_config_sqlite

    # 1. Sobe até head (base -> head)
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    # 2. Reverte para 001 (head -> 001)
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "001")

    with engine.connect() as conn:
        inspector = inspect(conn)
        cols = [c["name"] for c in inspector.get_columns("scripts")]
        assert "metadata_json" not in cols
        mc = MigrationContext.configure(conn)
        assert mc.get_current_revision() == "001"

    # 3. Reverte para base (001 -> base)
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")

    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = [t for t in inspector.get_table_names() if t != "alembic_version"]
        assert len(tables) == 0
        mc = MigrationContext.configure(conn)
        assert mc.get_current_revision() is None

    # 4. Re-aplica upgrade até head (base -> head)
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        assert {"source_videos", "scripts", "assets", "publications", "runs"}.issubset(tables)
        cols = [c["name"] for c in inspector.get_columns("scripts")]
        assert "metadata_json" in cols
        mc = MigrationContext.configure(conn)
        assert mc.get_current_revision() == "002"


def test_schema_no_drift_compare_metadata(alembic_config_sqlite):
    """Valida ausência de schema drift estrutural entre Base.metadata e banco migrado no SQLite.
    
    Filtros de dialeto no SQLite são estritamente documentados:
    - Divergências anônimas de constraints ou PK nullability específicas da reflexão do SQLite
      são toleradas apenas quando não afetam tabelas ou colunas.
    - Qualquer add_column, remove_column, add_table ou remove_table é estritamente proibido.
    """
    cfg, engine = alembic_config_sqlite

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        diff = compare_metadata(mc, Base.metadata)

        # Filtra diferenças estruturais (colunas e tabelas faltantes ou excedentes)
        structural_diffs = [
            d for d in diff 
            if d[0] in ("add_column", "remove_column", "add_table", "remove_table")
        ]
        assert structural_diffs == [], f"Schema drift estrutural detectado no SQLite: {structural_diffs}"

        # Assegura que metadata_json especificamente não possui drift
        add_cols = [d for d in diff if d[0] == "add_column" and d[2] == "scripts" and d[3].name == "metadata_json"]
        assert len(add_cols) == 0, "metadata_json está ausente no banco migrado"


def is_ci() -> bool:
    """Detecta se o teste está executando em ambiente de Integração Contínua (CI)."""
    import os
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


def test_postgres_real_migration_and_strict_zero_drift():
    """Validação estrita de zero-drift contra instância PostgreSQL real.
    
    REGRAS DE CONECTIVIDADE E FALHA:
    - No CI: PostgreSQL é OBRIGATÓRIO. Se não estiver acessível, FALHA com pytest.fail().
      O teste NUNCA pode ser silenciosamente ignorado/pulado no CI.
    - Em ambiente local: permite pytest.skip() exclusivamente se o PostgreSQL não estiver respondendo.
    
    REGRA DE SCHEMA DRIFT NO POSTGRESQL:
    - Exige compare_metadata() == [] rigorosamente SEM NENHUM FILTRO.
    """
    import os
    if not is_postgres_available():
        if is_ci():
            pytest.fail(
                "PostgreSQL 16 é OBRIGATÓRIO no CI, mas não foi detectado respondendo na porta 5432! "
                "O workflow de CI deve provisionar o container postgres:16 com TEST_DATABASE_URL."
            )
        else:
            pytest.skip("PostgreSQL não disponível na porta 5432 (permitido apenas em ambiente local)")

    url = os.getenv("TEST_DATABASE_URL") or get_settings().database_url
    engine = create_engine(url)

    ini_path = Path(__file__).parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", url)

    # Executa ciclo completo round-trip no PostgreSQL: downgrade base -> upgrade head
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        diff = compare_metadata(mc, Base.metadata)
        # No PostgreSQL, não há tolerância nem filtros: o diff deve ser rigorosamente vazio
        assert diff == [], f"Divergência de schema encontrada no PostgreSQL: {diff}"

    engine.dispose()
```

### 4. Workflow de CI `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [developer, main]
  pull_request:
    branches: [developer, main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: viralpanel_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      CI: "true"
      TEST_DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/viralpanel_test"

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]" || pip install -r requirements.txt

      - name: Run PostgreSQL Migration Tests (Mandatory in CI)
        run: |
          pytest -vv tests/test_migrations.py

      - name: Run Full Test Suite
        run: |
          pytest -q
```

---

## Validation Architecture

### 1. Test Harness Setup
- A suíte `tests/test_migrations.py` suporta execução dual-engine com garantia de CI verde e testes locais resilientes.
- **Ambiente Local (sem Postgres):** Executa clean upgrade, incremental com dados legados, ciclo round-trip (`head → 001 → base → head`) e schema drift estrutural via SQLite isolado em `tmp_path`. O teste de Postgres realiza skip informativo.
- **Ambiente de CI (GitHub Actions):** Serviço `postgres:16` com container healthcheck provisionado e `TEST_DATABASE_URL` configurado. A variável `CI=true` ativa a obrigatoriedade estrita: se o banco não responder, o job falha com `pytest.fail()`. O teste `test_postgres_real_migration_and_strict_zero_drift` executa com sucesso e exige `compare_metadata() == []` sem filtros.

### 2. Comandos de Validação Rápida

```powershell
# Execução da suíte completa de migrações
.venv\Scripts\pytest.exe -q tests/test_migrations.py

# Execução com saída detalhada e exibição de prints
.venv\Scripts\pytest.exe -vv -s tests/test_migrations.py

# Validação estática da sintaxe do workflow de CI
.venv\Scripts\python.exe -c "import yaml; data = yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); assert 'postgres' in data['jobs']['test']['services']; print('CI workflow syntax valid')"

# Execução de regressão de todo o repositório (garantindo que nada quebrou)
.venv\Scripts\pytest.exe -q
```

### 3. Acceptance Checklist da Phase 15
- [ ] Arquivo `alembic/versions/001_initial_schema.py` inalterado (integridade de hash e histórico preservada).
- [ ] Arquivo `alembic/versions/002_add_metadata_json_to_scripts.py` criado com `down_revision = "001"`.
- [ ] `alembic/env.py` refatorado para consumir `context.config.attributes.get('connection')` e `config.get_main_option('sqlalchemy.url')`.
- [ ] Arquivo `tests/test_migrations.py` criado com cobertura completa:
  - Subida limpa até `head`.
  - Subida incremental com validação de dados legados (`None`) e novos em `scripts.metadata_json`.
  - Ciclo completo round-trip (`head → 001 → base → head`).
  - Detecção de drift via `compare_metadata()`: filtros de dialeto documentados no SQLite, zero filtros no PostgreSQL (`assert diff == []`).
  - Teste contra PostgreSQL real OBRIGATÓRIO no CI (falha imediata com `pytest.fail()` se indisponível; skip condicional permitido apenas em dev local).
- [ ] Arquivo `.github/workflows/ci.yml` configurado com serviço `postgres:16`, `TEST_DATABASE_URL` e execução obrigatória dos testes de migração.
- [ ] 100% dos testes passando (`117 passed` preexistentes + novos testes de migração).
