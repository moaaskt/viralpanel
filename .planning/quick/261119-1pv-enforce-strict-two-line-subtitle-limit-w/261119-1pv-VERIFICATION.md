---
quick_id: "261119-1pv"
slug: "enforce-strict-two-line-subtitle-limit-w"
status: "verified"
date: "2026-11-19"
human_visual_approval: "approved"
verified_files:
  - src/viralpanel/branding.py
  - src/viralpanel/studio/subtitles.py
  - tests/test_branding.py
  - tests/test_studio_subtitles.py
  - tests/test_e2e_inspection.py
---

# Verification Report: Quick Task 261119-1pv

## Verification Status: PASSED

### 1. FontWidthMeasurer Architecture Gate
- **Critério:** Largura horizontal calculada via `hmtx` (`advanceWidth`), `cmap` (formato 4) e `unitsPerEm`, sem métricas verticais `OS/2` (`usWinAscent`/`usWinDescent`).
- **Evidência:** `tests/test_studio_subtitles.py::test_font_width_measurer_uses_hmtx_cmap_units_per_em_only` executado com inspeção estática do código-fonte e verificação dinâmica das propriedades.
- **Resultado:** **PASSED**

### 2. Max 2 Lines Enforcement Gate
- **Critério:** Nenhum evento `Dialogue` (inclusive todos os eventos do Active Word Highlight) pode produzir 3 ou mais linhas no libass.
- **Evidências:**
  - `tests/test_studio_subtitles.py::test_shark_script_reflow_enforces_max_two_lines_at_default_font_size` (61/61 palavras em $\le 2$ linhas em 64px) — **PASSED**
  - `tests/test_studio_subtitles.py::test_extreme_long_word_triggers_controlled_font_size_fallback_without_truncation` — **PASSED**
  - `tests/test_e2e_inspection.py::test_all_individual_active_word_highlight_events_never_exceed_two_rendered_lines` (amostragem real de bandas de glifos em frames RGB24 do FFmpeg) — **PASSED**
  - Telemetria no script real do tubarão: 52 eventos em 2 linhas, 9 eventos em 1 linha, 0 eventos com 3+ linhas.
- **Resultado:** **PASSED**

### 3. Non-Blocking Technical Notes Compliance Gate
- **Nota 1:** `\N` tratado como separador antes de `select_highlight_word` e regex de destaque aplicada por segmento de linha (`tests/test_studio_subtitles.py::test_format_ass_dialogue_line_handles_newline_break_before_highlight_selection`) — **PASSED**
- **Nota 2:** Calibração da fusão de diacríticos com `max_diacritic_gap_px=6` e `min_band_height_px=8` validada nos 5 controles de teste (`test_libass_rendered_line_counter_calibration_including_reduced_fonts`) — **PASSED**
- **Resultado:** **PASSED**

### 4. Regression & Visual Quality Gate
- **Suíte de Testes:** 178 testes passaram sem regressão (`pytest -v`, 100% verde) — **PASSED**
- **Validação Visual Humana:** Short V2 (`storage/runs/run_google_flow_shark_001/final_output_v2.mp4`) inspecionado e aprovado pelo Project Owner — **PASSED**
