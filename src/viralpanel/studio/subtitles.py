from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal
import re

from pydantic import BaseModel, Field

from viralpanel.branding import (
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
)


class SubtitleCue(BaseModel):
    """Unidade temporal de legenda compatível com a v1.0 e enriquecida para ZUNTO!."""

    start: float = Field(..., ge=0.0, description="Início do cue em segundos")
    end: float = Field(..., gt=0.0, description="Fim do cue em segundos")
    text: str = Field(..., min_length=1, description="Texto visível do bloco")
    highlight_word: str | None = Field(
        default=None,
        description="Palavra de impacto para destaque amarelo ZUNTO!",
    )
    timing_mode: str = Field(
        default="proportional_character_estimate",
        description="Modo de temporização ('proportional_character_estimate' ou 'word_timestamp_aligned')",
    )


@dataclass(frozen=True)
class SubtitleJobConfig:
    """Configuração de geração e estilização do arquivo ASS (Phase 10)."""

    script_text: str
    total_duration: float
    output_path: Path
    brand_style: str = "ZUNTO"
    max_words_per_cue: int = 5
    min_words_per_cue: int = 3
    play_res_x: int = SafeZones9x16.WIDTH
    play_res_y: int = SafeZones9x16.HEIGHT
    margin_v: int = SafeZones9x16.SUBTITLE_MARGIN_V  # 640
    box_padding: int = 16  # Outline no BorderStyle=3
    font_size: int = ZuntoTypography.SUBTITLE_FONT_SIZE  # 64
    font_name: str = ZuntoTypography.PRIMARY_FONT  # Montserrat
    fallback_font: str = ZuntoTypography.FALLBACK_FONT  # DejaVu Sans
    timing_mode: str = "proportional_character_estimate"
    word_timestamps: list[dict] | None = None


def build_ass_header(config: SubtitleJobConfig | None = None) -> str:
    """Gera o cabeçalho e estilos ASS v4+ segundo a configuração e branding ZUNTO!."""
    play_res_x = config.play_res_x if config else SafeZones9x16.WIDTH
    play_res_y = config.play_res_y if config else SafeZones9x16.HEIGHT
    margin_v = config.margin_v if config else SafeZones9x16.SUBTITLE_MARGIN_V
    box_padding = config.box_padding if config else 16
    font_size = config.font_size if config else ZuntoTypography.SUBTITLE_FONT_SIZE
    font_name = config.font_name if config else ZuntoTypography.PRIMARY_FONT

    primary_color = hex_to_ass_color(ZuntoPalette.PURE_WHITE)       # &H00FFFFFF&
    box_color = hex_to_ass_color(ZuntoPalette.DEEP_BLACK)           # &H000A0A0A&
    secondary_color = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)  # &H0015CCFA&

    style_line = (
        f"Style: Default,{font_name},{font_size},"
        f"{primary_color},{secondary_color},{box_color},{box_color},"
        f"-1,0,0,0,100,100,0,0,3,{box_padding},0,2,80,80,{margin_v},1"
    )

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


ASS_HEADER: Final[str] = build_ass_header()


def _format_ass_timestamp(seconds: float) -> str:
    total_cs = max(int(round(seconds * 100)), 0)
    cs = total_cs % 100
    total_sec = total_cs // 100
    secs = total_sec % 60
    total_min = total_sec // 60
    mins = total_min % 60
    hours = total_min // 60
    return f"{hours}:{mins:02d}:{secs:02d}.{cs:02d}"


def build_cues_from_script(
    script_text: str, total_duration: float, max_words_per_cue: int = 6
) -> list[SubtitleCue]:
    words = [w.strip() for w in script_text.replace("\n", " ").split() if w.strip()]
    if not words:
        return [
            SubtitleCue(
                start=0.0,
                end=max(total_duration, 1.0),
                text="...",
                timing_mode="proportional_character_estimate",
            )
        ]

    chunks: list[str] = []
    for i in range(0, len(words), max_words_per_cue):
        chunks.append(" ".join(words[i : i + max_words_per_cue]))

    duration = max(total_duration, 1.0)
    step = duration / len(chunks)
    cues: list[SubtitleCue] = []
    for idx, chunk in enumerate(chunks):
        start = round(idx * step, 2)
        end = round(min((idx + 1) * step, duration), 2)
        if end <= start:
            end = round(start + 0.5, 2)
        cues.append(
            SubtitleCue(
                start=start,
                end=end,
                text=chunk,
                timing_mode="proportional_character_estimate",
            )
        )
    return cues


def write_ass_subtitles(cues: list[SubtitleCue], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = build_ass_header()
    lines = [header.rstrip()]
    for cue in cues:
        start_str = _format_ass_timestamp(cue.start)
        end_str = _format_ass_timestamp(cue.end)
        clean_text = cue.text.replace("\n", "\\N").replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_text}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def generate_subtitles(config: SubtitleJobConfig) -> Path:
    """Gera o arquivo de legendas .ass estruturado a partir da configuração de job."""
    cues = build_cues_from_script(
        config.script_text,
        config.total_duration,
        max_words_per_cue=config.max_words_per_cue,
    )
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    header = build_ass_header(config)
    lines = [header.rstrip()]
    for cue in cues:
        start_str = _format_ass_timestamp(cue.start)
        end_str = _format_ass_timestamp(cue.end)
        clean_text = cue.text.replace("\n", "\\N").replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_text}")
    config.output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config.output_path
