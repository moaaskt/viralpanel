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
- **D-03 (Desacoplamento do Alembic env.py):** `alembic/env.py` deve ser refatorado cirurgicamente para suportar conexões injetadas via `context.config.attributes.get('connection')` e URL configurável via `context.config.get_main_option('sqlalchemy.url')`, eliminando a dependência rígida de `create_engine(get_settings().database_url)` em tempo de importação e execução. O fallback para `get_settings().database_url` ocorre exclusivamente no runtime normal da aplicação (CLI/produção), nunca nos testes de migração. [VERIFIED: alembic/env.py:9,19]
- **D-04 (Harness de Testes e Ciclo Completo de Migração):** Criação de `tests/test_migrations.py` cobrindo o ciclo completo de migrações:
  1. Subida limpa da base até `head` (`upgrade head`).
  2. Subida incremental de `001` até `head` (`002`), com asserção estrita de preservação e integridade de dados legados (registros pré-existentes mantêm `metadata_json = None`) e inserção de novos registros com JSON estruturado.
  3. Ciclo completo round-trip: `head → 001 → base → head`, assegurando que o downgrade não deixa tabelas ou versões órfãs e que re-aplicar o upgrade do zero restaura o schema completo sem erros.
  4. Detecção automatizada de schema drift: no SQLite, allowlist explícita e restritiva das divergências conhecidas do dialeto (qualquer divergência não listada reprova o teste); no PostgreSQL, asserção estrita `assert diff == []` sem nenhum filtro nem allowlist. [VERIFIED: ANALYZER-04:70,196-200]
- **D-05 (Estratégia Dual-Engine e PostgreSQL Obrigatório no CI):** 
  1. No ambiente de CI (`CI=true` ou `GITHUB_ACTIONS=true`), o PostgreSQL 16 é OBRIGATÓRIO através de container service dedicado. O teste contra PostgreSQL real NUNCA pode ser ignorado ou pulado (skip proibido no CI; falha obrigatória do build com `pytest.fail()` se o PostgreSQL não estiver disponível).
  2. A execução condicional com skip de PostgreSQL é restrita exclusivamente ao ambiente local de desenvolvimento quando `TEST_DATABASE_URL` não estiver configurada ou a instância local não estiver respondendo.
  3. Configuração de workflow formal de CI (`.github/workflows/ci.yml`) com serviço `postgres:16`, container healthcheck (`pg_isready`), porta 5432 mapeada, variável `TEST_DATABASE_URL` e execução obrigatória dos testes de migração e da suíte completa. [VERIFIED: user_instructions]
- **D-06 (Fronteira Estrita de Escopo da Phase 15):** A migração `003` (`Asset.status`) e os campos de concorrência/lease de `SourceVideo` pertencem exclusivamente à Phase 16 (Concorrência, Fencing & Lifecycle). A Phase 15 mantém foco estrito e cirúrgico na resolução do drift de `Script.metadata_json`, na homologação da infraestrutura de testes de migração e no workflow de CI com PostgreSQL 16. [VERIFIED: user_instructions, ANALYZER-04:195-200]
- **D-07 (Isolamento Estrito de Banco e Prevenção de Perda de Dados):** O teste de PostgreSQL (`test_postgres_real_migration_and_strict_zero_drift`) executa comandos destrutivos (`downgrade base`) e, por isso, deve operar exclusivamente em um banco dedicado, descartável, isolado e recriável.
  1. Uso EXCLUSIVO de `TEST_DATABASE_URL`. É terminantemente proibido qualquer fallback para `DATABASE_URL` ou `get_settings().database_url`.
  2. O banco de dados alvo deve ser estritamente `'viralpanel_test'`, configurado como banco dedicado, descartável e recriável. O teste jamais pode operar em banco compartilhado, persistente, de homologação ou da aplicação (`viralpanel`).
  3. Autorização explícita obrigatória para DDL destrutivo: o teste exige compulsoriamente a variável de ambiente `ALLOW_DESTRUCTIVE_TEST_DATABASE=true` ANTES de criar a engine ou abrir qualquer conexão com o PostgreSQL. Sem essa autorização explícita, o teste falha com `pytest.fail()` no CI e emite `pytest.skip()` seguro em dev local.
  4. Proteção de host coerente em local e CI: a lista de hosts locais permitidos é harmonizada como `SAFE_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}`. A validação é aplicada sem bypass de CI: qualquer conexão direcionada a hosts fora desta allowlist exige compulsoriamente a autorização separada `ALLOW_REMOTE_TEST_DATABASE=true`.
  5. Validação pré-execução e em runtime antes de qualquer comando Alembic: (a) variável configurada e não-vazia; (b) esquema PostgreSQL; (c) banco idêntico a `viralpanel_test`; (d) host pertencente a `SAFE_LOCAL_HOSTS` ou autorizado por `ALLOW_REMOTE_TEST_DATABASE=true` (uniforme em local e CI); (e) autorização destrutiva `ALLOW_DESTRUCTIVE_TEST_DATABASE=true` antes de criar a engine; (f) asserção em conexão ativa de `SELECT current_database() == 'viralpanel_test'`.
  6. Se em ambiente local `TEST_DATABASE_URL` estiver ausente, permite skip informativo seguro sem tocar em nenhum banco.
  7. Se em CI a variável estiver ausente, inválida, apontar para outro banco, a conexão falhar ou `ALLOW_DESTRUCTIVE_TEST_DATABASE=true` não estiver definida, executa `pytest.fail()` imediatamente antes de qualquer operação destrutiva. [VERIFIED: user_instructions]

### the agent's Discretion
- Implementação da allowlist SQLite restritiva (`is_allowed_sqlite_dialect_diff`) baseada na estrutura real de 7 posições do Alembic 1.20+ (`diff_item[5] is True` para `existing_nullable` e `diff_item[6] is False` para `modify_nullable`), validando concretamente objetos `UniqueConstraint` anônimos na tabela/coluna esperadas e chave primária `id` confirmada no `Base.metadata`.
- Estrutura de fixtures de isolamento e detecção automática de conectividade PostgreSQL em `tests/test_migrations.py`.
- Formatação dos tipos DDL para máxima portabilidade PostgreSQL 16 / SQLite 3.35+.

### Deferred Ideas (OUT OF SCOPE)
- Migração `003_add_status_to_assets.py` e colunas de leasing (`reservation_token`, `lease_expires_at`) → Phase 16.
- Atualização do schema da API REST (`ScriptSchema`) para expor `factual_claims` → Phase 18.
- Criação de containers Docker ephemeral via testcontainers → Fora do escopo (usar serviço postgres:16 no CI e banco de teste local dedicado).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Apoio da Pesquisa / Implementação |
|----|-----------|-----------------------------------|
| **MIGR-01** | Resolução do Schema Drift `scripts.metadata_json` no Alembic sem alterar a migração 001. | Criação de `alembic/versions/002_add_metadata_json_to_scripts.py` (`down_revision = "001"`). [VERIFIED: models.py:43, 001_initial_schema.py:32-40] |
| **MIGR-02** | Refatoração de `alembic/env.py` para permitir injeção de conexão e URL dinâmica de testes. | Adição de leitura de `attributes["connection"]` e `config.get_main_option("sqlalchemy.url")` em `run_migrations_online()` e `run_migrations_offline()`. [VERIFIED: alembic/env.py:9,19] |
| **MIGR-03** | Ciclo completo de testes de migração (Clean Upgrade, Incremental Upgrade, Downgrade e Integridade de Dados). | Implementação de testes automatizados em `tests/test_migrations.py` usando `alembic.command`. [VERIFIED: tests/test_models.py:10] |
| **MIGR-04** | Detecção automatizada de Schema Drift via `compare_metadata()`. | Verificação programática com `alembic.autogenerate.compare_metadata` garantindo paridade total entre `Base.metadata` e o banco migrado (allowlist restritiva no SQLite, zero drift estrito no PostgreSQL). [VERIFIED: alembic.autogenerate] |
| **MIGR-05** | Suporte dual com validação mandatória em PostgreSQL 16 no CI e execução rápida em SQLite local. | Configuração obrigatória de serviço PostgreSQL 16 no CI (`.github/workflows/ci.yml`) e fixture SQLite temporária em disco (`tmp_path`) para desenvolvimento local, com obrigatoriedade estrita e zero-skip no CI. [VERIFIED: pytest suite] |
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
4. **Viabilizar execução dual:** testes rápidos e isolados rodando via SQLite em qualquer máquina local, com validação mandatória e estrita em PostgreSQL 16 no pipeline de CI.
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

### 3. Peculiaridades de Reflexão do SQLite em `compare_metadata()` e Necessidade de Allowlist Explícita
- **Sintoma:** `compare_metadata()` acusa diferenças espúrias em bancos SQLite migrados (como `modify_nullable` em colunas `id` chave primária e `add_constraint` de constraints anônimas `unique`), mesmo quando o schema está perfeitamente alinhado. [VERIFIED: in-repo test]
- **Causa:** O dialeto de reflexão do SQLite não reflete com 100% de fidelidade a nulabilidade de chaves primárias sem declaração explícita de `NOT NULL`, e não reflete nomes de constraints únicas geradas inline.
- **Mitigação:** No teste rodando contra SQLite, implementar uma **allowlist explícita e restritiva** (`is_allowed_sqlite_dialect_diff`) contendo unicamente as divergências documentadas de dialeto (`modify_nullable` nas PKs `id` das tabelas conhecidas e constraints anônimas). Qualquer divergência fora desta allowlist (ex: colunas extras ou faltantes, tipos incompatíveis) reprova o teste imediatamente. No PostgreSQL, a asserção é `diff == []` estrito, sem nenhuma allowlist nem filtro.

### 4. Vazamento Prematuro de Alterações da Phase 16
- **Sintoma:** Tentar adicionar `Asset.status` ou colunas de lease de `SourceVideo` na migração `002`.
- **Causa:** Confusão de escopo entre o Blueprint de Remediação (onde a Phase 15 originalmente agrupava 002 e 003) e as decisões consolidadas pelo Tech Lead.
- **Mitigação:** Manter a Phase 15 focada **exclusivamente** na coluna `scripts.metadata_json` e no harness de testes de migração. `Asset.status` será tratado na Phase 16.

### 5. Queda Acidental e Perda de Dados no Banco da Aplicação por Fallback de URL de Teste
- **Sintoma:** Testes de migração executando `command.downgrade(cfg, "base")` contra o banco de dados operacional da aplicação (`viralpanel`), expurgando tabelas em ambiente local ou staging.
- **Causa:** O teste de PostgreSQL ou a função `is_postgres_available()` fazer fallback para `DATABASE_URL` ou `get_settings().database_url` quando `TEST_DATABASE_URL` estiver ausente.
- **Mitigação:** O banco `viralpanel_test` deve ser exclusivamente descartável e isolado. O teste com `downgrade base` jamais pode operar em banco compartilhado, persistente ou de aplicação. O teste e a função de disponibilidade utilizam EXCLUSIVAMENTE `TEST_DATABASE_URL`, com zero fallback. Antes de instanciar engine ou emitir DDL destrutivo, valida-se: (1) esquema `postgresql`; (2) nome do banco exatamente igual a `viralpanel_test`; (3) proteção de host local para impedir execução em servidores remotos/nuvem em dev local sem flag explícita (`ALLOW_REMOTE_TEST_DATABASE=true`); (4) confirmação em runtime de `SELECT current_database() == 'viralpanel_test'`. Em dev local, pular o teste com `pytest.skip()` se a variável estiver ausente; em CI, falhar compulsoriamente com `pytest.fail()`.

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
"""Testes de integridade de schema, ciclo completo de migrações e detecção de drift."""
import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import UniqueConstraint, create_engine, inspect, text
from sqlalchemy.engine.url import make_url
from viralpanel.database import Base

SAFE_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


def is_ci() -> bool:
    """Detecta se a suíte está executando em ambiente de Integração Contínua (CI)."""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


def get_verified_test_db_url() -> str:
    """Valida estritamente a URL de teste do PostgreSQL.
    
    Regras de Segurança e Isolamento:
    1. TEST_DATABASE_URL deve estar explicitamente configurada e não vazia.
    2. O esquema deve ser estritamente PostgreSQL (postgresql, postgresql+psycopg2, etc.).
    3. O banco de destino DEVE ser exatamente 'viralpanel_test', um banco dedicado, descartável e recriável.
       Proibido qualquer outro banco (como 'viralpanel', 'postgres', etc.) para proteger bases de aplicação.
    4. Proteção de host seguro como controle separado: em execução local, o host deve pertencer
       a SAFE_LOCAL_HOSTS ('localhost', '127.0.0.1', '::1', 'postgres') ou exigir a flag explícita
       ALLOW_REMOTE_TEST_DATABASE=true para impedir perda de dados em bancos remotos.
    
    Retorna a URL validada ou lança ValueError caso qualquer critério falhe.
    """
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url or not raw_url.strip():
        raise ValueError("TEST_DATABASE_URL não configurada ou vazia.")
    
    parsed = make_url(raw_url.strip())
    if not parsed.drivername.startswith("postgresql"):
        raise ValueError(f"TEST_DATABASE_URL possui driver inválido ({parsed.drivername}). Esperado driver PostgreSQL.")
    
    if parsed.database != "viralpanel_test":
        raise ValueError(
            f"BLOQUEIO DE SEGURANÇA: TEST_DATABASE_URL aponta para o banco '{parsed.database}'. "
            f"O teste destrutivo exige exclusivamente o banco descartável 'viralpanel_test' para prevenir corrupção de dados."
        )

    # Proteção de host coerente em local e CI (sem bypass de CI) via controle separado ALLOW_REMOTE_TEST_DATABASE
    host = parsed.host or "127.0.0.1"
    is_local_host = host in SAFE_LOCAL_HOSTS
    if not is_local_host and os.getenv("ALLOW_REMOTE_TEST_DATABASE") != "true":
        raise ValueError(
            f"BLOQUEIO DE SEGURANÇA: TEST_DATABASE_URL aponta para host não-local '{host}'. "
            f"Hosts autorizados sem flag: {SAFE_LOCAL_HOSTS}. "
            f"Para conectar a bancos remotos (em ambiente local ou CI), configure explicitamente ALLOW_REMOTE_TEST_DATABASE='true'."
        )
            
    return str(parsed)


def is_postgres_available() -> bool:
    """Verifica se há um servidor PostgreSQL de teste respondendo especificamente para TEST_DATABASE_URL.
    
    Não utiliza NUNCA a URL da aplicação (get_settings().database_url).
    Se TEST_DATABASE_URL não estiver configurada ou for inválida, retorna False imediatamente.
    """
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url or not raw_url.strip():
        return False
    try:
        url = get_verified_test_db_url()
        parsed = make_url(url)
        host = parsed.host or "127.0.0.1"
        port = parsed.port or 5432

        # 1. Checagem rápida de socket TCP no host/porta do banco de teste
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.8)
        result = sock.connect_ex((host, port))
        sock.close()
        if result != 0:
            return False

        # 2. Conexão real e validação de current_database() == 'viralpanel_test'
        eng = create_engine(url, connect_args={"connect_timeout": 2})
        with eng.connect() as conn:
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            if db_name != "viralpanel_test":
                eng.dispose()
                return False
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


def is_allowed_sqlite_dialect_diff(diff_item: Any) -> bool:
    """Allowlist estritamente restritiva de divergências conhecidas do dialeto SQLite.
    
    Formato real do diff do Alembic (AlterColumnOp.to_diff_tuple):
    - modify_nullable: tupla de 7 elementos:
      (
          'modify_nullable',             # [0] str
          schema,                        # [1] str | None
          table_name,                    # [2] str
          column_name,                   # [3] str
          existing_metadata_dict,        # [4] dict (existing_type, server_default, comment)
          existing_nullable,             # [5] bool (refletido no banco SQLite: True)
          modify_nullable,               # [6] bool (alvo no modelo SQLAlchemy: False)
      )
    - add_constraint: tupla de 2 elementos:
      (
          'add_constraint',              # [0] str
          constraint_obj,                # [1] UniqueConstraint anônima em source_videos.url
      )
    
    Qualquer divergência fora da estrutura exata REPROVA o teste imediatamente.
    """
    # Desempacota caso o diff venha envelopado em lista de 1 elemento
    if isinstance(diff_item, (list, tuple)) and len(diff_item) == 1 and isinstance(diff_item[0], tuple):
        diff_item = diff_item[0]

    if not isinstance(diff_item, tuple) or len(diff_item) < 2:
        return False

    diff_type = diff_item[0]

    # Divergência Conhecida 1: SQLite omite NOT NULL explícito em PKs refletidas como id
    if diff_type == "modify_nullable":
        if len(diff_item) == 7:
            table_name = diff_item[2]
            column_name = diff_item[3]
            existing_nullable = diff_item[5]
            modify_nullable = diff_item[6]

            known_tables = {"source_videos", "scripts", "assets", "publications", "runs"}
            if table_name in known_tables and column_name == "id":
                table = Base.metadata.tables.get(table_name)
                # Confirma concretamente que 'id' é a chave primária real da tabela no modelo Base.metadata
                if table is not None and "id" in table.primary_key.columns:
                    # Confirma índices exatos: existing_nullable=True no banco e modify_nullable=False no modelo
                    if existing_nullable is True and modify_nullable is False:
                        return True

    # Divergência Conhecida 2: Constraint UNIQUE anônima gerada inline pelo SQLite
    if diff_type == "add_constraint":
        if len(diff_item) == 2:
            constraint = diff_item[1]
            if isinstance(constraint, UniqueConstraint) and constraint.name is None:
                table_name = constraint.table.name if constraint.table is not None else None
                col_names = [col.name for col in constraint.columns]
                if table_name == "source_videos" and col_names == ["url"]:
                    return True

    return False


def test_schema_no_drift_compare_metadata(alembic_config_sqlite):
    """Valida ausência de schema drift no SQLite via allowlist explícita de dialeto.
    
    Qualquer divergência não prevista na allowlist REPROVA o teste imediatamente.
    """
    cfg, engine = alembic_config_sqlite

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        diff = compare_metadata(mc, Base.metadata)

        # Filtra exclusivamente itens que estão na allowlist documentada
        unallowed_diffs = [d for d in diff if not is_allowed_sqlite_dialect_diff(d)]
        assert unallowed_diffs == [], (
            f"Schema drift não autorizado detectado no SQLite! "
            f"Divergências encontradas fora da allowlist: {unallowed_diffs}"
        )

        # Assegura que metadata_json na tabela scripts tem drift rigorosamente ZERO
        metadata_json_diffs = [
            d for d in diff 
            if len(d) >= 4 and d[2] == "scripts" and getattr(d[3], "name", d[3]) == "metadata_json"
        ]
        assert metadata_json_diffs == [], "metadata_json possui divergência de schema no SQLite!"


def test_postgres_real_migration_and_strict_zero_drift():
    """Validação estrita de zero-drift contra instância PostgreSQL real descartável.
    
    REGRAS DE SEGURANÇA E ISOLAMENTO:
    - Exclusivamente TEST_DATABASE_URL. Zero fallback para DATABASE_URL ou get_settings().
    - O banco de dados deve ser dedicado, descartável, isolado e recriável: estritamente 'viralpanel_test'.
    - Autorização explícita obrigatória: exige ALLOW_DESTRUCTIVE_TEST_DATABASE=true antes de criar engine ou conectar.
    - Proteção explícita contra operações em bancos de produção ou remotos não autorizados:
      host deve pertencer a SAFE_LOCAL_HOSTS (localhost/127.0.0.1/::1/postgres) de modo coerente em local e CI,
      ou exigir a autorização separada ALLOW_REMOTE_TEST_DATABASE=true sem bypass automático de CI.
    - Em CI: qualquer ausência de variável, URL inválida, banco incorreto, falta de autorização destrutiva
      ou falha de conexão executa pytest.fail() imediatamente antes de qualquer operação destrutiva.
    - Em ambiente local: ausência ou banco indisponível emite pytest.skip() informativo.
    - Validação de current_database() == 'viralpanel_test' em conexão aberta antes do downgrade base.
    - Zero drift: assert diff == [] rigorosamente sem filtros.
    """
    raw_test_url = os.getenv("TEST_DATABASE_URL")

    # 1. Guarda de presença: tratamento consistente CI vs local
    if not raw_test_url or not raw_test_url.strip():
        if is_ci():
            pytest.fail(
                "FALHA DE SEGURANÇA NO CI: TEST_DATABASE_URL não configurada! "
                "O workflow de CI deve definir TEST_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/viralpanel_test'."
            )
        else:
            pytest.skip(
                "TEST_DATABASE_URL não configurada no ambiente local. "
                "Para rodar o teste de migração em PostgreSQL, defina TEST_DATABASE_URL apontando para o banco descartável 'viralpanel_test'."
            )

    # 2. Validação estrita de esquema, banco ('viralpanel_test') e host seguro (sem bypass de CI)
    try:
        test_url = get_verified_test_db_url()
    except ValueError as e:
        if is_ci():
            pytest.fail(f"FALHA DE SEGURANÇA NO CI: Configuração de TEST_DATABASE_URL inválida: {e}")
        else:
            pytest.skip(f"TEST_DATABASE_URL inválida em ambiente local: {e}")

    # 3. Autorização explícita obrigatória para DDL destrutivo ANTES de qualquer conexão ou criação de engine
    if os.getenv("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "true":
        if is_ci():
            pytest.fail(
                "FALHA DE SEGURANÇA NO CI: ALLOW_DESTRUCTIVE_TEST_DATABASE='true' não configurada! "
                "Operações no banco descartável 'viralpanel_test' exigem autorização destrutiva explícita antes de conectar."
            )
        else:
            pytest.skip(
                "Conexão e operações destrutivas no PostgreSQL puladas: requer ALLOW_DESTRUCTIVE_TEST_DATABASE='true'. "
                "O banco de teste 'viralpanel_test' precisa ser dedicado, descartável e recriável."
            )

    # 4. Validação de conectividade
    if not is_postgres_available():
        if is_ci():
            pytest.fail(
                "FALHA DE CONECTIVIDADE NO CI: PostgreSQL de teste (viralpanel_test) não está acessível em TEST_DATABASE_URL! "
                "Verifique a inicialização do container de serviço postgres:16."
            )
        else:
            pytest.skip(
                "PostgreSQL de teste (viralpanel_test) não está respondendo em TEST_DATABASE_URL. "
                "Verifique se o container postgres está ativo na porta 5432."
            )

    # 5. Engine criada exclusivamente a partir de TEST_DATABASE_URL validada
    engine = create_engine(test_url)

    # 6. Guarda em conexão aberta: valida current_database() ANTES de qualquer DDL destrutivo
    with engine.connect() as conn:
        active_db = conn.execute(text("SELECT current_database()")).scalar()
        assert active_db == "viralpanel_test", (
            f"SEGURANÇA VIOLADA: Conexão ativa no banco '{active_db}', esperado exclusivamente 'viralpanel_test'. Abortando!"
        )

    ini_path = Path(__file__).parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", test_url)

    # 7. Executa ciclo completo round-trip no PostgreSQL: downgrade base -> upgrade head
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")

    # 8. Validação estrita de zero-drift: compare_metadata() sem nenhum filtro
    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        diff = compare_metadata(mc, Base.metadata)
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
      ALLOW_DESTRUCTIVE_TEST_DATABASE: "true"

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
          pip install -e ".[dev]"

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
- **Ambiente Local (sem Postgres):** Executa clean upgrade, incremental com dados legados, ciclo round-trip (`head → 001 → base → head`) e schema drift estrutural via SQLite isolado em `tmp_path`. Se `TEST_DATABASE_URL` não for fornecida, o teste de PostgreSQL emite skip informativo sem tentar acessar a base da aplicação.
- **Ambiente de CI (GitHub Actions):** Serviço `postgres:16` com container healthcheck provisionado e `TEST_DATABASE_URL` configurado exclusivamente para `viralpanel_test` com a autorização explícita `ALLOW_DESTRUCTIVE_TEST_DATABASE=true`. A variável `CI=true` ativa a obrigatoriedade estrita: se a variável estiver ausente, se apontar para outro banco, se a autorização destrutiva faltar ou se o banco não responder, o job falha com `pytest.fail()`. O teste `test_postgres_real_migration_and_strict_zero_drift` executa com sucesso e exige `compare_metadata() == []` sem filtros.
- **Prevenção de Perda de Dados e Isolamento:** É terminantemente proibido fallback para `DATABASE_URL` ou `get_settings().database_url` em qualquer teste do PostgreSQL. O banco de teste `viralpanel_test` deve ser dedicado, descartável e recriável. Hosts locais são harmonizados via `SAFE_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}` e hosts externos requerem o controle separado `ALLOW_REMOTE_TEST_DATABASE=true`. Operações destrutivas (`downgrade base`) exigem obrigatoriamente `ALLOW_DESTRUCTIVE_TEST_DATABASE=true`.

### 2. Comandos de Validação Rápida

```powershell
# Execução da suíte completa de migrações
.venv\Scripts\pytest.exe -q tests/test_migrations.py

# Execução com saída detalhada e exibição de prints
.venv\Scripts\pytest.exe -vv -s tests/test_migrations.py

# Validação estática da sintaxe e variáveis do workflow de CI
.venv\Scripts\python.exe -c "import yaml; data = yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); assert 'postgres' in data['jobs']['test']['services']; assert data['jobs']['test']['env'].get('ALLOW_DESTRUCTIVE_TEST_DATABASE') == 'true'; print('CI workflow syntax and env valid')"

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
  - Detecção de drift via `compare_metadata()`: filtros de dialeto no SQLite através de allowlist estritamente restritiva (`is_allowed_sqlite_dialect_diff`), baseada no formato real de 7 posições do Alembic 1.20+ (`diff_item[5] is True` vs `diff_item[6] is False`), validando concretamente `UniqueConstraint` anônima em `source_videos.url` e PK `id` confirmada no `Base.metadata` nas 5 tabelas conhecidas; zero filtros no PostgreSQL (`assert diff == []`).
  - Teste contra PostgreSQL real consome EXCLUSIVAMENTE `TEST_DATABASE_URL` (zero fallback para database_url da aplicação), com pré-validação estrita do banco dedicado, descartável e recriável `viralpanel_test`, hosts restritos a `SAFE_LOCAL_HOSTS` de modo coerente em local e CI sem bypass de CI (ou controle separado `ALLOW_REMOTE_TEST_DATABASE=true`), autorização explícita obrigatória `ALLOW_DESTRUCTIVE_TEST_DATABASE=true` antes de criar a engine ou conectar, e asserção em runtime de `SELECT current_database() == 'viralpanel_test'`.
  - No CI, falha obrigatória com `pytest.fail()` se `TEST_DATABASE_URL` estiver ausente/inválida, apontar para outro banco, `ALLOW_DESTRUCTIVE_TEST_DATABASE` não for `true` ou o banco estiver inacessível. Em dev local, skip informativo seguro sem tentar acessar nenhum banco.
- [ ] Arquivo `.github/workflows/ci.yml` configurado com serviço `postgres:16`, `TEST_DATABASE_URL` apontando para `viralpanel_test`, `ALLOW_DESTRUCTIVE_TEST_DATABASE: "true"` e execução obrigatória dos testes de migração.
- [ ] 100% dos testes passando (aprovação integral de toda a suíte de regressão do repositório + novos testes de migração).
