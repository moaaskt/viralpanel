from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Final, Literal

from pydantic import BaseModel, Field

from viralpanel.branding import (
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
)

logger = logging.getLogger(__name__)

# Stopwords comuns em português para heurística de palavras de impacto
_PORTUGUESE_STOPWORDS: Final[set[str]] = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "pelo", "pela", "pelos", "pelas", "com", "para", "pra", "pro",
    "sem", "sob", "sobre", "ate", "até", "ao", "aos",
    "e", "ou", "mas", "se", "que", "como", "porque", "pois", "nem",
    "eu", "tu", "ele", "ela", "nos", "nós", "eles", "elas", "me", "te", "lhe",
    "isso", "isto", "aquilo", "seu", "sua", "seus", "suas",
    "é", "foi", "ser", "sao", "são", "tem", "vai", "ter",
}


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


def sanitize_ass_text(text: str) -> str:
    """Sanitiza o texto eliminando colisões com delimitadores de controle ASS.

    Substitui '{' por '(' e '}' por ')' para impedir injeção acidental no libass.
    Normaliza quebras de linha para '\\N'.
    """
    safe = text.replace("{", "(").replace("}", ")")
    safe = safe.replace("\r\n", "\\N").replace("\n", "\\N").replace("\r", "\\N")
    return safe


def select_highlight_word(words: list[str]) -> str | None:
    """Heurística para seleção da palavra de destaque de maior impacto semântico."""
    clean_words = [re.sub(r"[^\wáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]", "", w) for w in words]
    candidates = [
        w for w in clean_words
        if len(w) >= 4 and w.lower() not in _PORTUGUESE_STOPWORDS
    ]
    if candidates:
        return candidates[0]
    valid = [w for w in clean_words if w]
    return max(valid, key=len) if valid else None


def format_ass_dialogue_line(cue: SubtitleCue) -> str:
    """Formata a linha Dialogue com escape blindado e destaque amarelo com fechamento explícito."""
    sanitized = sanitize_ass_text(cue.text)
    start_str = _format_ass_timestamp(cue.start)
    end_str = _format_ass_timestamp(cue.end)

    yellow_ass = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)  # &H0015CCFA&
    white_ass = hex_to_ass_color(ZuntoPalette.PURE_WHITE)      # &H00FFFFFF&

    highlight = cue.highlight_word or select_highlight_word(sanitized.split())

    if highlight and highlight.lower() in sanitized.lower():
        pattern = re.compile(rf"\b({re.escape(highlight)})\b", re.IGNORECASE)
        formatted_text = pattern.sub(
            rf"{{\\c{yellow_ass}}}\1{{\\c{white_ass}}}", sanitized, count=1
        )
    else:
        formatted_text = sanitized

    return f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{formatted_text}"


def split_script_into_cues(
    script_text: str,
    total_duration: float,
    min_words: int = 3,
    max_words: int = 5,
    word_timestamps: list[dict] | None = None,
) -> list[SubtitleCue]:
    """Segmenta o roteiro em blocos sintáticos naturais e aloca duração proporcional.

    - Respeita pausas fortes (. ! ?) e pausas moderadas (, ; :) mantendo 3 a 5 palavras por cue.
    - Distribui o tempo proporcionalmente ao peso de caracteres e pausas (D-02).
    - Assegura contiguidade sequencial estrita sem sobreposições ou gaps.
    - Suporta word_timestamps opcionais quando disponíveis.
    """
    words = [w.strip() for w in script_text.replace("\n", " ").split() if w.strip()]
    if not words:
        return [
            SubtitleCue(
                start=0.0,
                end=max(round(total_duration, 2), 1.0),
                text="...",
                timing_mode="proportional_character_estimate",
            )
        ]

    # 1. Segmentação em blocos rítmicos orientados a pontuação
    chunks: list[list[str]] = []
    current_chunk: list[str] = []

    for i, word in enumerate(words):
        current_chunk.append(word)
        has_strong_punct = bool(re.search(r"[.!?]+$", word))
        has_pause_punct = bool(re.search(r"[,;:]+$", word))
        words_left = len(words) - (i + 1)

        if words_left == 0:
            break

        # Próxima palavra tem pontuação forte ou moderada?
        next_word = words[i + 1]
        next_has_strong = bool(re.search(r"[.!?]+$", next_word))

        if len(current_chunk) >= max_words:
            # Se a próxima palavra fecha uma frase imediatamente e o chunk ainda cabe com +1, junta
            if next_has_strong and len(current_chunk) < max_words + 2:
                continue
            chunks.append(current_chunk)
            current_chunk = []
        elif has_strong_punct and len(current_chunk) >= min_words:
            chunks.append(current_chunk)
            current_chunk = []
        elif has_pause_punct and len(current_chunk) >= min_words and words_left >= min_words:
            chunks.append(current_chunk)
            current_chunk = []
        elif has_strong_punct and len(current_chunk) >= 2 and words_left >= min_words:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        if len(current_chunk) < min_words and chunks:
            if len(chunks[-1]) + len(current_chunk) <= max_words + 2:
                chunks[-1].extend(current_chunk)
            else:
                chunks.append(current_chunk)
        else:
            chunks.append(current_chunk)

    if not chunks:
        chunks = [words]

    # 2. Alinhamento temporal com word_timestamps (quando disponível)
    if word_timestamps and len(word_timestamps) >= len(words):
        logger.info(
            "Alinhando cues com word timestamps explícitos (timing_mode='word_timestamp_aligned')"
        )
        cues: list[SubtitleCue] = []
        word_idx = 0
        current_start = 0.0

        for chunk_idx, chunk in enumerate(chunks):
            chunk_len = len(chunk)
            chunk_ts = word_timestamps[word_idx : word_idx + chunk_len]
            word_idx += chunk_len

            start = chunk_ts[0].get("start", current_start)
            end = chunk_ts[-1].get("end", start + 1.0)

            # Manter contiguidade estrita
            start = round(max(start, current_start), 2)
            if chunk_idx == len(chunks) - 1:
                end = round(max(end, total_duration), 2)
            else:
                end = round(max(end, start + 0.5), 2)

            cues.append(
                SubtitleCue(
                    start=start,
                    end=end,
                    text=" ".join(chunk),
                    timing_mode="word_timestamp_aligned",
                )
            )
            current_start = end
        return cues

    # 3. Fallback: Temporização proporcional por caracteres e pausas
    logger.info(
        "Calculando temporização proporcional por caracteres para %d cues (timing_mode='proportional_character_estimate')",
        len(chunks),
    )

    weights: list[float] = []
    for chunk in chunks:
        chunk_text = " ".join(chunk)
        commas = chunk_text.count(",") + chunk_text.count(";") + chunk_text.count(":")
        periods = chunk_text.count(".") + chunk_text.count("!") + chunk_text.count("?")
        w = float(len(chunk_text) + (commas * 4) + (periods * 7))
        weights.append(max(w, 1.0))

    total_weight = sum(weights)
    min_cue_dur = 0.8

    if total_duration >= len(chunks) * min_cue_dur:
        remaining_duration = total_duration - (len(chunks) * min_cue_dur)
        durations = [
            min_cue_dur + ((w / total_weight) * remaining_duration) for w in weights
        ]
    else:
        durations = [(w / total_weight) * total_duration for w in weights]

    cues = []
    current_time = 0.0
    for i, (chunk, dur) in enumerate(zip(chunks, durations)):
        is_last = i == len(chunks) - 1
        start = round(current_time, 2)
        if is_last:
            end = round(total_duration, 2)
        else:
            end = round(current_time + dur, 2)

        if end <= start:
            end = round(start + 0.5, 2)

        cues.append(
            SubtitleCue(
                start=start,
                end=end,
                text=" ".join(chunk),
                timing_mode="proportional_character_estimate",
            )
        )
        current_time = end

    return cues


def build_cues_from_script(
    script_text: str, total_duration: float, max_words_per_cue: int = 6
) -> list[SubtitleCue]:
    """Constrói cues de legendas delegando para split_script_into_cues (v1.0 compatível)."""
    min_words = max(2, max_words_per_cue // 2)
    return split_script_into_cues(
        script_text=script_text,
        total_duration=total_duration,
        min_words=min_words,
        max_words=max_words_per_cue,
    )


def write_ass_subtitles(cues: list[SubtitleCue], output_path: Path) -> Path:
    """Grava arquivo ASS v4+ estruturado segundo o branding ZUNTO!."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = build_ass_header()
    lines = [header.rstrip()]
    for cue in cues:
        lines.append(format_ass_dialogue_line(cue))
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def generate_subtitles(config: SubtitleJobConfig) -> Path:
    """Gera o arquivo de legendas .ass estruturado a partir da configuração de job."""
    cues = split_script_into_cues(
        script_text=config.script_text,
        total_duration=config.total_duration,
        min_words=config.min_words_per_cue,
        max_words=config.max_words_per_cue,
        word_timestamps=config.word_timestamps,
    )
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    header = build_ass_header(config)
    lines = [header.rstrip()]
    for cue in cues:
        lines.append(format_ass_dialogue_line(cue))
    config.output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config.output_path
