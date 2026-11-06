# Phase 8: Relatório Técnico de Auditoria, Contratos e Diagnóstico de Causa Raiz

**Data da Auditoria:** 2026-11-06  
**Milestone:** v1.1 — ZUNTO! Visual Engine  
**Fase:** 08 — Auditoria, Contratos e Diagnóstico de Causa Raiz  
**Requisitos Cobertos:** `COMP-01`, `SUB-01`, `AVTR-01`  
**Natureza da Fase:** 100% Diagnóstica e Analítica (D-15 — Zero modificações em `src/viralpanel/`)

---

## 1. Mapeamento de Contratos e Interfaces Atuais

Esta seção documenta a auditoria estática e dinâmica das fronteiras de integração entre a fila assíncrona Celery (`src/viralpanel/tasks.py`), o orquestrador de mídia (`src/viralpanel/studio/service.py`), o gerenciador de armazenamento (`src/viralpanel/storage.py`) e os motores especializados de voz (`voice.py`), avatar (`avatar.py`), legendas (`subtitles.py`) e renderização (`renderer.py`).

### 1.1 Contrato Público Obrigatório (`tasks.py` ↔ `StudioService.produce`)

Conforme a decisão arquitetural bloqueada **D-01**, a assinatura pública de `StudioService.produce` constitui uma fronteira imutável (*one-way door*) com a task Celery `trigger_daily_pipeline` e a função interna `_run_pipeline`.

- **Assinatura Inspecionada (Runtime & AST):**
  ```python
  # src/viralpanel/studio/service.py (linhas 67-122)
  def produce(self, db: Session, run_id: str, script: Script) -> Asset:
  ```
  *(Nota de tipagem: Em `src/viralpanel/models.py`, `PipelineRun.id` é definido como `Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)`, representando um UUID v4 serializado como `str`. Os DTOs internos propostos aceitam `str | uuid.UUID` mantendo `str` na fronteira do SQLAlchemy/Celery).*

- **Ponto de Chamada no Worker Celery (`src/viralpanel/tasks.py`, linhas 171-185):**
  ```python
  run.stage = "production"
  db.commit()
  final_asset = studio_service.produce(db=db, run_id=run.id, script=script)
  summary.update(
      final_asset_id=final_asset.id,
      final_video_path=final_asset.file_path,
      final_video_duration=final_asset.duration_seconds,
  )
  ```

- **Invariantes Pós-Condição Exigidos por `_run_pipeline` e `SupervisionService`:**
  1. **Valor de retorno:** Instância persistida e atualizada (`db.refresh`) de `viralpanel.models.Asset` com `asset_type == "final_video"`.
  2. **Atributos obrigatórios no `Asset` retornado:**
     - `id: str` (UUID v4 gerado e persistido no PostgreSQL/SQLite).
     - `script_id: str` (FK apontando para `script.id`).
     - `file_path: str` (caminho absoluto/resolvido no filesystem local para `final_reaction_9x16.mp4` existente e não vazio).
     - `duration_seconds: float` (duração real em segundos extraída via `probe_duration`).
  3. **Efeitos colaterais de persistência esperados na sessão `db`:**
     - Criação e persistência de 3 registros na tabela `assets` vinculados a `script.id`:
       - `asset_type="audio"` (`narration.wav`)
       - `asset_type="avatar"` (`avatar.mp4` — *nota: nas Phases 11/12, caso o vídeo intermediário seja eliminado no single-pass, o registro ou referência de asset deve preservar a compatibilidade relacional ou apontar para o recurso de avatar utilizado sem quebrar consultas do dashboard*).
       - `asset_type="final_video"` (`final_reaction_9x16.mp4`)
     - Atualização de estado: `script.source_video.status = "produced"` (quando `script.source_video is not None`) seguida de `db.commit()`.

---

### 1.2 Matriz Exaustiva de Contratos e Fronteiras Internas

A tabela abaixo mapeia todas as assinaturas inspecionadas dinamicamente via `inspect.signature` e análise de código-fonte:

| Componente / Módulo | Método / Função | Parâmetros de Entrada (Tipos Atuais) | Retorno (Tipo Atual) | Efeitos de I/O & Estado | Problemas de Acoplamento Identificados |
|---------------------|-----------------|--------------------------------------|----------------------|-------------------------|----------------------------------------|
| `tasks.py` | `build_default_services(mock: bool \| None = None)` | `mock: bool \| None` | `tuple[DiscoveryService, ScriptingService, StudioService, SupervisionService, PublishingService]` | Lê `get_settings()`; instancia dependências concretas | Acoplamento direto às classes concretas sem configuração granular de estilo/layout. |
| `studio/service.py` | `StudioService.__init__(...)` | `voice_synthesizer: BaseVoiceSynthesizer`, `avatar_animator: BaseAvatarAnimator`, `renderer: ReactionVideoRenderer \| None = None`, `storage: StorageManager \| None = None` | `None` | Inicializa `ReactionVideoRenderer()` e `StorageManager()` padrão se omitidos | Aceita injeção limpa, permitindo evolução interna sem afetar `tasks.py`. |
| `studio/service.py` | `StudioService.produce(db, run_id, script)` | `db: Session`, `run_id: str`, `script: Script` | `Asset` (`final_video`) | Cria diretório via `storage.get_run_dir(run_id)`; grava `narration.wav`, `avatar.mp4`, `captions.ass`, `final_reaction_9x16.mp4`; faz `db.commit()` | Hardcode de nomes de arquivos (`narration.wav`, `avatar.mp4`, `captions.ass`) e orquestração sequencial acoplada a tipos primitivos. |
| `studio/service.py` | `StudioService._ensure_source_video(run_id, duration=2.0)` | `run_id: str`, `duration: float = 2.0` | `Path` (`.../runs/source/source.mp4`) | Acessa `self.storage._safe(self.storage.get_run_dir(run_id).parent / "source")`; invoca `ffmpeg` se ausente | **Bug estrutural latente de path:** `get_run_dir(run_id)` retorna `runs/<run_id>/assets`. Logo, `.parent` é `runs/<run_id>`, gravando em `runs/<run_id>/source/source.mp4`, que coincide com `MediaDownloader` (`runs/<run_id>/source/source.mp4`), mas viola encapsulamento ao chamar método privado `storage._safe(...)`. |
| `storage.py` | `StorageManager.get_run_dir(run_id)` | `run_id: str` | `Path` (`<base_dir>/runs/<run_id>/assets`) | Executa `mkdir(parents=True, exist_ok=True)` imediatamente | Não fornece método público para o subdiretório `source` (forçando callers a usar `_safe` diretamente). |
| `studio/voice.py` | `BaseVoiceSynthesizer.synthesize(text, output_path, speaker_wav=None)` | `text: str`, `output_path: Path`, `speaker_wav: Path \| None = None` | `tuple[Path, float]` | Sintetiza WAV em disco (`24000 Hz`, mono) e mede duração via `probe_duration` | Retorna apenas duração escalar total (`float`), sem timestamps por palavra para sincronia fina de legendas. |
| `studio/avatar.py` | `BaseAvatarAnimator.generate_avatar_video(audio_path, output_path, avatar_image_path=None)` | `audio_path: Path`, `output_path: Path`, `avatar_image_path: Path \| None = None` | `tuple[Path, float]` | Lê `assets/creator_avatar.png` (ou cria fallback via FFmpeg) e gera `avatar.mp4` (`360x360`, `yuv420p`) | Gera vídeo MP4 intermediário opaco (`yuv420p`) com dimensão `360x360`, divergindo de `renderer.avatar_size = 340` (forçando re-escala). |
| `studio/subtitles.py` | `build_cues_from_script(script_text, total_duration, max_words_per_cue=6)` | `script_text: str`, `total_duration: float`, `max_words_per_cue: int = 6` | `list[SubtitleCue]` | Processamento puro em memória (divisão uniforme de chunks pelo tempo total) | Divisão temporal puramente linear (`duration / len(chunks)`), ignorando cadência real da fala, pausas e comprimento fonético das palavras. |
| `studio/subtitles.py` | `write_ass_subtitles(cues, output_path)` | `cues: list[SubtitleCue]`, `output_path: Path` | `Path` | Escreve arquivo `.ass` UTF-8 com `ASS_HEADER` hardcoded | Cabeçalho ASS (`DejaVu Sans,62`, `MarginV=480`) é constante global imutável, impedindo customização de estilo ZUNTO! ou posicionamento dinâmico por safe zone. |
| `studio/renderer.py` | `ReactionVideoRenderer.render(source_video_path, avatar_video_path, voice_audio_path, ass_subtitle_path, output_path)` | 5 argumentos `Path` posicionais/nomeados | `tuple[Path, float]` | Verifica `has_video_stream`; cria `source_visual_bg.mp4` se necessário; executa `ffmpeg` final | Recebe 5 `Path`s soltos sem metadados de layout, safe zones, transparência de avatar ou diretrizes de composição. |

---

### 1.3 Acoplamento Temporal, Espacial e de Diretórios

1. **Acoplamento Temporal Estrito:**
   - `StudioService.produce` depende da execução sequencial:
     1. `voice_synthesizer.synthesize` precisa terminar primeiro porque `voice_duration: float` é a única fonte de verdade temporal para todas as etapas seguintes.
     2. `build_cues_from_script(script_text, total_duration=voice_duration)` usa `voice_duration` para fatiar os tempos `start`/`end` de cada `SubtitleCue`.
     3. `_ensure_source_video(run_id, duration=max(voice_duration, 2.0))` usa `voice_duration` caso precise sintetizar um vídeo fonte de fallback.
     4. `renderer.render(...)` recalcula `duration = max(probe_duration(voice_audio_path), 1.5)` invocando `ffprobe` novamente sobre `narration.wav`, demonstrando redundância de I/O por falta de um DTO de contexto compartilhado.
2. **Descompasso Dimensional entre `avatar.py` e `renderer.py`:**
   - `AudioReactiveAvatarAnimator` inicializa com `width: int = 360, height: int = 360`.
   - `ReactionVideoRenderer` inicializa com `avatar_size: int = 340` e, no `filter_complex`, reescala o vídeo de 360x360 para 340x340 e depois aplica `pad=352:352:6:6:color=white`.
3. **Acoplamento de Caminhos no `StorageManager`:**
   - O `MediaDownloader` (em `scripting/service.py` -> `media/downloader.py`) salva o vídeo baixado do TikTok em `runs/<run_id>/source/source.mp4`.
   - O `StudioService` acessa esse mesmo arquivo construindo manualmente `self.storage.get_run_dir(run_id).parent / "source" / "source.mp4"`. Não há contrato explícito passando o caminho do vídeo baixado entre `ScriptingService` e `StudioService`.

---

### 1.4 Diagrama Sequencial de Chamadas e Fluxo de Dados (Estado Atual)

```mermaid
sequenceDiagram
    autonumber
    participant Celery as tasks.py (_run_pipeline)
    participant DB as SQLAlchemy Session (db)
    participant Studio as StudioService.produce()
    participant Storage as StorageManager
    participant Voice as BaseVoiceSynthesizer
    participant Avatar as BaseAvatarAnimator
    participant Subs as subtitles.py
    participant Renderer as ReactionVideoRenderer
    participant FFmpeg as FFmpeg / FFprobe CLI

    Celery->>DB: run.stage = "production"; db.commit()
    Celery->>Studio: produce(db=db, run_id=run.id, script=script)
    Studio->>Storage: get_run_dir(run_id)
    Storage-->>Studio: Path(".../runs/{run_id}/assets")

    Note over Studio,Voice: Etapa 1: Síntese de Voz
    Studio->>Voice: synthesize(script_text, Path("narration.wav"))
    Voice->>FFmpeg: subprocess (TTS / loudnorm / probe_duration)
    FFmpeg-->>Voice: narration.wav (24kHz mono) + voice_duration (float)
    Voice-->>Studio: (voice_path, voice_duration)
    Studio->>DB: db.add(Asset(asset_type="audio"))

    Note over Studio,Avatar: Etapa 2: Animação de Avatar (Passe FFmpeg Intermediário)
    Studio->>Avatar: generate_avatar_video(voice_path, Path("avatar.mp4"))
    Avatar->>FFmpeg: probe_duration(voice_path)
    Avatar->>FFmpeg: ffmpeg -loop 1 -i creator_avatar.png -i narration.wav -> avatar.mp4 (360x360, yuv420p)
    FFmpeg-->>Avatar: avatar.mp4 + avatar_duration
    Avatar-->>Studio: (avatar_path, avatar_duration)
    Studio->>DB: db.add(Asset(asset_type="avatar"))

    Note over Studio,Subs: Etapa 3: Geração de Legendas ASS
    Studio->>Subs: build_cues_from_script(script_text, total_duration=voice_duration)
    Subs-->>Studio: list[SubtitleCue]
    Studio->>Subs: write_ass_subtitles(cues, Path("captions.ass"))
    Subs-->>Studio: subtitles_path (captions.ass)

    Note over Studio,Renderer: Etapa 4: Verificação de Source e Composição Final
    Studio->>Studio: _ensure_source_video(run_id, duration=max(voice_duration, 2.0))
    Studio->>FFmpeg: has_video_stream(source.mp4) [via ffprobe]
    Studio->>Renderer: render(source_video_path, avatar_path, voice_path, subtitles_path, output_path)
    Renderer->>FFmpeg: probe_duration(voice_audio_path)
    Renderer->>FFmpeg: has_video_stream(source_video_path)
    opt Sem stream de vídeo no source
        Renderer->>FFmpeg: Passe Fallback: lavfi color=#0f172a -> source_visual_bg.mp4
    end
    Renderer->>FFmpeg: Passe Final: scale/crop bg + scale/pad(white) avatar + overlay + ass -> final_reaction_9x16.mp4
    Renderer->>FFmpeg: probe_duration(final_reaction_9x16.mp4)
    Renderer-->>Studio: (final_video_path, final_duration)

    Studio->>DB: db.add(Asset(asset_type="final_video"))
    Studio->>DB: script.source_video.status = "produced"; db.commit(); db.refresh(final_asset)
    Studio-->>Celery: final_asset (Asset)
```

---

### 1.5 Especificação Conceitual de DTOs Tipados Internos (D-02 e D-03)

Para eliminar o tráfego de parâmetros primitivos descontextualizados (`Path`, `str`, `int`, `float`) e desacoplar responsabilidades nas Phases 10, 11 e 12 — **sem alterar a assinatura pública `StudioService.produce(db, run_id, script) -> Asset` (D-01)** e **sem introduzir injeção abstrata excessiva (D-03)** — especifica-se o conjunto enxuto de DTOs internos (baseados em `pydantic.BaseModel` / `dataclasses`):

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import uuid
from pydantic import BaseModel, Field


class SubtitleCue(BaseModel):
    """Unidade temporal de legenda (compatível com o modelo atual em subtitles.py,
    estendido opcionalmente para suportar destaque de palavra ativa na Phase 10)."""
    start: float = Field(..., ge=0.0, description="Início do cue em segundos")
    end: float = Field(..., gt=0.0, description="Fim do cue em segundos")
    text: str = Field(..., min_length=1, description="Texto visível do bloco")
    highlight_word: str | None = Field(default=None, description="Palavra de impacto para destaque amarelo ZUNTO!")


@dataclass(frozen=True)
class SubtitleJobConfig:
    """Configuração de geração e estilização do arquivo ASS (Phase 10)."""
    script_text: str
    total_duration: float
    output_path: Path
    brand_style: Literal["ZUNTO", "DEFAULT"] = "ZUNTO"
    max_words_per_cue: int = 4
    play_res_x: int = 1080
    play_res_y: int = 1920
    margin_v: int = 520  # Safe zone vertical calibrada acima da UI do TikTok/Reels/Shorts


@dataclass(frozen=True)
class AvatarConfig:
    """Especificação de dimensão, recorte orgânico e posicionamento do avatar (Phase 11).
    Também referenciado como AvatarJobConfig."""
    avatar_image_path: Path
    size: int = 340
    crop_mode: Literal["circle_alpha", "rounded_rect", "native_rgba"] = "circle_alpha"
    border_color: str = "#FACC15"  # Amarelo de impacto ZUNTO! (ou sem borda quadrada branca)
    border_width: int = 4
    overlay_x_expr: str = "W-w-48"
    overlay_y_expr: str = "H-h-380"  # Posicionado em safe zone sem colidir com legendas ou UI
    enable_waveform: bool = True
    waveform_color: str = "#FACC15@0.90"


@dataclass(frozen=True)
class ReactionCompositionSpec:
    """Especificação das camadas e parâmetros técnicos do grafo FFmpeg single-pass (Phase 12)."""
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 24
    video_codec: str = "libx264"
    preset: str = "veryfast"
    pix_fmt: str = "yuv420p"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    single_pass: bool = True


@dataclass(frozen=True)
class StudioRenderRequest:
    """DTO agregador que encapsula todos os insumos de uma requisição de renderização
    interna entre StudioService e ReactionVideoRenderer (equivalente a RenderJobContext)."""
    run_id: str | uuid.UUID
    source_video_path: Path
    voice_audio_path: Path
    voice_duration: float
    ass_subtitle_path: Path
    output_path: Path
    avatar: AvatarConfig
    composition: ReactionCompositionSpec = field(default_factory=ReactionCompositionSpec)
```

#### Como os DTOs Isolam a Complexidade sem Quebrar o Celery:
1. **`tasks.py` permanece 100% intocado:** Continua chamando `studio_service.produce(db=db, run_id=run.id, script=script)` e recebendo `Asset`.
2. **Eliminação de chamadas duplicadas ao `ffprobe`:** `voice_duration` é calculado uma única vez na síntese de voz e propagado dentro de `StudioRenderRequest` e `SubtitleJobConfig`.
3. **Prontidão para o Single-Pass (Phase 12):** Como `StudioRenderRequest` carrega `AvatarConfig` (apontando diretamente para `avatar_image_path` e parâmetros de `crop_mode` e `waveform`), o `ReactionVideoRenderer` pode compor o avatar estático/reativo diretamente no `filter_complex` principal sem depender obrigatoriamente de um arquivo `avatar.mp4` pré-renderizado em `yuv420p`.

---

## 2. Diagnóstico de Causa Raiz de Legendas Duplicadas (SUB-01)

*(Seção a ser detalhada no Plano 08-02)*

---

## 3. Diagnóstico de Assets e Formato do Avatar Reaction (AVTR-01)

*(Seção a ser detalhada no Plano 08-02)*

---

## 4. Grafo e Passes FFmpeg & Proposta Single-Pass (COMP-01)

*(Seção em elaboração na Task 2 do Plano 08-01)*

---

## 5. Matriz de Decisões e Plano de Implementação (Phases 9 a 12)

*(Seção a ser consolidada no Plano 08-02)*

---

## 6. Verificação de Integridade da Fase Diagnóstica

*(Seção a ser consolidada no Plano 08-02)*
