"""Testes unitários e de renderização tipográfica para o módulo central de Branding ZUNTO!."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import re
import shutil
import subprocess
from typing import get_type_hints

import pytest

import viralpanel.branding as branding_module
from viralpanel.branding import (
    BrandGuidelines,
    FontResolutionError,
    ResolvedFont,
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
    resolve_typography_font,
)


def test_zunto_palette_constants():
    """Valida constantes da paleta oficial ZUNTO! per D-10 e BRND-01."""
    palette = ZuntoPalette()
    assert palette.DEEP_BLACK == "#0A0A0A"
    assert palette.IMPACT_YELLOW == "#FACC15"
    assert palette.PURE_WHITE == "#FFFFFF"
    assert palette.DARK_NEUTRAL == "#1A1A1A"

    # Valida imutabilidade
    with pytest.raises(FrozenInstanceError):
        palette.IMPACT_YELLOW = "#000000"


def test_zunto_typography_constants():
    """Valida especificações tipográficas calibradas para 1080x1920."""
    typography = ZuntoTypography()
    assert typography.PRIMARY_FONT == "Montserrat"
    assert typography.FALLBACK_FONT == "DejaVu Sans"
    assert typography.SUBTITLE_FONT_SIZE == 64
    assert typography.TITLE_FONT_SIZE == 84
    assert typography.SUBTITLE_MAX_CHARS_PER_LINE == 28
    assert typography.SUBTITLE_MAX_LINES == 2

    # Valida imutabilidade
    with pytest.raises(FrozenInstanceError):
        typography.SUBTITLE_FONT_SIZE = 48


def test_safe_zones_9x16_constants():
    """Valida SafeZones9x16 calibradas para Phase 13.2 como referências conservadoras configuráveis."""
    safe = SafeZones9x16()
    assert safe.WIDTH == 1080
    assert safe.HEIGHT == 1920

    # Referências conservadoras da UI mobile
    assert safe.TOP_MARGIN == 220
    assert safe.BOTTOM_MARGIN == 340
    assert safe.RIGHT_MARGIN == 140
    assert safe.LEFT_MARGIN == 48

    # Zonas calibradas de legendas no terço inferior
    assert safe.SUBTITLE_MARGIN_V == 420
    assert safe.SUBTITLE_MARGIN_RIGHT == 440
    assert safe.SUBTITLE_MARGIN_LEFT == 80
    assert safe.SUBTITLE_Y_MIN == 1340
    assert safe.SUBTITLE_Y_MAX == 1500

    # Avatar PIP calibrado (X in [680, 940], Y in [1360, 1620])
    assert safe.AVATAR_SIZE == 260
    assert safe.AVATAR_MARGIN_RIGHT == 140
    assert safe.AVATAR_MARGIN_BOTTOM == 300

    # Palco Cinematic Backdrop
    assert safe.STAGE_FG_Y_TOP == 240
    assert safe.STAGE_FG_MAX_H == 900
    assert safe.STAGE_BACKDROP_BLUR == "20:5"
    assert safe.STAGE_BACKDROP_BRIGHTNESS == -0.15
    assert safe.STAGE_BACKDROP_CONTRAST == 0.9

    # Valida tipagem Final em todas as constantes declaradas
    hints = get_type_hints(SafeZones9x16, include_extras=True)
    for field_name, hint in hints.items():
        assert "Final[" in str(hint), f"{field_name} deve ser tipado como Final[...], obtido {hint}"

    # Valida imutabilidade
    with pytest.raises(FrozenInstanceError):
        safe.SUBTITLE_MARGIN_V = 500


def test_brand_guidelines_constants():
    """Valida diretrizes de marca e slogan per D-02 e BRND-02."""
    guidelines = BrandGuidelines()
    assert guidelines.BRAND_NAME == "ZUNTO!"
    assert guidelines.SLOGAN == "Você não sabia. Agora sabe."
    assert "livre de clichês" in guidelines.TONE_OF_VOICE.lower()

    # Valida imutabilidade
    with pytest.raises(FrozenInstanceError):
        guidelines.BRAND_NAME = "OUTRO"


def test_hex_to_ass_color_zunto_palette():
    """Valida conversão de cores hexadecimais para ASS BGR (&HAABBGGRR&)."""
    # Amarelo ZUNTO! (#FACC15 -> R=FA, G=CC, B=15) -> &H0015CCFA&
    assert hex_to_ass_color("#FACC15") == "&H0015CCFA&"

    # Preto Profundo (#0A0A0A) -> &H000A0A0A&
    assert hex_to_ass_color("#0A0A0A") == "&H000A0A0A&"

    # Branco Puro (#FFFFFF) -> &H00FFFFFF&
    assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF&"

    # Cinza Escuro Neutro (#1A1A1A) -> &H001A1A1A&
    assert hex_to_ass_color("#1A1A1A") == "&H001A1A1A&"

    # Suporte a minúsculas
    assert hex_to_ass_color("#facc15") == "&H0015CCFA&"

    # Sem hashtag inicial
    assert hex_to_ass_color("FACC15") == "&H0015CCFA&"


def test_hex_to_ass_color_alpha_support():
    """Valida conversão com canal alpha customizado e formato 8 dígitos."""
    # Alpha explícito como argumento
    assert hex_to_ass_color("#FACC15", alpha_hex="80") == "&H8015CCFA&"
    assert hex_to_ass_color("#FACC15", alpha_hex="&H80") == "&H8015CCFA&"

    # Formato 8 dígitos #RRGGBBAA -> &HAABBGGRR&
    assert hex_to_ass_color("#FACC1580") == "&H8015CCFA&"
    assert hex_to_ass_color("FACC15FF") == "&HFF15CCFA&"


def test_hex_to_ass_color_invalid_input():
    """Valida tratamento de erro (ValueError) em formatos inválidos per T-09-01."""
    with pytest.raises(ValueError, match="Formato de cor Hex inválido"):
        hex_to_ass_color("")

    with pytest.raises(ValueError, match="Formato de cor Hex inválido"):
        hex_to_ass_color("#12345")  # 5 dígitos

    with pytest.raises(ValueError, match="Formato de cor Hex inválido"):
        hex_to_ass_color("#1234567")  # 7 dígitos

    with pytest.raises(ValueError, match="Formato de cor Hex inválido"):
        hex_to_ass_color("#GGFFFF")  # caracteres não hexadecimais

    with pytest.raises(ValueError, match="Formato de cor Hex inválido"):
        hex_to_ass_color("invalid_color")


def test_resolve_typography_font_returns_resolved_font_structure():
    """Valida que resolve_typography_font() retorna ResolvedFont imutável e válido."""
    resolved = resolve_typography_font()
    assert isinstance(resolved, ResolvedFont)
    assert resolved.font_path.is_file()
    assert resolved.fonts_dir.is_dir()
    assert resolved.font_path.parent == resolved.fonts_dir
    assert resolved.font_name in (ZuntoTypography.PRIMARY_FONT, ZuntoTypography.FALLBACK_FONT)
    assert resolved.variant in ("montserrat", "dejavu_sans")

    with pytest.raises(FrozenInstanceError):
        resolved.font_name = "Arial"


def test_resolve_typography_font_custom_dejavu_fallback(tmp_path):
    """Valida reconhecimento de variante DejaVu Sans quando caminho aponta para DejaVuSans-Bold.ttf."""
    fake_dejavu = tmp_path / "DejaVuSans-Bold.ttf"
    fake_dejavu.write_bytes(b"TTF-DUMMY")

    resolved = resolve_typography_font(custom_font_path=fake_dejavu)
    assert resolved.font_path == fake_dejavu.resolve()
    assert resolved.fonts_dir == fake_dejavu.resolve().parent
    assert resolved.font_name == "DejaVu Sans"
    assert resolved.variant == "dejavu_sans"


def test_resolve_typography_font_fail_closed(monkeypatch):
    """Política fail-closed: levanta FontResolutionError se nenhuma fonte homologada existir."""
    monkeypatch.setattr(branding_module.Path, "is_file", lambda self: False)

    with pytest.raises(FontResolutionError) as exc_info:
        resolve_typography_font()

    msg = str(exc_info.value)
    assert "Montserrat-Bold.ttf" in msg
    assert "DejaVuSans-Bold.ttf" in msg
    assert "fonts-dejavu-core" in msg
    assert "fonts-montserrat" in msg


def test_avatar_safe_zone_conformance():
    """Comprova X_avatar_min=680 e X_avatar_max=940, respeitando coluna lateral mobile (X<=940)."""
    safe = SafeZones9x16()
    x_avatar_min = safe.WIDTH - safe.AVATAR_SIZE - safe.AVATAR_MARGIN_RIGHT
    x_avatar_max = safe.WIDTH - safe.AVATAR_MARGIN_RIGHT

    assert x_avatar_min == 680
    assert x_avatar_max == 940
    assert x_avatar_max <= safe.WIDTH - safe.RIGHT_MARGIN


def test_avatar_vertical_conformance():
    """Comprova Y_avatar_min=1360 e Y_avatar_max=1620 acima da barra inferior mobile."""
    safe = SafeZones9x16()
    y_avatar_min = safe.HEIGHT - safe.AVATAR_SIZE - safe.AVATAR_MARGIN_BOTTOM
    y_avatar_max = safe.HEIGHT - safe.AVATAR_MARGIN_BOTTOM

    assert y_avatar_min == 1360
    assert y_avatar_max == 1620
    assert y_avatar_max <= safe.HEIGHT - safe.AVATAR_MARGIN_BOTTOM


def test_subtitle_and_avatar_no_overlap_with_outline():
    """Prova matemática: com MarginR=440 e box_padding=16, X_box_max=656 <= 680 - 24."""
    safe = SafeZones9x16()
    box_padding = 16
    x_text_max = safe.WIDTH - safe.SUBTITLE_MARGIN_RIGHT
    x_box_max = x_text_max + box_padding
    x_avatar_min = safe.WIDTH - safe.AVATAR_SIZE - safe.AVATAR_MARGIN_RIGHT

    assert x_text_max == 640
    assert x_box_max == 656
    assert x_avatar_min == 680
    assert x_avatar_min - x_box_max >= 24


def test_stage_fg_conformance():
    """Valida que o stage foreground respeita topo >= 220px e termina acima das legendas (< 1340px)."""
    safe = SafeZones9x16()
    assert safe.STAGE_FG_Y_TOP > safe.TOP_MARGIN
    assert safe.STAGE_FG_Y_TOP + safe.STAGE_FG_MAX_H == 1140
    assert safe.STAGE_FG_Y_TOP + safe.STAGE_FG_MAX_H < safe.SUBTITLE_Y_MIN


def test_subtitle_box_dimensions_with_real_font_measurement(tmp_path):
    """Valida via renderização ASS real FFmpeg/libass (fontselect + pixels rgb24) que a caixa <= 656px."""
    assert shutil.which("ffmpeg") is not None, "FFmpeg deve estar disponível no ambiente de teste."

    resolved_font = resolve_typography_font()
    safe = SafeZones9x16()
    box_padding = 16
    escaped_fontsdir = (
        str(resolved_font.fonts_dir).replace("\\", "/").replace(":", "\\:")
    )

    cues = [
        ("0:00:00.00", "0:00:01.00", "O desenvolvimento tecnológico extraordinariamente"),
        ("0:00:01.00", "0:00:02.00", "Transformação digital exige responsabilidade"),
        ("0:00:02.00", "0:00:03.00", "Decisão inconstitucionalmente contestada hoje"),
        ("0:00:03.00", "0:00:04.00", "Extraordinariamente relevante para você"),
        ("0:00:04.00", "0:00:05.00", "Desenvolvimento exige responsabilidade real"),
    ]

    forbidden_system_fallbacks = ("arial", "liberation", "tahoma", "segoe", "times new roman")

    for font_size in (58, 64):
        ass_path = tmp_path / f"subtitles_{font_size}.ass"
        raw_path = tmp_path / f"frame_{font_size}.rgb"

        events_lines = "\n".join(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
            for start, end, text in cues
        )
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {safe.WIDTH}
PlayResY: {safe.HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{resolved_font.font_name},{font_size},&H00FFFFFF&,&H0015CCFA&,&H000A0A0A&,&H000A0A0A&,-1,0,0,0,100,100,0,0,3,{box_padding},0,2,{safe.SUBTITLE_MARGIN_LEFT},{safe.SUBTITLE_MARGIN_RIGHT},{safe.SUBTITLE_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{events_lines}
"""
        ass_path.write_text(ass_content, encoding="utf-8")
        escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "verbose",
                "-f",
                "lavfi",
                "-i",
                f"color=c=magenta:s={safe.WIDTH}x{safe.HEIGHT}:r=1:d=5",
                "-vf",
                f"ass='{escaped_ass}':fontsdir='{escaped_fontsdir}'",
                "-frames:v",
                "5",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                str(raw_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        stderr = proc.stderr
        fontselect_lines = [line for line in stderr.splitlines() if "fontselect:" in line]
        assert fontselect_lines, f"Log fontselect do libass ausente no stderr:\n{stderr}"

        expected_pattern = re.compile(
            rf"fontselect:\s*\({re.escape(resolved_font.font_name)},\s*700,\s*0\)\s*->\s*.*{re.escape(resolved_font.font_path.stem)}",
            re.IGNORECASE,
        )
        assert any(expected_pattern.search(line) for line in fontselect_lines), (
            f"libass não selecionou a fonte esperada {resolved_font.font_path.stem}: {fontselect_lines}"
        )
        for line in fontselect_lines:
            lower_line = line.lower()
            for forbidden in forbidden_system_fallbacks:
                assert forbidden not in lower_line, (
                    f"Fallback espúrio detectado no fontselect: {line}"
                )

        if "Using font provider directwrite" in stderr:
            assert any(
                "Loading font file" in line and resolved_font.font_path.name in line
                for line in stderr.splitlines()
            ), f"Esperado log 'Loading font file' para {resolved_font.font_path.name}"

        raw_bytes = raw_path.read_bytes()
        frame_size = safe.WIDTH * safe.HEIGHT * 3
        assert len(raw_bytes) == frame_size * len(cues)

        x_avatar_min = safe.WIDTH - safe.AVATAR_SIZE - safe.AVATAR_MARGIN_RIGHT  # 680

        for cue_idx in range(len(cues)):
            frame_offset = cue_idx * frame_size
            max_x = -1
            min_x = safe.WIDTH
            box_pixels = 0

            # Inspeciona a metade inferior completa (Y=1000..1920) para máxima cobertura
            for y in range(1000, safe.HEIGHT):
                row_start = frame_offset + y * safe.WIDTH * 3
                for x in range(safe.WIDTH):
                    idx = row_start + x * 3
                    r = raw_bytes[idx]
                    g = raw_bytes[idx + 1]
                    b = raw_bytes[idx + 2]
                    # Fundo magenta puro = (255, 0, 255)
                    if abs(r - 255) > 15 or g > 15 or abs(b - 255) > 15:
                        if x > max_x:
                            max_x = x
                        if x < min_x:
                            min_x = x
                        if r < 30 and g < 30 and b < 30:
                            box_pixels += 1

            assert box_pixels > 200, (
                f"Fontsize {font_size}, cue {cue_idx}: caixa opaca #0A0A0A não detectada."
            )
            assert max_x <= 656, (
                f"Fontsize {font_size}, cue {cue_idx} ({cues[cue_idx][2]!r}): "
                f"pixel da caixa/texto atingiu X={max_x} > 656px (invasão da folga ao avatar em X={x_avatar_min})."
            )
            assert x_avatar_min - max_x >= 24, (
                f"Folga física inferior a 24px: max_x={max_x}, x_avatar_min={x_avatar_min}"
            )
            assert min_x >= safe.SUBTITLE_MARGIN_LEFT - box_padding - 4
