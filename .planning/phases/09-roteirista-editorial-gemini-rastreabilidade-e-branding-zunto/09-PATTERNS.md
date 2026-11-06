# Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO! - Pattern Map
**Mapped:** 2026-11-06  
**Files analyzed:** 6  
**Analogs found:** 6 / 6  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/viralpanel/branding.py` | config/utility | static-constants/transform | `src/viralpanel/idempotency.py` & `src/viralpanel/storage.py` | role-match |
| `src/viralpanel/models.py` | model | CRUD/ORM | `src/viralpanel/models.py` (linhas 33-46) | exact |
| `src/viralpanel/scripting/gemini.py` | service/provider | request-response | `src/viralpanel/scripting/gemini.py` | exact |
| `src/viralpanel/scripting/service.py` | service | request-response/pipeline | `src/viralpanel/scripting/service.py` | exact |
| `tests/test_branding.py` | test | unit/transform | `tests/test_publishing_metadata.py` | role-match |
| `tests/test_gemini_scripting.py` | test | unit/integration | `tests/test_gemini_scripting.py` | exact |

---

## Pattern Assignments

### `src/viralpanel/branding.py` (config/utility, static-constants/transform)

**Analog:** `src/viralpanel/idempotency.py` e `src/viralpanel/storage.py`

**Imports pattern**:
```python
from dataclasses import dataclass
from typing import Final
```

**Core Pattern (Classes imutáveis com `dataclass(frozen=True)` e constantes tipadas `Final`)**:
```python
@dataclass(frozen=True)
class ZuntoPalette:
    """Paleta de cores oficial da marca ZUNTO!."""
    DEEP_BLACK: Final[str] = "#0A0A0A"     # Preto profundo (fundo, caixas opacas)
    IMPACT_YELLOW: Final[str] = "#FACC15"  # Amarelo de alto impacto (destaques, bordas)
    PURE_WHITE: Final[str] = "#FFFFFF"     # Branco puro (texto primário, legendas)
    DARK_NEUTRAL: Final[str] = "#1A1A1A"   # Cinza escuro neutro (cards, detalhes secundários)


@dataclass(frozen=True)
class ZuntoTypography:
    """Especificações tipográficas para resolução base 1080x1920."""
    PRIMARY_FONT: Final[str] = "Montserrat"
    FALLBACK_FONT: Final[str] = "DejaVu Sans"
    SUBTITLE_FONT_SIZE: Final[int] = 64
    TITLE_FONT_SIZE: Final[int] = 84
    SUBTITLE_MAX_CHARS_PER_LINE: Final[int] = 28
    SUBTITLE_MAX_LINES: Final[int] = 2


@dataclass(frozen=True)
class SafeZones9x16:
    """Limites e coordenadas de safe zone em 1080x1920 para TikTok, Reels e Shorts."""
    WIDTH: Final[int] = 1080
    HEIGHT: Final[int] = 1920
    TOP_MARGIN: Final[int] = 220
    BOTTOM_MARGIN: Final[int] = 340
    RIGHT_MARGIN: Final[int] = 140
    LEFT_MARGIN: Final[int] = 48
    SUBTITLE_Y_MIN: Final[int] = 1080
    SUBTITLE_Y_MAX: Final[int] = 1280
    SUBTITLE_MARGIN_V: Final[int] = 640
    AVATAR_SIZE: Final[int] = 340
    AVATAR_MARGIN_RIGHT: Final[int] = 48
    AVATAR_MARGIN_BOTTOM: Final[int] = 260


@dataclass(frozen=True)
class BrandGuidelines:
    """Diretrizes editoriais e slogan da marca ZUNTO!."""
    BRAND_NAME: Final[str] = "ZUNTO!"
    SLOGAN: Final[str] = "Você não sabia. Agora sabe."
    TONE_OF_VOICE: Final[str] = (
        "Direto, maduro, confiante, provocativo e livre de clichês motivacionais rasos."
    )
```

**Data Transform & Validation pattern (`hex_to_ass_color`)**:
```python
def hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str:
    """Converte cor Hex (#RRGGBB ou #RRGGBBAA) para formato ASS BGR (&HAABBGGRR&)."""
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) == 6:
        r, g, b = cleaned[0:2], cleaned[2:4], cleaned[4:6]
        a = alpha_hex.strip().lstrip("&Hh")
        if len(a) != 2:
            a = "00"
    elif len(cleaned) == 8:
        r, g, b, a = cleaned[0:2], cleaned[2:4], cleaned[4:6], cleaned[6:8]
    else:
        raise ValueError(f"Formato de cor Hex inválido: {hex_color}. Esperado #RRGGBB ou #RRGGBBAA.")
    return f"&H{a.upper()}{b.upper()}{g.upper()}{r.upper()}&"
```

---

### `src/viralpanel/models.py` (model, CRUD/ORM)

**Analog:** `src/viralpanel/models.py` (linhas 1-46, `SourceVideo` e `Script`)

**Imports pattern** (linhas 4-6):
```python
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from viralpanel.database import Base
```

**Core Model pattern (`Script` com campo `metadata_json` retrocompatível)**:
```python
class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_video_id: Mapped[str] = mapped_column(ForeignKey("source_videos.id"), index=True)
    transcription: Mapped[str | None] = mapped_column(Text)
    script_text: Mapped[str | None] = mapped_column(Text)
    hook: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source_video: Mapped["SourceVideo"] = relationship(back_populates="scripts")
    assets: Mapped[list["Asset"]] = relationship(back_populates="script")
```

---

### `src/viralpanel/scripting/gemini.py` (service/provider, request-response)

**Analog:** `src/viralpanel/scripting/gemini.py` (linhas 1-170)

**Imports pattern** (linhas 1-12):
```python
import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from viralpanel.config import get_settings
from viralpanel.media.transcriber import TranscriptionResult
```

**Pydantic Schemas & OpenAPI Response Schema pattern** (linhas 45-68):
```python
class FactualClaim(BaseModel):
    """Afirmação factual identificada no roteiro com rastreabilidade."""
    claim: str = Field(..., description="Afirmação factual feita no roteiro")
    source_reference: str | None = Field(default=None, description="Referência ou contexto de origem")
    source_excerpt: str | None = Field(default=None, description="Trecho extraído da transcrição original")
    timestamp: str | None = Field(default=None, description="Timestamp de referência na transcrição")
    verification_status: str = Field(
        default="unverified_source_claim",
        description="Status de verificação (ex: unverified_source_claim, extracted_from_transcript)",
    )


class GeneratedScriptSchema(BaseModel):
    theme: str = ""
    hook: str = Field(min_length=3, description="Gancho nos primeiros 0-3s")
    body: str = Field(min_length=20, description="Desenvolvimento narrativo fluido")
    closing_thought: str = Field(default="", description="Fechamento narrativo natural")
    cta: str | None = Field(default=None, description="Chamada para ação opcional")
    estimated_duration_seconds: float = Field(ge=10, le=75)
    factual_claims: list[FactualClaim] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = [self.hook, self.body]
        if self.closing_thought:
            parts.append(self.closing_thought)
        if self.cta and self.cta.strip():
            parts.append(self.cta.strip())
        return "\n\n".join(parts)


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "theme": {"type": "STRING"},
        "hook": {"type": "STRING"},
        "body": {"type": "STRING"},
        "closing_thought": {"type": "STRING"},
        "cta": {"type": "STRING", "nullable": True},
        "estimated_duration_seconds": {"type": "NUMBER"},
        "factual_claims": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "claim": {"type": "STRING"},
                    "source_reference": {"type": "STRING", "nullable": True},
                    "source_excerpt": {"type": "STRING", "nullable": True},
                    "timestamp": {"type": "STRING", "nullable": True},
                    "verification_status": {"type": "STRING"},
                },
                "required": ["claim", "verification_status"],
            },
        },
    },
    "required": ["hook", "body", "closing_thought", "estimated_duration_seconds"],
}
```

**Retry & HTTP Error Handling pattern** (linhas 136-160):
```python
for attempt in range(1, self.max_retries + 1):
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            resp_data = json.loads(resp.read().decode())
        return resp_data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode() if exc.fp else "sem corpo de resposta"
        logger.warning(
            "Gemini API (%s) HTTP %d (Tentativa %d/%d): %s",
            self.model, exc.code, attempt, self.max_retries, err_body,
        )
        last_error = RuntimeError(f"Gemini API erro {exc.code} ({self.model}): {err_body}")
        if exc.code in (429, 500, 503):
            time.sleep(2 ** attempt)
            continue
        raise last_error from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("Falha de rede na chamada Gemini (%s, Tentativa %d/%d): %s", self.model, attempt, self.max_retries, exc)
        last_error = exc
        time.sleep(2 ** attempt)
        continue
```

---

### `src/viralpanel/scripting/service.py` (service, request-response/pipeline)

**Analog:** `src/viralpanel/scripting/service.py` (linhas 1-88)

**Imports pattern** (linhas 1-8):
```python
import logging
from sqlalchemy.orm import Session
from viralpanel.media.downloader import MediaDownloader
from viralpanel.media.transcriber import AudioTranscriber, MockTranscriber
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.scripting.gemini import ScriptWriter
```

**Core Pipeline & Metadata Persistence pattern** (linhas 61-75):
```python
generated = self.writer.generate(transcription, fallback_context=fallback_context)

# Extração de metadados editoriais e de rastreabilidade
metadata_payload = {
    "theme": generated.theme,
    "closing_thought": generated.closing_thought,
    "cta": generated.cta,
    "estimated_duration_seconds": generated.estimated_duration_seconds,
    "factual_claims": [claim.model_dump() for claim in generated.factual_claims],
    "brand": "ZUNTO!",
}

last_version = max((s.version for s in source.scripts), default=0)
script = Script(
    source_video_id=source.id,
    transcription=transcription.model_dump_json(),
    script_text=generated.full_text,
    hook=generated.hook,
    version=last_version + 1,
    metadata_json=metadata_payload,
)
db.add(script)
db.flush()
```

---

### `tests/test_branding.py` (test, unit/transform)

**Analog:** `tests/test_publishing_metadata.py` & `tests/test_models.py`

**Imports pattern**:
```python
import pytest
from viralpanel.branding import (
    BrandGuidelines,
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
)
```

**Unit Test patterns**:
```python
def test_hex_to_ass_color_conversions():
    # Amarelo ZUNTO! -> BGR 0015CCFA
    assert hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW) == "&H0015CCFA&"
    # Preto profundo -> BGR 000A0A0A
    assert hex_to_ass_color(ZuntoPalette.DEEP_BLACK) == "&H000A0A0A&"
    # Branco puro -> BGR 00FFFFFF
    assert hex_to_ass_color(ZuntoPalette.PURE_WHITE) == "&H00FFFFFF&"
    # Com alpha explícito
    assert hex_to_ass_color("#FACC15", alpha_hex="80") == "&H8015CCFA&"


def test_hex_to_ass_color_invalid_format():
    with pytest.raises(ValueError, match="Formato de cor Hex inválido"):
        hex_to_ass_color("invalid_color")


def test_safe_zones_and_guidelines_constants():
    assert SafeZones9x16.WIDTH == 1080
    assert SafeZones9x16.HEIGHT == 1920
    assert SafeZones9x16.SUBTITLE_MARGIN_V == 640
    assert BrandGuidelines.BRAND_NAME == "ZUNTO!"
    assert BrandGuidelines.SLOGAN == "Você não sabia. Agora sabe."
```

---

### `tests/test_gemini_scripting.py` (test, unit/integration)

**Analog:** `tests/test_gemini_scripting.py` (linhas 1-169)

**Imports pattern** (linhas 1-23):
```python
import json
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from viralpanel.database import Base
from viralpanel.media.downloader import MockMediaDownloader
from viralpanel.media.transcriber import AudioTranscriber, MockTranscriber, TranscriptionResult
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.scripting.gemini import (
    FallbackScriptWriter,
    GeminiScriptWriter,
    GeneratedScriptSchema,
    FactualClaim,
    GroqScriptWriter,
    MockGeminiScriptWriter,
    ScriptWriter,
)
from viralpanel.scripting.service import InsufficientSpeechError, ScriptingService
from viralpanel.storage import StorageManager
```

**Structured JSON Test pattern** (linhas 43-62 estendido para `closing_thought`, `cta: None` e `factual_claims`):
```python
def test_gemini_writer_parses_structured_json_with_factual_claims(monkeypatch):
    writer = GeminiScriptWriter(api_key="fake")
    payload = {
        "theme": "foco e dopamina",
        "hook": "Seu celular está roubando sua vida.",
        "body": "Cada notificação quebra seu foco por minutos seguidos no dia a dia.",
        "closing_thought": "Retome o controle da sua atenção agora.",
        "cta": None,
        "estimated_duration_seconds": 30,
        "factual_claims": [
            {
                "claim": "Notificações fragmentam a atenção por minutos",
                "source_reference": "Transcrição do vídeo original",
                "source_excerpt": "cada interrupção leva minutos para recuperar",
                "timestamp": "00:15",
                "verification_status": "extracted_from_transcript",
            }
        ],
    }

    monkeypatch.setattr(writer, "_call", lambda prompt: json.dumps(payload))
    out = writer.generate(MockTranscriber().transcribe(None))
    assert out.hook == payload["hook"]
    assert out.closing_thought == payload["closing_thought"]
    assert out.cta is None
    assert len(out.factual_claims) == 1
    assert out.factual_claims[0].claim == "Notificações fragmentam a atenção por minutos"
    assert "None" not in out.full_text
```

**Service Persistence Integration Test pattern** (linhas 64-85 estendido para `metadata_json`):
```python
def test_scripting_service_persists_script_with_metadata_json(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    svc = ScriptingService(
        MockMediaDownloader(storage=StorageManager(tmp_path)), MockTranscriber(), MockGeminiScriptWriter()
    )
    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@a/video/1", author="a", score=10)
        db.add(src)
        db.commit()
        script = svc.process(db, run_id="r1", source=src)
        assert script.metadata_json is not None
        assert "brand" in script.metadata_json
        assert script.metadata_json["brand"] == "ZUNTO!"
```

---

## Shared Patterns

### Structured Data Validation (Pydantic v2)
**Source:** `src/viralpanel/scripting/gemini.py` / `src/viralpanel/media/transcriber.py`  
**Apply to:** `GeneratedScriptSchema`, `FactualClaim` e schemas DTO da camada de scripting  
```python
from pydantic import BaseModel, Field

class FactualClaim(BaseModel):
    claim: str = Field(...)
    source_reference: str | None = Field(default=None)
    source_excerpt: str | None = Field(default=None)
    timestamp: str | None = Field(default=None)
    verification_status: str = Field(default="unverified_source_claim")
```

### In-Memory SQLite Testing Pattern
**Source:** `tests/test_gemini_scripting.py` (linhas 64-75) / `tests/test_models.py` (linhas 8-12)  
**Apply to:** Todos os testes unitários e de integração de models/services  
```python
eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
Base.metadata.create_all(eng)
factory = sessionmaker(bind=eng, expire_on_commit=False)
```

### Clean String Composition for Narration (TTS)
**Source:** `src/viralpanel/scripting/gemini.py` (`full_text` property)  
**Apply to:** Composição de texto para narração de roteiro sem vazamento de `None` ou quebras órfãs  
```python
parts = [self.hook, self.body]
if self.closing_thought:
    parts.append(self.closing_thought)
if self.cta and self.cta.strip():
    parts.append(self.cta.strip())
return "\n\n".join(parts)
```

---

## No Analog Found

Nenhum arquivo sem análogo. Todos os componentes possuem correspondentes diretos ou análogos estruturais com mesmo papel e fluxo de dados no repositório.

---

## Metadata

**Analog search scope:** `src/viralpanel/`, `tests/`  
**Files scanned:** 26 arquivos rastreados  
**Pattern extraction date:** 2026-11-06  
