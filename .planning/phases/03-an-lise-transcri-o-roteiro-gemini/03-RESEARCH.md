# Phase 3 Research: Análise, Transcrição & Roteiro Gemini

## 1. Escopo & Requisitos
- **MEDIA-01**: Download do vídeo selecionado e extração do áudio limpo usando `yt-dlp` e `FFmpeg`. Registro dos arquivos no `StorageManager` (isolado por `run_id`).
- **MEDIA-02**: Transcrição do áudio com marcações de tempo (timestamps) usando Whisper / faster-whisper, gerando segmentos estruturados e texto contínuo.
- **SCRP-01**: Envio da transcrição e diretrizes de persona ao Gemini 2.5 Flash (`google-genai` / REST API oficial) para análise de retenção e estrutura.
- **SCRP-02**: Geração de roteiro 100% original estruturado com:
  1. Gancho de alta retenção (0–3s)
  2. Desenvolvimento fluido (4–45s)
  3. Chamada para Ação (CTA final)
  Persistência do roteiro na tabela `scripts` vinculado ao `SourceVideo`.

## 2. Decisões Técnicas e Arquitetura
1. **Módulo de Mídia (`viralpanel/media/downloader.py`)**:
   - `MediaDownloader`: executa download do vídeo de referência via `yt-dlp` e extrai áudio WAV/MP3 via `ffmpeg` em `storage/runs/{run_id}/source/`.
   - Suporte a mock/offline mode para testes unitários resilientes sem depender de rede externa.
2. **Módulo de Transcrição (`viralpanel/media/transcriber.py`)**:
   - `AudioTranscriber`: interface com suporte a Whisper / MockTranscriber.
   - Retorna dataclass `TranscriptionResult(text=..., segments=[{"start": 0.0, "end": 2.5, "text": "..."}])`.
3. **Módulo Gemini Roteirista (`viralpanel/scripting/gemini.py`)**:
   - Integração com Gemini 2.5 Flash via biblioteca oficial (`google-genai` ou requests com GEMINI_API_KEY).
   - Suporte a schema estruturado (Pydantic / JSON mode) garantindo os 3 blocos obrigatórios: `hook` (0-3s), `body` (4-45s), `cta` (final).
   - Fallback e mock para testes automatizados.
4. **Integração no Pipeline Celery (`viralpanel/tasks.py`)**:
   - Etapa diária: pós-seleção do vídeo candidato, dispara download -> transcrição -> roteirização Gemini -> persistência em `Script`.

## 3. Divisão de Planos
- **03-01-PLAN.md (Wave 1)**: Download de mídia e extração de áudio limpo via FFmpeg com persistência de assets no storage.
- **03-02-PLAN.md (Wave 2)**: Transcrição com Whisper / timestamps e contrato de dados.
- **03-03-PLAN.md (Wave 3)**: Integração com Gemini 2.5 Flash, geração do roteiro estruturado (0-3s, 4-45s, CTA), persistência no banco e integração no Celery.
