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
    split_script_into_cues,
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


def test_cue_chunking_punctuation_aware():
    """Valida segmentação sensível a pontuação e limites de retenção mobile (3-5 palavras)."""
    script = "Pare de esperar o momento ideal. Comece agora, mesmo sem motivação, e veja o resultado!"
    cues = split_script_into_cues(script, total_duration=8.0, min_words=3, max_words=5)

    assert len(cues) >= 3
    for cue in cues:
        word_count = len(cue.text.split())
        # Cada cue deve respeitar a cadência entre 2 e 6 palavras (meta de 3 a 5 palavras sem quebras artificiais)
        assert 2 <= word_count <= 6, f"Cue fora do intervalo rítmico: {cue.text!r}"

    # O texto concatenado deve conter todo o roteiro original
    reconstructed = " ".join(c.text for c in cues)
    for word in ["esperar", "ideal.", "Comece", "motivação,", "resultado!"]:
        assert word in reconstructed


def test_proportional_timing_allocation():
    """Valida alocação de tempo proporcional ao peso de caracteres e pausas."""
    # Frase 1: curta (10 chars, 1 ponto)
    # Frase 2: longa (58 chars, 1 vírgula, 1 ponto)
    script = "Comece já. A disciplina diária supera a motivação temporária de qualquer pessoa."
    cues = split_script_into_cues(script, total_duration=7.0, min_words=2, max_words=6)

    assert len(cues) >= 2
    # O primeiro cue é curto ("Comece já.")
    # Os cues subsequentes são mais longos
    cue_first = cues[0]
    cue_last = cues[-1]

    dur_first = cue_first.end - cue_first.start
    dur_last = cue_last.end - cue_last.start

    assert dur_first >= 0.8  # Piso mínimo
    assert dur_last > dur_first, f"Cue mais longo deve ter mais tempo: {dur_last} vs {dur_first}"


def test_temporal_contiguity_and_no_overlaps():
    """Valida contiguidade temporal estrita sem sobreposições e sem gaps."""
    script = (
        "Você não precisa de mais tempo. Precisa de foco implacável. "
        "A cada minuto perdido, sua concorrência dá mais um passo à frente."
    )
    total_duration = 9.4
    cues = split_script_into_cues(script, total_duration=total_duration, min_words=3, max_words=5)

    assert len(cues) > 1
    assert cues[0].start == 0.0

    for i in range(len(cues)):
        assert cues[i].start < cues[i].end, f"Cue {i} inválido: start >= end"
        if i > 0:
            # Contiguidade estrita sem gaps nem overlaps
            assert cues[i].start == pytest.approx(cues[i - 1].end, abs=1e-2)
            assert cues[i - 1].end <= cues[i].start

    assert cues[-1].end == pytest.approx(total_duration, abs=1e-2)


def test_timing_mode_metadata_and_word_timestamps():
    """Valida metadados de timing_mode com fallback heurístico e word timestamps."""
    script = "Aja agora mesmo."

    # Cenário 1: Fallback heurístico proporcional
    cues_heur = split_script_into_cues(script, total_duration=3.0)
    assert all(c.timing_mode == "proportional_character_estimate" for c in cues_heur)

    # Cenário 2: Word timestamps fornecidos explicitamente
    w_timestamps = [
        {"word": "Aja", "start": 0.2, "end": 0.8},
        {"word": "agora", "start": 0.85, "end": 1.6},
        {"word": "mesmo.", "start": 1.65, "end": 2.8},
    ]
    cues_aligned = split_script_into_cues(
        script,
        total_duration=3.0,
        word_timestamps=w_timestamps,
    )
    assert all(c.timing_mode == "word_timestamp_aligned" for c in cues_aligned)
    assert cues_aligned[0].start == pytest.approx(0.2, abs=0.05)
    assert cues_aligned[-1].end == pytest.approx(3.0, abs=0.05)


def test_build_cues_from_script_backwards_compatibility():
    """Valida que build_cues_from_script preserva compatibilidade delegando com sucesso."""
    cues = build_cues_from_script(
        "Foco diário constrói resultados duradouros.",
        total_duration=4.5,
        max_words_per_cue=5,
    )
    assert isinstance(cues, list)
    assert len(cues) >= 1
    assert all(isinstance(c, SubtitleCue) for c in cues)
    assert cues[0].start == 0.0
    assert cues[-1].end == pytest.approx(4.5, abs=0.05)

