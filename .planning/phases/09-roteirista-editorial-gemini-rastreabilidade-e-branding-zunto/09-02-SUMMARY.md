---
phase: 09-roteirista-editorial-gemini-rastreabilidade-e-branding-zunto
plan: 02
subsystem: scripting
tags:
  - gemini
  - prompt-engineering
  - zunto
  - factual-claims
  - metadata
  - pydantic
status: complete
requires:
  - 09-01
provides:
  - SCRP-01
  - SCRP-02
  - structured-editorial-scripting
  - factual-claims-traceability
affects:
  - scripting
  - models
  - studio
tech-stack:
  added: []
  patterns:
    - Pydantic v2 structured schemas
    - OpenAPI responseSchema nullable fields
    - SQLAlchemy JSON metadata persistence
key-files:
  created: []
  modified:
    - src/viralpanel/models.py
    - src/viralpanel/scripting/gemini.py
    - src/viralpanel/scripting/service.py
    - tests/test_gemini_scripting.py
decisions:
  - "D-01/D-02: Persona ZUNTO! orientada por 'Você não sabia. Agora sabe.' com ganchos de 0-3s e sem encerramentos forçados"
  - "D-03/D-04: Separação estrita de closing_thought e cta opcional nullable em GeneratedScriptSchema e full_text limpo sem linhas órfãs"
  - "D-06/D-07: FactualClaim com preservação rigorosa da transcrição original sem inventar fontes externas"
  - "D-08: Script.metadata_json armazena factual_claims e metadados de roteirização preservando compatibilidade com o banco"
metrics:
  duration: "6m"
  completed_date: "2026-11-06"
actuals:
  tokens: 5162
  tasks: 3
  commits: 3
  plan_head_before: "cf1cb4295b59275bf877c4e462730ebbb9e7e51c"
  plan_head_after: "a1a034356f10e7016bdaccb0dd285bfe8b2bd6c8"
---

# Phase 9 Plan 02: Roteirista Editorial Gemini e Rastreabilidade Factual Summary

Implementação da camada editorial avançada do Gemini 2.5 Flash com separação formal de `closing_thought` e `cta` opcional, modelagem tipada de alegações factuais (`FactualClaim`), refinamento da persona editorial ZUNTO! ("Você não sabia. Agora sabe.") e persistência dos metadados de roteiro em `Script.metadata_json`.

## Entregas Realizadas

### 1. Evolução dos Schemas e Modelos (`models.py`, `gemini.py`)
- Adicionada a coluna `metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)` ao modelo SQLAlchemy `Script`, mantendo isolamento e sem interferir em `SourceVideo.metrics`.
- Criado o modelo Pydantic `FactualClaim` com campos `claim`, `source_reference`, `source_excerpt`, `timestamp` e `verification_status` (com default `"unverified_source_claim"`).
- Atualizado `GeneratedScriptSchema` para incluir `closing_thought: str = Field(default="", ...)` e `cta: str | None = Field(default=None, ...)`.
- Implementada a propriedade `full_text` dinâmica: une `hook`, `body` e `closing_thought`, anexando `cta` apenas quando presente e não vazio, evitando quebras de linha órfãs.
- Atualizado `RESPONSE_SCHEMA` OpenAPI para structured outputs do Gemini com suporte a campo nullable (`cta`) e array de claims factuais.

### 2. Refinamento de Prompts e Persona Editorial ZUNTO! (`gemini.py`)
- Refinada a `PERSONA` para refletir a autoridade, maturidade e tom provocativo do criador solo masculino da marca ZUNTO!, integrando a filosofia "Você não sabia. Agora sabe." como postura investigativa de revelação sem encerramentos forçados ou repetições mecânicas.
- Otimizada a cadência rítmica e pausas lógicas para síntese de voz (TTS).
- Atualizado o `PROMPT_TEMPLATE` com instruções para gancho magnético de 0–3s (máximo ~10 palavras, corte seco e sem saudações) e extração rigorosa de `factual_claims` estritamente baseados na transcrição de referência, proibindo terminantemente a alucinação de fontes externas.
- Atualizados os provedores de fallback `GroqScriptWriter` e `MockGeminiScriptWriter` para compatibilidade total com o novo schema estruturado.

### 3. Persistência de Metadados e Cobertura de Testes (`service.py`, `test_gemini_scripting.py`)
- Atualizado `ScriptingService.process()` para persistir os `factual_claims`, `closing_thought` e `cta` dentro de `script.metadata_json`.
- Expandida a suíte de testes em `tests/test_gemini_scripting.py` cobrindo validação de claims factuais, schema de roteiro com e sem CTA, formatação limpa de `full_text`, persistência de `metadata_json` no banco SQLite e testes dos provedores Gemini e Groq.
- Suíte completa de 67 testes executada com 100% de aprovação.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] `src/viralpanel/models.py` modificado com `metadata_json` em `Script`
- [x] `src/viralpanel/scripting/gemini.py` modificado com `FactualClaim`, `closing_thought`, `cta` opcional, prompts ZUNTO! e fallback
- [x] `src/viralpanel/scripting/service.py` modificado com persistência em `metadata_json`
- [x] `tests/test_gemini_scripting.py` expandido com testes de validação e persistência
- [x] Commits atômicos realizados para cada task:
  - `e7a5af6`: Task 1
  - `0635acc`: Task 2
  - `a1a0343`: Task 3
- [x] Todos os 67 testes da suíte passando sem erros.
