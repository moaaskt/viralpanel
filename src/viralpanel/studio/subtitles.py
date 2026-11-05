from pathlib import Path

from pydantic import BaseModel


class SubtitleCue(BaseModel):
    start: float
    end: float
    text: str


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,62,&H00FFFFFF,&H0000FFFF,&H00111827,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _format_ass_timestamp(seconds: float) -> str:
    total_cs = max(int(round(seconds * 100)), 0)
    cs = total_cs % 100
    total_sec = total_cs // 100
    secs = total_sec % 60
    total_min = total_sec // 60
    mins = total_min % 60
    hours = total_min // 60
    return f"{hours}:{mins:02d}:{secs:02d}.{cs:02d}"


def build_cues_from_script(script_text: str, total_duration: float, max_words_per_cue: int = 6) -> list[SubtitleCue]:
    words = [w.strip() for w in script_text.replace("\n", " ").split() if w.strip()]
    if not words:
        return [SubtitleCue(start=0.0, end=max(total_duration, 1.0), text="...")]

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
        cues.append(SubtitleCue(start=start, end=end, text=chunk))
    return cues


def write_ass_subtitles(cues: list[SubtitleCue], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [ASS_HEADER.rstrip()]
    for cue in cues:
        start_str = _format_ass_timestamp(cue.start)
        end_str = _format_ass_timestamp(cue.end)
        clean_text = cue.text.replace("\n", "\\N").replace("{", "").replace("}", "")
        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_text}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
