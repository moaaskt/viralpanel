---
phase: 10-motor-de-legendas-zunto-e-desacoplamento
plan: 01
subsystem: studio
tags: [subtitles, libass, zunto, branding, typography, safe-zones, timing]
status: complete
requires:
  - 08-auditoria-contratos-e-diagn-stico-de-causa-raiz
  - 09-padronizacao-identidade-visual-zunto
provides:
  - subtitle-engine-zunto
  - subtitle-job-config-dto
  - ass-opaque-box-header
  - punctuation-aware-chunking
  - proportional-timing-allocation
  - ass-strict-sanitization
  - yellow-highlight-explicit-closure
affects:
  - src/viralpanel/studio/subtitles.py
  - src/viralpanel/studio/__init__.py
  - tests/test_studio_subtitles.py
tech-stack:
  added: []
  patterns:
    - ASS v4+ opaque box styling (BorderStyle=3, Outline=16, MarginV=640)
    - Punctuation-aware syntactic cue segmentation (3 to 5 words cadence)
    - Proportional character-weighted timing allocation with minimum cue duration clamp
    - Two-phase ASS sanitization preventing control code injection
    - Explicit inline colour override closure preventing style leakage
key-files:
  created:
    - tests/test_studio_subtitles.py
  modified:
    - src/viralpanel/studio/subtitles.py
    - src/viralpanel/studio/__init__.py
decisions:
  - "Adotado BorderStyle=3 com OutlineColour e BackColour em &H000A0A0A& (preto profundo #0A0A0A), Outline=16 e MarginV=640 para criar backdrop opaco dinâmico nativo cobrindo hard-subs preexistentes sem custo computacional extra."
  - "Definido SubtitleJobConfig como DTO imutável (@dataclass frozen=True) parametrizável consumindo constantes centrais de branding.py."
  - "Implementada segmentação de cues sensível a pausas (. , ! ? ; :) mantendo cadência de 3 a 5 palavras por cue e contiguidade temporal estrita sem sobreposições."
  - "Implementada temporização proporcional ao peso de caracteres e pausas com piso mínimo de 0.8s e log formal de timing_mode ('proportional_character_estimate' vs 'word_timestamp_aligned')."
  - "Sanitização em duas etapas substituindo '{' por '(' e '}' por ')' com normalização de quebras para '\\N', eliminando risco de quebra do parser libass."
  - "Destaque de palavra de impacto em amarelo ZUNTO! ({\\c&H0015CCFA&}) com fechamento obrigatório e compulsório em branco ({\\c&H00FFFFFF&}), eliminando vazamento de estilos."
  - "Contratos legados (SubtitleCue, build_cues_from_script, write_ass_subtitles) 100% preservados e retrocompatíveis."
metrics:
  duration: 8m
  completed_date: "2026-11-08"
actuals:
  tokens: 6992
  tasks: 3
  commits: 3
  plan_head_before: 56006b48a3a177c089aed17e6d6132f85c702828
  plan_head_after: e2d7c9a834a537f561bb7cd2d7c57a23c8ff0dd1
---

# Phase 10 Plan 01: Núcleo do Motor de Legendas ZUNTO! e Desacoplamento Summary

**Motor de legendas desacoplado ZUNTO! com caixa opaca nativa (BorderStyle=3, MarginV=640), quebra sintática de 3-5 palavras por cue, temporização proporcional sem sobreposições e destaque amarelo blindado contra style leakage.**

## Performance & Execution Overview

- **Duração total:** 8 minutos
- **Tasks executadas:** 3 de 3 (Task 1 Tracer + Task 2 TDD + Task 3 TDD)
- **Commits atômicos realizados:** 3 commits verificados no ledger
- **Suíte de testes:** 79 testes passando com 100% de sucesso (12 novos testes dedicados em `tests/test_studio_subtitles.py`, 67 testes preexistentes sem qualquer regressão)

## Requirements Coverage

| Requisito | Status | Como foi atendido |
|-----------|--------|-------------------|
| **SUB-01** | Cumprido | Backdrop opaco retangular ASS com `BorderStyle=3`, `Outline=16`, `MarginV=640` e cores ZUNTO! cobrindo fisicamente hard-subs preexistentes na safe zone vertical; desacoplamento estrito entre a lógica textual/temporal de `subtitles.py` e o renderizador. |
| **SUB-02** | Cumprido | Segmentação sintática orientada a pausas e pontuação (`.`, `,`, `!`, `?`, `;`, `:`), mantendo cadência de 3 a 5 palavras por cue; temporização proporcional ao peso de caracteres e pausas com contiguidade temporal estrita (`cue[i].end == cue[i+1].start`) e piso mínimo de 0.8s; suporte a `word_timestamps` com registro formal de `timing_mode`. |
| **SUB-03** | Cumprido | Tipografia Montserrat/DejaVu Sans calibrada em 64px, safe zone em 1080x1920 (`PlayResX: 1080`, `PlayResY: 1920`); destaque inline amarelo ZUNTO! (`{\c&H0015CCFA&}`) na palavra de impacto e fechamento compulsório em branco puro (`{\c&H00FFFFFF&}`) prevenindo vazamento de cores. |
| **BRND-01** | Cumprido | Consumo estrito das constantes e utilitários de `src/viralpanel/branding.py` (`ZuntoPalette.DEEP_BLACK`, `ZuntoPalette.IMPACT_YELLOW`, `ZuntoPalette.PURE_WHITE`, `SafeZones9x16`, `hex_to_ass_color`). |

## Key Changes & Architecture

### 1. DTO `SubtitleJobConfig` e Cabeçalho ASS ZUNTO!
- Criado `SubtitleJobConfig` imutável com campos de safe zones, padding de caixa, margem vertical (`MarginV=640`), resolução 1080x1920 e metadados de sincronização.
- Enriquecido `SubtitleCue` com campos opcionais `highlight_word: str | None = None` e `timing_mode: str = "proportional_character_estimate"`.
- Implementada a função `build_ass_header(config: SubtitleJobConfig | None = None) -> str` configurando `BorderStyle=3` (caixa opaca retangular), `Outline=16`, `Shadow=0`, `Alignment=2` (centro-inferior), cores BGR oficiais ZUNTO! (`&H000A0A0A&`, `&H00FFFFFF&`, `&H0015CCFA&`) e resolução 1080x1920.

### 2. Segmentação Sintática e Temporização Proporcional
- Implementado `split_script_into_cues` que analisa pontuação e ritmo de leitura, agrupando sentenças em blocos editoriais de 3 a 5 palavras sem quebras artificiais de termos conectados.
- Alocação proporcional de duração ponderada pelo comprimento de caracteres e pontuações de pausa (vírgula adiciona peso 4, ponto final adiciona peso 7), garantindo piso mínimo de 0.8s quando a duração total permite.
- Contiguidade temporal rigorosa: `cues[0].start == 0.0`, `cues[i].start == cues[i-1].end`, `cues[i].start < cues[i].end` e `cues[-1].end == round(total_duration, 2)`.
- Compatibilidade retroativa garantida via delegação direta em `build_cues_from_script`.

### 3. Sanitização Blindada e Destaque Amarelo ZUNTO!
- `sanitize_ass_text(text: str) -> str`: converte `{` para `(` e `}` para `)`, além de normalizar `\r\n` e `\n` para `\N`, bloqueando injeção ou quebra acidental do parser `libass`.
- `select_highlight_word(words: list[str]) -> str | None`: heurística que filtra stopwords comuns da língua portuguesa e palavras curtas (< 4 caracteres) para realçar termos de alto impacto semântico.
- `format_ass_dialogue_line(cue: SubtitleCue) -> str`: aplica override amarelo `{\c&H0015CCFA&}` e fecha compulsoriamente com `{\c&H00FFFFFF&}` imediatamente após a palavra destacada, eliminando qualquer risco de style leakage.
- `write_ass_subtitles(cues, output_path)` e `generate_subtitles(config)` atualizados para emitir diálogos formatados e seguros.

## Threat Model Mitigations Handled

- **T-10-01 (Tampering / ASS injection):** Resolvido via `sanitize_ass_text` antes de qualquer manipulação de tags.
- **T-10-02 (Tampering / Style Leakage):** Resolvido via regex word boundary com fechamento explícito compulsório `{\c&H00FFFFFF&}` validado por testes de contagem de tags.
- **T-10-03 (DoS / Gaps e Overlaps):** Resolvido com clamp temporal estrito e indexação sequencial contígua.
- **T-10-SC (Supply Chain):** Zero novas dependências externas; estritamente biblioteca padrão e Pydantic.

## Deviations from Plan

None - plano executado exatamente como planejado e especificado.

## Self-Check: PASSED

- [x] `src/viralpanel/studio/subtitles.py` existe e está implementado
- [x] `tests/test_studio_subtitles.py` existe e tem 12 testes passando
- [x] Commits `c2345b5`, `0d2578d`, `e2d7c9a` verificados e presentes no histórico git
- [x] Total de 79 testes passando na suíte inteira
- [x] Zero regressões em `tests/test_studio_renderer.py`
