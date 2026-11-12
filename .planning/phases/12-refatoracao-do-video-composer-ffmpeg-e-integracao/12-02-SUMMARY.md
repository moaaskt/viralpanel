---
phase: 12-refatoracao-do-video-composer-ffmpeg-e-integracao
plan: 02
subsystem: studio
status: complete
tags:
  - studio
  - celery
  - studio-render-request
  - single-pass
  - atomic-persistence
  - assets
  - regression-free

requires:
  - phase: 12-refatoracao-do-video-composer-ffmpeg-e-integracao
    provides: DTOs ReactionCompositionSpec e StudioRenderRequest, e ReactionVideoRenderer single-pass

provides:
  - Integração do StudioService.produce com o DTO StudioRenderRequest para composição de vídeo
  - Preservação da assinatura pública produce(db, run_id, script) -> Asset mantendo 100% de compatibilidade com o worker Celery
  - Persistência atômica dos 3 registros Asset ('audio', 'avatar', 'final_video') vinculados a script.id
  - Transição garantida do status do vídeo de origem para 'produced'
  - Validação end-to-end com a tarefa Celery tasks._run_pipeline e teste unitário dedicado em test_celery_tasks.py
  - Aprovação com 100% de sucesso nos 91 testes da suíte global do repositório

affects:
  - 13 (Inspeção visual e UAT final da Phase 13)

actuals:
  tokens: 4200
  tasks: 2
  commits: 2
  plan_head_before: 66ad26de760f20d3f99b7c3d1293e776d743d8f0
  plan_head_after: deff5dbfa4ade076f2c5b503188c1affa7c72426

tech-stack:
  added: []
  patterns:
    - Encapsulamento de insumos de renderização em DTO StudioRenderRequest no nível de serviço
    - Fallback elegante para renderizadores legados via hasattr(self.renderer, "render_from_request")
    - Transação atômica SQLAlchemy para persistência dos assets do run e atualização de status

key-files:
  created: []
  modified:
    - src/viralpanel/studio/__init__.py
    - src/viralpanel/studio/service.py
    - tests/test_studio_renderer.py
    - tests/test_celery_tasks.py

key-decisions:
  - "Instanciação do StudioRenderRequest dentro de StudioService.produce repassando run_id, source, avatar, voz, legendas, duração da voz, avatar_config e specs de composição"
  - "Preservação estrita da assinatura produce(self, db: Session, run_id: str, script: Script) -> Asset garantindo compatibilidade transparente com o Celery worker"
  - "Inclusão de verificação hasattr(self.renderer, 'render_from_request') para manter total compatibilidade com mocks legados que implementem apenas render()"

patterns-established:
  - "Service-to-Renderer DTO contract: a camada de serviço prepara insumos de negócio e instancia o DTO imutável StudioRenderRequest para o renderizador"

requirements-completed:
  - COMP-03
  - COMP-01
  - COMP-02
  - BRND-01
  - BRND-02

coverage:
  - id: STUDIO-DTO-INTEGRATION
    description: "StudioService.produce instancia e delega para StudioRenderRequest com preservação de assinatura e persistência atômica"
    requirement: COMP-03
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py::test_studio_service_produce_encapsulates_studio_render_request"
        status: pass
      - kind: integration
        ref: "tests/test_studio_renderer.py::test_studio_service_renders_vertical_9x16_reaction_video"
        status: pass
    human_judgment: false
  - id: CELERY-E2E-VALIDATION
    description: "Execução assíncrona do Celery consumindo StudioService sem regressão contratual e registrando histórico do run"
    requirement: COMP-03
    verification:
      - kind: integration
        ref: "tests/test_celery_tasks.py::test_run_pipeline_success"
        status: pass
      - kind: integration
        ref: "tests/test_celery_tasks.py::test_task_records_run_and_is_idempotent"
        status: pass
    human_judgment: false

duration: 8m
---

# Phase 12 Plan 02: Integração do StudioService e Validação E2E com Celery Summary

**One-liner:** Integração do StudioService ao pipeline single-pass via StudioRenderRequest, persistência atômica de 3 assets e validação E2E com Celery tasks sem regressões.

## Execução das Tarefas

### Task 1: Atualizar StudioService.produce com StudioRenderRequest preservando contratos e persistência atômica
- **Arquivos modificados:** `src/viralpanel/studio/__init__.py`, `src/viralpanel/studio/service.py`, `tests/test_studio_renderer.py`
- **Alterações:**
  - Importação de `StudioRenderRequest`, `ReactionCompositionSpec` e `AvatarConfig` em `StudioService`.
  - Suporte a `avatar_config` e `composition` configuráveis no construtor de `StudioService` com defaults retrocompatíveis.
  - Instanciação de `StudioRenderRequest(run_id, source_video_path, avatar_video_path, voice_audio_path, ass_subtitle_path, output_path, voice_duration, avatar_config, composition)` no passo 4 da renderização de `produce`.
  - Delegação para `self.renderer.render_from_request(render_request)` com fallback para `self.renderer.render(...)` quando chamado por mocks legados.
  - Preservação estrita da assinatura `produce(self, db: Session, run_id: str, script: Script) -> Asset`.
  - Persistência dos 3 registros `Asset` (`audio`, `avatar`, `final_video`) vinculados a `script.id` e atualização de `script.source_video.status = "produced"`.
  - Adição do teste unitário `test_studio_service_produce_encapsulates_studio_render_request` em `tests/test_studio_renderer.py`.
- **Commit:** `ec3445a` (`feat(studio): integrar StudioService.produce com StudioRenderRequest e persistencia atomica`)

### Task 2: Validar integração com Celery tasks e executar regressão E2E em toda a suíte de testes
- **Arquivos modificados:** `tests/test_celery_tasks.py`
- **Alterações:**
  - Adição de `test_run_pipeline_success` em `tests/test_celery_tasks.py` para validar a execução ponta a ponta da orquestração assíncrona do Celery consumindo `StudioService.produce(db, run_id, script)`.
  - Validação dos 5 assets gerados ao longo do pipeline (2 de scripting: `source_video`, `source_audio`; 3 de studio: `audio`, `avatar`, `final_video`).
  - Execução dos testes combinados de Celery e renderização (`tests/test_celery_tasks.py tests/test_studio_renderer.py`).
  - Execução da suíte completa de testes (`./.venv/bin/pytest tests/ -v`): 91 testes aprovados com 100% de sucesso sem nenhuma regressão.
- **Commit:** `deff5db` (`test(studio): validar integracao e2e com celery tasks e regressao global`)

## Deviations from Plan

None - plano executado exatamente como especificado.

## Known Stubs

Nenhum stub identificado. Todos os componentes estão plenamente integrados e validados no banco de dados SQLite e no pipeline de renderização.

## Threat Flags

Nenhuma nova superfície de risco identificada. As mitigações T-12-04 (atomicidade da sessão SQLAlchemy), T-12-05 (estabilidade de contratos com o Celery worker) e T-12-06 (gestão determinística de caminhos via StorageManager) foram integralmente respeitadas.

## Self-Check: PASSED
- [x] `src/viralpanel/studio/service.py` atualizado e integrado com `StudioRenderRequest`.
- [x] Assinatura pública `StudioService.produce(db, run_id, script) -> Asset` rigorosamente preservada.
- [x] Persistência atômica dos 3 assets e transição para `produced` validadas.
- [x] Compatibilidade ponta a ponta com o Celery em `tests/test_celery_tasks.py`.
- [x] Suíte completa de 91 testes aprovada com 100% de sucesso.
- [x] Commits atômicos `ec3445a` e `deff5db` presentes no histórico Git.
