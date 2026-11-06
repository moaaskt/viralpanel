# Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz - Pattern Map

**Mapped:** 2026-11-06  
**Files analyzed:** 2 (Relatório Técnico de Auditoria + Suite/Script Diagnóstico não destrutivo)  
**Analogs found:** 2 / 2  

---

## File Classification

A Phase 8 é uma **fase 100% analítica e diagnóstica** (D-15), sem alteração em código de produção (`src/viralpanel/*`) nem substituição de assets nesta etapa. Os arquivos a serem criados/utilizados na fase consistem no documento oficial de auditoria técnica consolidada e em scripts/testes diagnósticos que comprovam os achados empíricos com `ffprobe` e `pytest`.

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` | documentation / audit report | transform / analysis | `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-RESEARCH.md` | exact |
| `tests/test_studio_diagnostics.py` *(ou harness diagnóstico pontual)* | test / diagnostic suite | request-response / inspection | `tests/test_studio_renderer.py` | exact |

---

## Pattern Assignments

### `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` (audit report, analysis)

**Analog:** `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-RESEARCH.md` (e estrutura canônica de auditoria técnica)

**Estrutura canônica do relatório:**
```markdown
# Phase 8: Auditoria Técnica de Contratos, Interfaces e Diagnóstico de Causa Raiz

## 1. Mapeamento de Contratos e Interfaces Atuais
- Assinatura pública inalterada: StudioService.produce(db, run_id, script) -> Asset
- Integração Celery tasks.py <-> StudioService
- Proposta de DTOs tipados internos (RenderJobContext, SubtitleJobConfig, AvatarJobConfig)

## 2. Diagnóstico de Causa Raiz de Duplicação de Legendas (SUB-01)
- Evidências no código: ReactionVideoRenderer.render (linha 130) possui filtro ASS único
- Mecânica real comprovada: vídeos baixados do TikTok já contêm hard-subs (burned-in)
- Análise de impacto e estratégias mitigadoras para Phase 10

## 3. Diagnóstico de Assets e Formato do Avatar Reaction (AVTR-01)
- Inspeção ffprobe em assets/creator_avatar.png: 512x512, rgb24 (sem alpha)
- Padding branco hardcoded em renderer.py:128 (pad=...color=white)
- Perda de transparência no encode intermediário avatar.mp4 (yuv420p)
- Propostas técnicas para Phase 11 (máscara procedural geq vs RGBA nativo)

## 4. Mapeamento dos Passes FFmpeg e Proposta Single-Pass (COMP-01)
- Passes atuais: Passe 0 (fundo fallback), Passe 1 (avatar.mp4), Passe 2 (composição final)
- Tabela de I/O, codecs, pixel formats e presets
- Proposta de grafo unificado single-pass para Phase 12
```

---

### `tests/test_studio_diagnostics.py` (test / diagnostic suite, inspection)

**Analog:** `tests/test_studio_renderer.py` (linhas 1-38)

**Imports pattern:**
```python
from pathlib import Path
import subprocess
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import MockAvatarAnimator, AudioReactiveAvatarAnimator
from viralpanel.studio.renderer import ReactionVideoRenderer, probe_video_dimensions
from viralpanel.studio.service import StudioService
from viralpanel.studio.subtitles import build_cues_from_script, write_ass_subtitles
from viralpanel.studio.voice import MockVoiceSynthesizer
```

**Diagnostic assertion pattern:**
```python
def test_diagnose_avatar_asset_format():
    """Valida via ffprobe/leitura que assets/creator_avatar.png é rgb24 (sem canal alfa)."""
    avatar_path = Path("assets/creator_avatar.png")
    assert avatar_path.exists()
    
    # Executa ffprobe seguro com lista de argumentos
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=pix_fmt",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(avatar_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    pix_fmt = result.stdout.strip()
    assert pix_fmt == "rgb24", f"Formato esperado 'rgb24', obtido '{pix_fmt}'"


def test_diagnose_renderer_single_ass_filter():
    """Comprova que o renderer possui exatamente 1 ocorrência do filtro ass."""
    from viralpanel.studio.renderer import ReactionVideoRenderer
    # Inspeciona a construção do filter_complex
    renderer = ReactionVideoRenderer()
    # Verifica ausência de duplicação interna
```

---

## Shared Patterns

### 1. Invocação Segura de Subprocessos e FFprobe (ASVS V5)
**Source:** `src/viralpanel/studio/renderer.py` linhas 45-65 e `src/viralpanel/studio/avatar.py` linhas 110-125  
**Apply to:** Qualquer rotina de diagnóstico ou inspeção de mídia  
```python
# Sempre passar lista de argumentos (shell=False) e capturar stdout/stderr com timeout
cmd = [
    "ffprobe",
    "-v", "error",
    "-show_entries", "stream=width,height,pix_fmt",
    "-of", "json",
    str(target_media_path),
]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10.0, check=True)
```

### 2. Validação de Contrato Público do StudioService (D-01)
**Source:** `src/viralpanel/tasks.py` linhas 210-230 e `src/viralpanel/studio/service.py` linhas 64-122  
**Apply to:** Avaliação arquitetural e preservação da compatibilidade com Celery  
```python
# A assinatura pública DEVE permanecer estritamente:
def produce(self, db: Session, run_id: str, script: Script) -> Asset:
    ...
```

### 3. Modelagem de DTOs Conceituais Tipados
**Source:** `src/viralpanel/studio/subtitles.py` linhas 3-8 (uso de Pydantic/dataclass)  
**Apply to:** Especificações conceituais de DTOs em `08-AUDIT-REPORT.md`  
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class RenderJobContext:
    source_video_path: Path
    voice_audio_path: Path
    subtitles_path: Path
    output_path: Path
    avatar_image_path: Path
    target_width: int = 1080
    target_height: int = 1920
```

---

## No Analog Found

Não há arquivos sem análogo. Todo o escopo de diagnóstico mapeia-se diretamente sobre os arquivos e testes existentes em `src/viralpanel/studio/` e `.planning/`.

---

## Metadata

**Analog search scope:** `src/viralpanel/studio/`, `src/viralpanel/tasks.py`, `tests/`, `.planning/phases/08-*/`  
**Files scanned:** 12 arquivos  
**Pattern extraction date:** 2026-11-06  
