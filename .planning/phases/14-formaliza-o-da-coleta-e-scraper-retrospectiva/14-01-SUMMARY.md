---
phase: 14-formaliza-o-da-coleta-e-scraper-retrospectiva
plan: 01
subsystem: discovery
tags: [tiktok, yt-dlp, deduplication, scoring, retrospective]

requires:
  - phase: 02 (v1.0)
    provides: DiscoveryService, TikTok scraper, MediaDownloader
provides:
  - Rastreabilidade formal DISC-04 / DISC-05 para os commits c77a44c..10229d6
affects: [phase-15, phase-16]

actuals:
  tokens: 0
  tasks: 3
  commits: 0

tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - .planning/phases/14-formaliza-o-da-coleta-e-scraper-retrospectiva/14-01-SUMMARY.md
    - .planning/phases/14-formaliza-o-da-coleta-e-scraper-retrospectiva/14-VERIFICATION.md
  modified: []

key-decisions:
  - "Fase puramente retrospectiva: nenhum código, teste ou migration alterado"

patterns-established: []

requirements-completed: [DISC-04, DISC-05]

coverage:
  - id: D1
    description: "Normalização canônica de URLs TikTok, deduplicação na coleta e rejeição de score <= 0"
    requirement: DISC-04
    verification:
      - kind: unit
        ref: "tests/test_phase14_recovery.py#test_normalize_tiktok_url_variants"
        status: pass
      - kind: integration
        ref: "tests/test_phase14_recovery.py#test_discovery_deduplicates_equivalent_urls"
        status: pass
      - kind: integration
        ref: "tests/test_phase14_recovery.py#test_select_best_candidate_ignores_zero_or_negative_scores"
        status: pass
    human_judgment: false
  - id: D2
    description: "yt-dlp cross-platform com fallback, sobrescrita limpa em retries e limpeza de mídia sem fala"
    requirement: DISC-05
    verification:
      - kind: unit
        ref: "tests/test_phase14_recovery.py#test_ytdlp_cmd_* (3 testes)"
        status: pass
      - kind: integration
        ref: "tests/test_phase14_recovery.py#test_downloader_cleans_previous_files_on_retry"
        status: pass
      - kind: integration
        ref: "tests/test_phase14_recovery.py#test_scripting_service_cleans_files_on_insufficient_speech"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-11-13
status: complete
---

# Phase 14: Formalização da Coleta e Scraper (Retrospectiva) Summary

**DISC-04 e DISC-05 formalmente vinculados às implementações existentes no HEAD `0a006c8`, com 15/15 testes da fase e 117/117 da suíte completa aprovados na execução formal.**

## Performance

- **Started:** 2026-11-13T19:44:29-03:00
- **Completed:** 2026-11-13T19:47-03:00
- **Tasks:** 3/3
- **Files modified (código/testes):** 0

## Accomplishments

- **Task 1 (DISC-04):** auditados `normalize_tiktok_url` (`src/viralpanel/discovery/tiktok.py:18`), deduplicação em `DiscoveryService.collect_and_rank` e filtro `SourceVideo.score > 0.0` em `select_best_candidate` (`src/viralpanel/discovery/service.py:81`). Testes: **3 passed** (0.60s).
- **Task 2 (DISC-05):** auditados `get_ytdlp_cmd` (`src/viralpanel/discovery/tiktok.py:32`, `src/viralpanel/media/downloader.py:14`) com fallback `[sys.executable, "-m", "yt_dlp"]`, limpeza prévia + `--force-overwrites` em `MediaDownloader.fetch` (`src/viralpanel/media/downloader.py:50-58`) e remoção de mídia + `skipped_no_speech` em `ScriptingService` (`src/viralpanel/scripting/service.py:44-55`). Testes: **5 passed** (1.03s).
- **Task 3:** `test_phase14_recovery.py` + `test_discovery_scoring.py`: **15 passed** (1.02s). Suíte completa: **117 passed** (31.89s).

## Traceability Matrix

| Requisito | Commits | Implementação |
|---|---|---|
| DISC-04 | `e848edb`, `5e99225` | `normalize_tiktok_url`, `collect_and_rank`, `select_best_candidate` |
| DISC-05 | `e848edb`, `a9c4945`, `2628e09` | `get_ytdlp_cmd` (x2), `MediaDownloader.fetch`, `ScriptingService` |
| Contexto (não-DISC) | `c77a44c`, `88d8aaa`, `133571c`, `d482cf2`, `455a1d8`, `746a598`, `9c27de6`, `10229d6` | deps, nicho editorial, model IDs, fail-closed do ScriptWriter, testes |

## Task Commits

Nenhum commit de tarefa: fase retrospectiva sem alterações de código. O trabalho auditado já existe nos commits `c77a44c..10229d6`.

## Deviations from Plan

1. **Mecanismo de deduplicação:** o plano citava um conjunto `seen_urls`. O código real usa um dicionário `persisted_map` indexado pela URL normalizada, mais uma consulta ao banco (`url == raw OR url == norm`). Mesmo efeito (e mais robusto, pois também deduplica contra registros já persistidos). O plano tinha um erro de redação, não há defeito no código.
2. **Assinatura de `normalize_tiktok_url`:** o plano citava `(url, default_author="curiosidades")`. A assinatura real é `(raw_url: str, default_author: str = "unknown")`. Sem impacto funcional.
3. **Comportamento assimétrico de `get_ytdlp_cmd` quando o yt-dlp está ausente:** `src/viralpanel/discovery/tiktok.py` retorna `None`, enquanto `src/viralpanel/media/downloader.py` lança `RuntimeError`. Coberto por teste e intencional, mas registrado para revisão futura.

## Issues / Notes

- HEAD avançou de `10229d6` para `0a006c8` (commit de docs do owner) antes da execução; nenhum arquivo de `src/` ou `tests/` foi alterado entre eles.
- `REQUIREMENTS.md` e `ROADMAP.md` não foram atualizados para "Complete" nesta execução. A promoção de status fica para depois da revisão do owner.
