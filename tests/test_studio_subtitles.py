from pathlib import Path
import pytest

from viralpanel.branding import (
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
)
from viralpanel.studio.subtitles import (
    SubtitleCue,
    SubtitleJobConfig,
    build_ass_header,
    build_cues_from_script,
    generate_subtitles,
    write_ass_subtitles,
)


def test_subtitle_job_config_defaults(tmp_path: Path):
    """Testa instanciação de SubtitleJobConfig com valores padrão ZUNTO!."""
    out = tmp_path / "captions.ass"
    config = SubtitleJobConfig(
        script_text="Texto do roteiro de alta retenção.",
        total_duration=5.0,
        output_path=out,
    )
    assert config.brand_style == "ZUNTO"
    assert config.max_words_per_cue == 5
    assert config.min_words_per_cue == 3
    assert config.margin_v == SafeZones9x16.SUBTITLE_MARGIN_V  # 640
    assert config.margin_v == 640
    assert config.box_padding == 16
    assert config.font_size == ZuntoTypography.SUBTITLE_FONT_SIZE  # 64
    assert config.font_name == ZuntoTypography.PRIMARY_FONT  # Montserrat
    assert config.play_res_x == 1080
    assert config.play_res_y == 1920
    assert config.timing_mode == "proportional_character_estimate"


def test_ass_header_zunto_style():
    """Valida que o cabeçalho ASS possui BorderStyle=3, MarginV=640 e cores ZUNTO!."""
    header = build_ass_header()

    assert "PlayResX: 1080" in header
    assert "PlayResY: 1920" in header
    assert "[V4+ Styles]" in header

    # Cores esperadas convertidas de branding.py
    expected_primary = hex_to_ass_color(ZuntoPalette.PURE_WHITE)       # &H00FFFFFF&
    expected_secondary = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)  # &H0015CCFA&
    expected_box = hex_to_ass_color(ZuntoPalette.DEEP_BLACK)           # &H000A0A0A&

    assert expected_primary == "&H00FFFFFF&"
    assert expected_secondary == "&H0015CCFA&"
    assert expected_box == "&H000A0A0A&"

    # Verificar linha Style
    style_lines = [line for line in header.splitlines() if line.startswith("Style: Default")]
    assert len(style_lines) == 1
    style = style_lines[0]

    # Style: Default,Montserrat,64,&H00FFFFFF,&H0015CCFA,&H000A0A0A,&H000A0A0A,-1,0,0,0,100,100,0,0,3,16,0,2,80,80,640,1
    tokens = style.replace("Style: ", "").split(",")
    # Formato dos campos:
    # 0: Name (Default)
    # 1: Fontname (Montserrat)
    # 2: Fontsize (64)
    # 3: PrimaryColour (&H00FFFFFF&)
    # 4: SecondaryColour (&H0015CCFA&)
    # 5: OutlineColour (&H000A0A0A&)
    # 6: BackColour (&H000A0A0A&)
    # 15: BorderStyle (3)
    # 16: Outline (16)
    # 17: Shadow (0)
    # 18: Alignment (2)
    # 21: MarginV (640)
    assert tokens[0] == "Default"
    assert tokens[2] == "64"
    assert tokens[3] == expected_primary
    assert tokens[4] == expected_secondary
    assert tokens[5] == expected_box
    assert tokens[6] == expected_box
    assert tokens[15] == "3"  # BorderStyle=3 (caixa opaca)
    assert tokens[16] == "16"  # Outline=16 (padding)
    assert tokens[17] == "0"  # Shadow=0
    assert tokens[18] == "2"  # Alignment=2 (Bottom-center)
    assert tokens[21] == "640"  # MarginV=640


def test_generate_subtitles_tracer_end_to_end(tmp_path: Path):
    """Teste tracer ponta a ponta gerando arquivo ASS válido em disco com estilo ZUNTO!."""
    out_file = tmp_path / "subtitles_zunto.ass"
    config = SubtitleJobConfig(
        script_text="Pare de procrastinar agora mesmo.",
        total_duration=3.0,
        output_path=out_file,
    )

    result_path = generate_subtitles(config)
    assert result_path == out_file
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "[V4+ Styles]" in content
    assert "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV" in content
    assert ",3,16,0,2,80,80,640,1" in content
    assert "Dialogue: 0," in content
