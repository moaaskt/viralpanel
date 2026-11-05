---
phase: 04-produ-o-studio-voz-avatar-v-deo-reaction
plan: 03
status: success
requirements: [PROD-03]
---
# Plan 04-03 Summary: Renderizador FFmpeg 9:16 Reaction, Legendas ASS & Integração Celery
- `subtitles.py`: geração de legendas dinâmicas ASS (`1080x1920`) com cue splitting por palavras.
- `renderer.py`: `ReactionVideoRenderer` com `filter_complex` FFmpeg compondo vídeo base em 9:16, avatar em PIP com moldura e burning de legendas via `libass`.
- `service.py`: `StudioService` orquestrando `audio`, `avatar`, `captions.ass` e `final_video`, salvando os registros em `Asset` e atualizando `SourceVideo.status = "produced"`.
- `tasks.py`: stage `production` integrado ao `trigger_daily_pipeline`.
- Testes: `tests/test_studio_renderer.py` (2/2) e `tests/test_celery_tasks.py` (2/2); suíte total 25/25.
