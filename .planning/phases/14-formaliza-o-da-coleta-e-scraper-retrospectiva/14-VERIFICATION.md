---
phase: 14-formaliza-o-da-coleta-e-scraper-retrospectiva
verified: 2026-11-13
status: passed
score: 7/7 must-haves verified
head: 0a006c8
---

# Phase 14 Verification

## Must-haves (truths)

| # | Truth | Evidence | Status |
|---|---|---|---|
| 1 | `normalize_tiktok_url` canonicaliza variantes | `src/viralpanel/discovery/tiktok.py:18`; `test_normalize_tiktok_url_variants` PASS | ✅ |
| 2 | `collect_and_rank` deduplica URLs equivalentes | `src/viralpanel/discovery/service.py` `persisted_map` + lookup no banco; `test_discovery_deduplicates_equivalent_urls` PASS | ✅ |
| 3 | `select_best_candidate` ignora score ≤ 0 | `src/viralpanel/discovery/service.py:81`; `test_select_best_candidate_ignores_zero_or_negative_scores` PASS | ✅ |
| 4 | `get_ytdlp_cmd` faz fallback para `sys.executable -m yt_dlp` | `src/viralpanel/discovery/tiktok.py:32`, `src/viralpanel/media/downloader.py:14`; 3 testes `test_ytdlp_cmd_*` PASS | ✅ |
| 5 | `MediaDownloader.fetch` limpa arquivos prévios + `--force-overwrites` | `src/viralpanel/media/downloader.py:50-58`; `test_downloader_cleans_previous_files_on_retry` PASS | ✅ |
| 6 | Mídia órfã removida em `InsufficientSpeechError` | `src/viralpanel/scripting/service.py:44-55`; `test_scripting_service_cleans_files_on_insufficient_speech` PASS | ✅ |
| 7 | 10 + 5 testes passam | 15 passed (1.02s) | ✅ |

## Automated runs (formal execution, 2026-11-13 ~19:45 -03)

```
T1  pytest -k normalize|deduplicate|score   -> 3 passed, 7 deselected (0.60s)
T2  pytest -k ytdlp|clean|speech            -> 5 passed, 5 deselected (1.03s)
T3  test_phase14_recovery + discovery_scoring -> 15 passed (1.02s)
FULL pytest                                 -> 117 passed (31.89s)
```

## Scope guards

- `src/`, `tests/` e `alembic/` não foram modificados (git status limpo nesses caminhos).
- Phase 13 e Milestone v1.1 não foram tocados.
- Phases 15–18 não foram iniciadas.

## Human verification

Não há itens de UI ou perceptuais. Nenhum item exige verificação humana.

## Gaps

Nenhum gap bloqueante. Ponto informativo: o comportamento de `get_ytdlp_cmd` quando o yt-dlp está ausente é assimétrico entre os módulos (`None` vs `RuntimeError`).
