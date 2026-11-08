---
phase: 12-refatoracao-do-video-composer-ffmpeg-e-integracao
plan: 01
subsystem: studio
tags:
  - ffmpeg
  - reaction-video
  - single-pass
  - lavfi
  - libx264
  - veryfast
  - crf20
  - dataclass

requires:
  - phase: 10-padronizacao-visual-zunto-e-regras-de-safe-zones-9-16
    provides: SafeZones9x16, ZuntoPalette e padronização visual
  - phase: 11-refatoracao-do-gerador-de-legendas-ass-zunto
    provides: gerador de legendas ASS ZUNTO! com caixa opaca e safe zone vertical

provides:
  - DTOs imutáveis ReactionCompositionSpec e StudioRenderRequest em src/viralpanel/studio/renderer.py
  - Motor de renderização ReactionVideoRenderer em passagem única (single-pass) sem fallback em disco (eliminação de source_visual_bg.mp4)
  - Injeção direta de lavfi inline color=c=#0f172a:s=1080x1920:r=24:d={duration} em [0:v] quando has_video_stream é falso
  - Codificação de alta fidelidade libx264 com preset veryfast, crf 20, pix_fmt yuv420p e áudio aac 192k
  - Suporte retrocompatível no método render(...) para chamadas legadas e chamadas com StudioRenderRequest

affects:
  - 12-02 (Integração do StudioService e Pipeline com render_from_request)
  - 13 (Inspeção visual e UAT final)

actuals:
  tokens: 4766
  tasks: 3
  commits: 3
  plan_head_before: 066275407296b3ccae266fbbb20ee4c6b1fb1164
  plan_head_after: 192dc2f4cbff967ca461f9dfafa22153d6375032

tech-stack:
  added: []
  patterns:
    - Single-pass FFmpeg composition com lavfi inline fallback
    - Frozen DTOs com validação de caminhos para Path em __post_init__ via object.__setattr__
    - Retrocompatible method overloading com delegação para DTO handler

key-files:
  created: []
  modified:
    - src/viralpanel/studio/renderer.py
    - tests/test_studio_renderer.py

key-decisions:
  - "Eliminação total do subprocesso intermediário do FFmpeg e do arquivo source_visual_bg.mp4 em disco através da injeção de lavfi inline diretamente como entrada [0:v]"
  - "Adoção de codificação libx264 com preset veryfast e crf 20 para equilíbrio ideal entre velocidade de renderização e nitidez visual ZUNTO! 1080x1920"
  - "Preservação da assinatura e kwargs do método render(...) para evitar quebras em chamadas legadas enquanto se expõe o novo método render_from_request"

patterns-established:
  - "Single-pass FFmpeg: todas as camadas ([0:v] bg/lavfi, [1:v] avatar pip, [composed] ass captions) são processadas em uma única execução de subprocess.run"

requirements-completed:
  - COMP-01
  - COMP-02
  - BRND-01
  - BRND-02

coverage:
  - id: DTO-01
    description: "DTOs ReactionCompositionSpec e StudioRenderRequest imutáveis com validação de tipos e Path"
    requirement: COMP-02
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py::test_studio_render_request_dto"
        status: pass
    human_judgment: false
  - id: COMP-SINGLEPASS
    description: "Composição FFmpeg single-pass sem criação de source_visual_bg.mp4 em disco"
    requirement: COMP-01
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py::test_single_pass_composition_no_disk_fallback"
        status: pass
    human_judgment: false
  - id: COMP-ENCODING
    description: "Flags de codificação FFmpeg de alta fidelidade (-preset veryfast, -crf 20, -pix_fmt yuv420p, -shortest)"
    requirement: COMP-02
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py::test_reaction_renderer_output_specs_and_encoding_flags"
        status: pass
    human_judgment: false
  - id: BRND-LAYERS
    description: "Ordenação estrita de camadas e safe zones [0:v] fundo -> [1:v] avatar -> [composed] ass -> [vout]"
    requirement: BRND-01
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py::test_reaction_renderer_single_ass_layer_and_path_escape"
        status: pass
    human_judgment: false

duration: 10m
completed: 2026-11-08
status: complete
---

# Phase 12 Plan 01: Refatoração do Video Composer FFmpeg e Composição Single-Pass Summary

**Composição de vídeo vertical 9:16 (1080x1920) refatorada para single-pass no FFmpeg com lavfi inline em [0:v], DTOs imutáveis frozen e codificação libx264 de alta fidelidade (preset veryfast, crf 20).**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-11-08T03:10:39Z
- **Completed:** 2026-11-08T03:20:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- **DTOs Imutáveis:** Criados `ReactionCompositionSpec` e `StudioRenderRequest` com `@dataclass(frozen=True)` em `src/viralpanel/studio/renderer.py`, garantindo parâmetros default estritos de codificação (1080x1920, 24fps, libx264, preset veryfast, crf 20, yuv420p, aac 192k) e conversão em `__post_init__` para `pathlib.Path`.
- **Passagem Única Sem I/O Intermediário:** Eliminado 100% da criação em disco e do subprocesso de `source_visual_bg.mp4` quando `has_video_stream()` for falso, injetando lavfi inline (`-f lavfi -i color=c=#0f172a:s=1080x1920:r=24:d={duration}`) diretamente na entrada `[0:v]`.
- **Alta Fidelidade & Safe Zones:** Composição configurada com `libx264` (`preset="veryfast"`, `-crf 20`, `yuv420p`), áudio com `-c:a aac -b:a 192k -shortest` e camadas ordenadas respeitando safe zones de PIP circular (`W-w-54:H-h-320`) e legendas ASS (`MarginV=640`).
- **Retrocompatibilidade Garantida:** Método público `render(...)` suporta tanto o novo DTO `StudioRenderRequest` quanto parâmetros posicionais/kwargs legados delegando internamente para `render_from_request`.
- **Testes Automatizados:** Suíte de testes expandida para 8 testes em `tests/test_studio_renderer.py` (e 89 testes no projeto inteiro), com 100% de sucesso.

## Task Commits

Each task was committed atomically:

1. **Task 1: Definir DTOs tipados imutáveis ReactionCompositionSpec e StudioRenderRequest** - `4a3e041` (feat)
2. **Task 2: Implementar composição single-pass com lavfi inline, preset veryfast, crf=20 e sobrecarga retrocompatível** - `fdf3f88` (feat)
3. **Task 3: Desenvolver testes comprovando eliminação de fallback em disco e parâmetros de codificação FFmpeg** - `192dc2f` (test)

**Plan metadata commit:** `docs(12): complete plan 12-01`

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] `src/viralpanel/studio/renderer.py` exists and is modified.
- [x] `tests/test_studio_renderer.py` exists and has new tests.
- [x] Commits `4a3e041`, `fdf3f88` e `192dc2f` exist in git history.
- [x] Suíte completa de testes (`./.venv/bin/pytest tests/test_studio_renderer.py`) aprovada com 8/8 testes.
