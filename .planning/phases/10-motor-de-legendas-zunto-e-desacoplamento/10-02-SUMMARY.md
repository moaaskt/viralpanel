---
phase: 10-motor-de-legendas-zunto-e-desacoplamento
plan: 02
subsystem: studio
tags: [ffmpeg, libass, subtitles, zunto, visual-engine, safe-zones]
status: complete
requires:
  - phase: 10-01
    provides: SubtitleJobConfig, generate_subtitles, SafeZones9x16, branding
provides:
  - StudioService integrado com motor ZUNTO! gerando captions.ass
  - Burn-in único garantido com escape rigoroso de caminhos em ReactionVideoRenderer
  - Validação empírica geométrica de caixa opaca por amostragem de pixels FFmpeg/libass
affects:
  - 11-pipeline-supervisor-e-orquestracao
  - 13-validacao-audiovisual-e-benchmark
tech-stack:
  added: []
  patterns:
    - Injeção de DTO SubtitleJobConfig em StudioService.produce
    - Burn-in de legenda em camada única final no FFmpeg filter_complex
    - Teste empírico de renderização sem dependências externas via rawvideo rgb24
key-files:
  created: []
  modified:
    - src/viralpanel/studio/service.py
    - tests/test_studio_renderer.py
decisions:
  - "D-01: Integração de SubtitleJobConfig em StudioService.produce preservando contratos de Asset e banco de dados"
  - "D-04: Burn-in de legenda aplicado estritamente em camada única no passe final do ReactionVideoRenderer ([composed]ass='...')"
  - "D-05: Posição geométrica nominal de legendas com MarginV=640 e alinhamento inferior central (Alignment=2)"
  - "D-06: Validação de renderização empírica via amostragem de pixels rawvideo e delegação formal da validação visual final de UIs móveis para a Phase 13"
metrics:
  duration: 4m
  completed_date: "2026-11-08"
actuals:
  tokens: 18500
  tasks: 2
  commits: 2
plan_head_before: dd6cf2556d6b59b970207186141403437ccb388f
plan_head_after: ecd7b3b38634743bc9be51f7d4ae6e4cf236ba69
---

# Phase 10 Plan 02: Integração do Motor de Legendas ZUNTO! e Renderização Summary

**Integração do motor desacoplado de legendas ZUNTO! em StudioService.produce e ReactionVideoRenderer, burn-in garantido em camada única com escape de caminhos, validação empírica de renderização de frame 1080x1920 com FFmpeg/libass e zero regressões na suíte de testes.**

## Performance & Execution Overview

- **Duração total:** 4 minutos
- **Tasks executadas:** 2 de 2 (Task 1 Auto + Task 2 Auto)
- **Commits atômicos realizados:** 2 commits verificados no git ledger:
  - `465123d`: `feat(10-02): integrar SubtitleJobConfig e geracao ZUNTO! em StudioService.produce`
  - `ecd7b3b`: `test(10-02): validar parametros ASS, camada unica e teste empirico de frame FFmpeg`
- **Suíte de testes:** 81 testes passando com 100% de sucesso (4 testes em `tests/test_studio_renderer.py`, 77 testes do restante do projeto sem qualquer regressão)

## Requirements Coverage

| Requisito | Status | Como foi atendido |
|-----------|--------|-------------------|
| **SUB-01** | Cumprido | `StudioService.produce` agora instancia `SubtitleJobConfig` com `margin_v=SafeZones9x16.SUBTITLE_MARGIN_V` (640) e gera `captions.ass` no padrão ZUNTO! com caixa opaca nativa (`BorderStyle=3`, `Outline=16`, `BackColour=&H000A0A0A&`); validação empírica por amostragem de pixels com FFmpeg confirma a presença da caixa opaca na safe zone sem presumir cobertura abstrata infalível. |
| **SUB-02** | Cumprido | Renderização de legendas aplicada em camada única estrita no passe final do FFmpeg (`[composed]ass='{escaped_ass}'[vout]`), sem duplicação de filtros ASS ou camadas sobrepostas; escape rigoroso de dois pontos (`\:`) e barras normais (`/`) contra quebra do libass. |
| **SUB-03** | Cumprido | Resolução vertical nominal 1080x1920 preservada em todas as etapas; posicionamento geométrico central inferior (`Alignment=2`, `PlayResY=1920`, `MarginV=640`); preservada tipografia Montserrat/DejaVu Sans calibrada em 64px e destaque em amarelo ZUNTO!. |
| **BRND-01** | Cumprido | Consumo de `SafeZones9x16.SUBTITLE_MARGIN_V`, `ZuntoPalette.DEEP_BLACK` e utilitários de branding em `service.py` e na suíte de testes. |

## Key Changes & Architecture

### 1. `StudioService.produce` Integrado com `SubtitleJobConfig`
- Substituída a geração anterior de legendas pela instanciação explícita de `SubtitleJobConfig`:
  ```python
  job_config = SubtitleJobConfig(
      script_text=script_text,
      total_duration=voice_duration,
      output_path=subtitles_path,
      margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,
  )
  generate_subtitles(job_config)
  ```
- Preservada integralmente a assinatura pública `StudioService.produce(db, run_id, script) -> Asset`.
- Preservada a criação e vinculação dos 3 registros `Asset` obrigatórios (`audio`, `avatar`, `final_video`) vinculados ao `script.id` e atualização do status `script.source_video.status = 'produced'`.

### 2. Camada Única de Burn-in e Blindagem de Caminhos no Renderer
- O `ReactionVideoRenderer.render` mantém o filtro ASS aplicado em passe final único (`[composed]ass='{escaped_ass}'[vout]`), impedindo textos duplicados.
- Escape rigoroso de caminhos do arquivo ASS (`str(path.resolve()).replace('\\', '/').replace(':', '\\:')`), mitigando T-10-04.
- Teste dedicado `test_reaction_renderer_single_ass_layer_and_path_escape` valida a ocorrência única de `ass='...'` e o correto escape de dois-pontos.

### 3. Validação Geométrica Empírica de Frame com FFmpeg/libass
- Implementado teste de integração `test_empirical_reference_frame_ass_rendering` que renderiza um frame de referência 1080x1920 sobre fundo magenta contrastante (`color=c=magenta:s=1080x1920:d=0.1`).
- Exportação em `rawvideo rgb24` (6.220.800 bytes) inspecionada puramente com standard library Python (sem novas dependências pesadas, em estrita conformidade com T-10-SC).
- Confirmação de >1000 pixels da caixa opaca `#0A0A0A` (R, G, B <= 25) concentrados na faixa de safe zone (Y entre 1080 e 1280), enquanto as extremidades (Y=500 e Y=1600) permanecem intocadas com o fundo magenta original.
- **Delegação Formal:** Registrado expressamente que a comprovação visual definitiva perante as interfaces móveis ativas do TikTok, Reels e Shorts e hard-subs de vídeos com enquadramentos arbitrários fica formalmente delegada à inspeção audiovisual da Phase 13.

## Threat Model Mitigations Handled

- **T-10-04 (Tampering / FFmpeg filter escape):** Caminho do arquivo ASS rigorosamente tratado com `replace('\\', '/').replace(':', '\\:')` e validado por teste de interceptação.
- **T-10-05 (Repudiation / Asset persistence):** Garantida criação atômica dos 3 registros de Asset e status do vídeo mantidos com `db.commit()` e `db.refresh()`.
- **T-10-SC (Supply Chain):** Zero novas dependências adicionadas; processamento binário de frame realizado nativamente via standard library Python.

## Deviations from Plan

None - plano executado exatamente como planejado e especificado.

## Self-Check: PASSED

- [x] `src/viralpanel/studio/service.py` atualizado com `SubtitleJobConfig` e `generate_subtitles`
- [x] `tests/test_studio_renderer.py` estendido com 4 testes passando
- [x] Commits `465123d` e `ecd7b3b` verificados e medidos no git ledger
- [x] Total de 81 testes passando com 100% de sucesso em toda a suíte do repositório
- [x] Zero regressões em módulos do sistema
