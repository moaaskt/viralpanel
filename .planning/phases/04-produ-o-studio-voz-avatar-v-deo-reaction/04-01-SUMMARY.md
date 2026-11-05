---
phase: 04-produ-o-studio-voz-avatar-v-deo-reaction
plan: 01
status: success
requirements: [PROD-01]
---
# Plan 04-01 Summary: Síntese de Voz (XTTS / Mock)
- `BaseVoiceSynthesizer`, `XTTSVoiceSynthesizer` (import tardio `TTS.api.TTS`) e `MockVoiceSynthesizer` (FFmpeg lavfi proporcional às palavras) implementados em `src/viralpanel/studio/voice.py`.
- Helper `probe_duration` via `ffprobe`.
- Testes: `tests/test_studio_voice.py` (1/1).
