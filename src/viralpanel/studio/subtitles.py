from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Final, Literal

from pydantic import BaseModel, Field

from viralpanel.branding import (
    ResolvedFont,
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
    resolve_typography_font,
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
STOPWORDS: Final[set[str]] = _PORTUGUESE_STOPWORDS


def _clean_token(tok: str) -> str:
    """Normaliza token removendo pontuação periférica e aplicando lowercase."""
    return re.sub(r"^[^\w]+|[^\w]+$", "", tok.lower())


def _alnum_token(tok: str) -> str:
    """Remove toda pontuação interna e periférica para comparar hífens/contrações."""
    return re.sub(r"[^\w]", "", tok.lower())


def _interpolate_segment(
    words: list[str],
    start_sec: float,
    end_sec: float,
    total_duration: float,
) -> list[dict]:
    """Distribui um intervalo [start_sec, end_sec] proporcionalmente ao peso em caracteres."""
    clamped_start = round(min(max(0.0, start_sec), total_duration), 3)
    clamped_end = round(min(max(clamped_start, end_sec), total_duration), 3)
    span = max(0.0, clamped_end - clamped_start)
    char_counts = [max(len(w), 1) for w in words]
    total_chars = max(sum(char_counts), 1)

    cur = clamped_start
    items: list[dict] = []
    for idx, (word, count) in enumerate(zip(words, char_counts)):
        if idx == len(words) - 1:
            w_end = clamped_end
        else:
            w_end = round(min(cur + (count / total_chars) * span, clamped_end), 3)
        w_start = round(min(cur, w_end), 3)
        items.append({
            "word": word,
            "start": w_start,
            "end": w_end,
            "duration": round(max(0.0, w_end - w_start), 3),
        })
        cur = w_end
    return items


def align_words_with_timestamps(
    script_words: list[str],
    word_timestamps: list[dict] | None,
    total_duration: float,
) -> list[dict]:
    """Alinha palavras do roteiro com eventos WordBoundary de forma sequencial, monotônica e desambiguada.

    - Trata pontuações periféricas, contrações e palavras compostas por hífen (1<->N e N<->1).
    - Desambiguação no lookahead: evita stopwords curtas (<= 2 caracteres ou em STOPWORDS)
      como âncoras isoladas e exige confirmação bi-gram em repetições ou stopwords.
    - Aplica clamp estrito em [0.0, total_duration] preservando ordem monotônica.
    """
    if not script_words:
        return []

    safe_total = max(float(total_duration), 0.0)
    if not word_timestamps:
        return _interpolate_segment(script_words, 0.0, safe_total, safe_total)

    aligned: list[dict] = []
    s_idx = 0
    wb_idx = 0
    num_script = len(script_words)
    num_wb = len(word_timestamps)
    last_end = 0.0

    while s_idx < num_script:
        word = script_words[s_idx]
        c_word = _clean_token(word)
        a_word = _alnum_token(word)

        if wb_idx >= num_wb:
            remaining = _interpolate_segment(script_words[s_idx:], last_end, safe_total, safe_total)
            aligned.extend(remaining)
            break

        wb = word_timestamps[wb_idx]
        c_wb = _clean_token(str(wb.get("word", "")))
        a_wb = _alnum_token(str(wb.get("word", "")))

        # 1. Correspondência exata após stripping de pontuação
        if c_word == c_wb or (a_word and a_word == a_wb):
            raw_start = float(wb.get("start", last_end))
            raw_end = float(wb.get("end", raw_start))
            start = round(min(max(last_end, raw_start), safe_total), 3)
            end = round(min(max(start, raw_end), safe_total), 3)
            aligned.append({
                "word": word,
                "start": start,
                "end": end,
                "duration": round(max(0.0, end - start), 3),
            })
            last_end = end
            s_idx += 1
            wb_idx += 1
            continue

        # 2. Fusão 1 script word <-> N speech events (ex: "guarda-chuva" ou "d'água")
        if a_wb and a_word and len(a_word) > len(a_wb) and a_word.startswith(a_wb):
            acc = a_wb
            scan_wb = wb_idx + 1
            while scan_wb < num_wb and len(acc) < len(a_word):
                next_a = _alnum_token(str(word_timestamps[scan_wb].get("word", "")))
                if not next_a or not a_word.startswith(acc + next_a):
                    break
                acc += next_a
                scan_wb += 1
            if acc == a_word:
                raw_start = float(wb.get("start", last_end))
                raw_end = float(word_timestamps[scan_wb - 1].get("end", raw_start))
                start = round(min(max(last_end, raw_start), safe_total), 3)
                end = round(min(max(start, raw_end), safe_total), 3)
                aligned.append({
                    "word": word,
                    "start": start,
                    "end": end,
                    "duration": round(max(0.0, end - start), 3),
                })
                last_end = end
                s_idx += 1
                wb_idx = scan_wb
                continue

        # 3. Fissão N script words <-> 1 speech event
        if a_word and a_wb and len(a_wb) > len(a_word) and a_wb.startswith(a_word):
            acc_s = a_word
            scan_s = s_idx + 1
            while scan_s < num_script and len(acc_s) < len(a_wb):
                next_sa = _alnum_token(script_words[scan_s])
                if not next_sa or not a_wb.startswith(acc_s + next_sa):
                    break
                acc_s += next_sa
                scan_s += 1
            if acc_s == a_wb and scan_s > s_idx + 1:
                raw_start = float(wb.get("start", last_end))
                raw_end = float(wb.get("end", raw_start))
                start = max(last_end, min(max(0.0, raw_start), safe_total))
                end = max(start, min(raw_end, safe_total))
                seg = _interpolate_segment(script_words[s_idx:scan_s], start, end, safe_total)
                aligned.extend(seg)
                last_end = seg[-1]["end"]
                s_idx = scan_s
                wb_idx += 1
                continue

        # 4. Lookahead Resync com desambiguação de stopwords e palavras repetidas
        best_anchor: tuple[int, int] | None = None
        best_score: tuple[int, int] = (999, 999)

        max_look_s = min(4, num_script - s_idx)
        max_look_wb = min(4, num_wb - wb_idx)

        for look_s in range(0, max_look_s):
            cand_s = _clean_token(script_words[s_idx + look_s])
            if not cand_s:
                continue
            for look_wb in range(0, max_look_wb):
                if look_s == 0 and look_wb == 0:
                    continue
                cand_wb = _clean_token(str(word_timestamps[wb_idx + look_wb].get("word", "")))
                if cand_s != cand_wb:
                    continue

                is_stopword = len(cand_s) <= 2 or cand_s in STOPWORDS
                has_prev_or_next_repeat = (
                    (s_idx + look_s + 1 < num_script and _clean_token(script_words[s_idx + look_s + 1]) == cand_s)
                    or (s_idx + look_s - 1 >= s_idx and _clean_token(script_words[s_idx + look_s - 1]) == cand_s)
                    or (wb_idx + look_wb + 1 < num_wb and _clean_token(str(word_timestamps[wb_idx + look_wb + 1].get("word", ""))) == cand_s)
                )

                has_next_s = (s_idx + look_s + 1) < num_script
                has_next_wb = (wb_idx + look_wb + 1) < num_wb
                bigram_confirmed = False

                if has_next_s and has_next_wb:
                    next_s = _clean_token(script_words[s_idx + look_s + 1])
                    next_wb = _clean_token(str(word_timestamps[wb_idx + look_wb + 1].get("word", "")))
                    bigram_confirmed = bool(next_s and next_s == next_wb)
                elif (not has_next_s) and (not has_next_wb):
                    bigram_confirmed = True

                if (is_stopword or has_prev_or_next_repeat) and not bigram_confirmed:
                    continue

                # Prefere âncora confirmada por bi-gram e de menor deslocamento (look_s + look_wb)
                score = (0 if bigram_confirmed else 1, look_s + look_wb)
                if score < best_score:
                    best_score = score
                    best_anchor = (look_s, look_wb)

        if best_anchor is not None:
            look_s, look_wb = best_anchor
            if look_s == 0:
                # Evento(s) de fala espúrio(s) descartado(s) antes da palavra atual do roteiro
                wb_idx += look_wb
                continue

            target_start = min(max(last_end, float(word_timestamps[wb_idx + look_wb].get("start", last_end))), safe_total)
            if look_s == 1 and look_wb == 1:
                # Substituição direta 1<->1 (ex: numeral "400" vs "quatrocentos")
                raw_start = float(wb.get("start", last_end))
                raw_end = float(wb.get("end", raw_start))
                start = round(min(max(last_end, raw_start), target_start, safe_total), 3)
                end = round(min(max(start, min(raw_end, target_start)), safe_total), 3)
                aligned.append({
                    "word": word,
                    "start": start,
                    "end": end,
                    "duration": round(max(0.0, end - start), 3),
                })
                last_end = end
            else:
                seg = _interpolate_segment(script_words[s_idx : s_idx + look_s], last_end, target_start, safe_total)
                aligned.extend(seg)
                last_end = seg[-1]["end"]
            s_idx += look_s
            wb_idx += look_wb
            continue

        # 5. Sem âncora no lookahead: consome par local com clamp estrito
        raw_start = float(wb.get("start", last_end))
        raw_end = float(wb.get("end", raw_start))
        start = round(min(max(last_end, raw_start), safe_total), 3)
        end = round(min(max(start, raw_end), safe_total), 3)
        aligned.append({
            "word": word,
            "start": start,
            "end": end,
            "duration": round(max(0.0, end - start), 3),
        })
        last_end = end
        s_idx += 1
        wb_idx += 1

    return aligned


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
    """Configuração de geração e estilização do arquivo ASS (Phase 10 / Phase 13.2)."""

    script_text: str
    total_duration: float
    output_path: Path
    brand_style: str = "ZUNTO"
    max_words_per_cue: int = 5
    min_words_per_cue: int = 3
    play_res_x: int = SafeZones9x16.WIDTH
    play_res_y: int = SafeZones9x16.HEIGHT
    margin_l: int = SafeZones9x16.SUBTITLE_MARGIN_LEFT
    margin_r: int = SafeZones9x16.SUBTITLE_MARGIN_RIGHT
    margin_v: int = SafeZones9x16.SUBTITLE_MARGIN_V
    box_padding: int = 16  # Outline no BorderStyle=3
    font_size: int = ZuntoTypography.SUBTITLE_FONT_SIZE  # 64
    font_name: str = ZuntoTypography.PRIMARY_FONT  # Montserrat
    fallback_font: str = ZuntoTypography.FALLBACK_FONT  # DejaVu Sans
    resolved_font: ResolvedFont | None = None
    timing_mode: str = "proportional_character_estimate"
    word_timestamps: list[dict] | None = None

    def __post_init__(self) -> None:
        if self.resolved_font is not None:
            object.__setattr__(self, "font_name", self.resolved_font.font_name)


def build_ass_header(config: SubtitleJobConfig | None = None) -> str:
    """Gera o cabeçalho e estilos ASS v4+ segundo a configuração e branding ZUNTO!."""
    play_res_x = config.play_res_x if config else SafeZones9x16.WIDTH
    play_res_y = config.play_res_y if config else SafeZones9x16.HEIGHT
    margin_l = config.margin_l if config else SafeZones9x16.SUBTITLE_MARGIN_LEFT
    margin_r = config.margin_r if config else SafeZones9x16.SUBTITLE_MARGIN_RIGHT
    margin_v = config.margin_v if config else SafeZones9x16.SUBTITLE_MARGIN_V
    box_padding = config.box_padding if config else 16
    font_size = config.font_size if config else ZuntoTypography.SUBTITLE_FONT_SIZE

    resolved = (
        config.resolved_font
        if (config is not None and config.resolved_font is not None)
        else resolve_typography_font()
    )
    font_name = resolved.font_name

    primary_color = hex_to_ass_color(ZuntoPalette.PURE_WHITE)       # &H00FFFFFF&
    box_color = hex_to_ass_color(ZuntoPalette.DEEP_BLACK)           # &H000A0A0A&
    secondary_color = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)  # &H0015CCFA&

    style_line = (
        f"Style: Default,{font_name},{font_size},"
        f"{primary_color},{secondary_color},{box_color},{box_color},"
        f"-1,0,0,0,100,100,0,0,3,{box_padding},0,2,{margin_l},{margin_r},{margin_v},1"
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


def _format_cs(cs: int) -> str:
    """Formata centésimos inteiros de segundo para carimbo temporal ASS (H:MM:SS.cs)."""
    safe_cs = max(int(cs), 0)
    centis = safe_cs % 100
    total_sec = safe_cs // 100
    secs = total_sec % 60
    total_min = total_sec // 60
    mins = total_min % 60
    hours = total_min // 60
    return f"{hours}:{mins:02d}:{secs:02d}.{centis:02d}"


def _format_ass_timestamp(seconds: float) -> str:
    return _format_cs(max(int(round(seconds * 100)), 0))


def _normalize_ass_color_tag(color: str) -> str:
    cleaned = color.strip()
    return cleaned if cleaned.endswith("&") else f"{cleaned}&"


def generate_word_karaoke_dialogue_events(
    cue_words: list[dict],
    yellow_ass_color: str,
    white_ass_color: str,
    total_audio_duration: float,
) -> list[str]:
    """Gera eventos Dialogue sequenciais por palavra ativa no estilo ZUNTO! Word Highlight.

    Invariantes:
    1. Exclusividade estrita: apenas a palavra ativa recebe o amarelo ZUNTO!, e as
       demais permanecem/retornam ao branco puro (sem tags \\k/\\kf).
    2. Piso visual de 50ms sem sobreposição (end_i <= start_{i+1}) e sem propagar drift
       cumulativo; a sincronização acústica real prevalece se a janela < 50ms.
    3. Pausas intra-bloco curtas (<= 120ms) estendem a palavra ativa; pausas longas
       (> 120ms) emitem evento neutro contíguo todo branco mantendo a caixa preta ativa.
    4. Contiguidade inteira em centésimos: event[k].end_cs == event[k+1].start_cs.
    """
    if not cue_words:
        return []

    safe_total = max(float(total_audio_duration), 0.0)
    yellow_tag = _normalize_ass_color_tag(yellow_ass_color)
    white_tag = _normalize_ass_color_tag(white_ass_color)
    num_words = len(cue_words)

    calibrated_words: list[dict] = []
    for i in range(num_words):
        raw_start = float(cue_words[i].get("start", 0.0))
        raw_end = float(cue_words[i].get("end", raw_start))
        start_i = min(max(0.0, raw_start), safe_total)
        end_i = min(max(start_i, raw_end), safe_total)

        if i + 1 < num_words:
            next_start = min(max(start_i, float(cue_words[i + 1].get("start", safe_total))), safe_total)
        else:
            next_start = safe_total

        available = max(0.0, next_start - start_i)
        if available < 0.05:
            effective_end = min(next_start, safe_total)
        else:
            effective_end = min(max(end_i, start_i + 0.05), next_start, safe_total)

        calibrated_words.append({
            "word": sanitize_ass_text(str(cue_words[i].get("word", ""))),
            "start": start_i,
            "end": effective_end,
            "duration": round(max(0.0, effective_end - start_i), 3),
        })

    sanitized_words = [w["word"] for w in calibrated_words]
    neutral_text = " ".join(sanitized_words)
    start_cs_list = [max(int(round(w["start"] * 100)), 0) for w in calibrated_words]
    end_cs_list = [max(int(round(w["end"] * 100)), start_cs_list[idx]) for idx, w in enumerate(calibrated_words)]

    dialogues: list[str] = []
    for i in range(num_words):
        start_cs = start_cs_list[i]
        end_cs = end_cs_list[i]

        if i + 1 < num_words:
            next_start_cs = start_cs_list[i + 1]
            # Garante invariante de não-sobreposição também após arredondamento em centésimos
            end_cs = min(max(start_cs, end_cs), next_start_cs)
            gap_cs = max(0, next_start_cs - end_cs)
        else:
            next_start_cs = end_cs
            gap_cs = 0

        if 0 < gap_cs <= 12:
            end_cs = next_start_cs

        formatted_tokens: list[str] = []
        for j, token in enumerate(sanitized_words):
            if j == i:
                formatted_tokens.append(f"{{\\c{yellow_tag}}}{token}{{\\c{white_tag}}}")
            else:
                formatted_tokens.append(token)
        dialogue_text = " ".join(formatted_tokens)

        dialogues.append(
            f"Dialogue: 0,{_format_cs(start_cs)},{_format_cs(end_cs)},Default,,0,0,0,,{dialogue_text}"
        )

        if gap_cs > 12:
            dialogues.append(
                f"Dialogue: 0,{_format_cs(end_cs)},{_format_cs(next_start_cs)},Default,,0,0,0,,{neutral_text}"
            )

    return dialogues


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


def _segment_words_into_chunks(
    words: list[str],
    min_words: int = 3,
    max_words: int = 5,
) -> list[list[str]]:
    """Segmenta palavras do roteiro em blocos rítmicos de 3 a 5 palavras sensíveis à pontuação."""
    chunks: list[list[str]] = []
    current_chunk: list[str] = []

    for i, word in enumerate(words):
        current_chunk.append(word)
        has_strong_punct = bool(re.search(r"[.!?]+$", word))
        has_pause_punct = bool(re.search(r"[,;:]+$", word))
        words_left = len(words) - (i + 1)

        if words_left == 0:
            break

        next_word = words[i + 1]
        next_has_strong = bool(re.search(r"[.!?]+$", next_word))

        if len(current_chunk) >= max_words:
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

    return chunks if chunks else [words]


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
    chunks = _segment_words_into_chunks(words, min_words=min_words, max_words=max_words)

    # 2. Alinhamento temporal com word_timestamps (quando disponível)
    if word_timestamps:
        aligned_ts = (
            word_timestamps
            if len(word_timestamps) >= len(words)
            else align_words_with_timestamps(words, word_timestamps, total_duration=total_duration)
        )
        logger.info(
            "Alinhando cues com word timestamps explícitos (timing_mode='word_timestamp_aligned')"
        )
        cues: list[SubtitleCue] = []
        word_idx = 0
        current_start = 0.0

        for chunk_idx, chunk in enumerate(chunks):
            chunk_len = len(chunk)
            chunk_ts = aligned_ts[word_idx : word_idx + chunk_len]
            word_idx += chunk_len

            start = float(chunk_ts[0].get("start", current_start))
            end = float(chunk_ts[-1].get("end", start + 1.0))

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
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    header = build_ass_header(config)
    lines = [header.rstrip()]

    words = [w.strip() for w in config.script_text.replace("\n", " ").split() if w.strip()]
    if words and config.word_timestamps:
        aligned_words = align_words_with_timestamps(
            words,
            config.word_timestamps,
            total_duration=config.total_duration,
        )
        chunks = _segment_words_into_chunks(
            words,
            min_words=config.min_words_per_cue,
            max_words=config.max_words_per_cue,
        )
        yellow_ass = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)
        white_ass = hex_to_ass_color(ZuntoPalette.PURE_WHITE)

        word_offset = 0
        for chunk in chunks:
            chunk_len = len(chunk)
            cue_words = aligned_words[word_offset : word_offset + chunk_len]
            word_offset += chunk_len
            lines.extend(
                generate_word_karaoke_dialogue_events(
                    cue_words=cue_words,
                    yellow_ass_color=yellow_ass,
                    white_ass_color=white_ass,
                    total_audio_duration=config.total_duration,
                )
            )
    else:
        cues = split_script_into_cues(
            script_text=config.script_text,
            total_duration=config.total_duration,
            min_words=config.min_words_per_cue,
            max_words=config.max_words_per_cue,
            word_timestamps=config.word_timestamps,
        )
        for cue in cues:
            lines.append(format_ass_dialogue_line(cue))

    config.output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config.output_path
