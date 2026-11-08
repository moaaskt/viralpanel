"""Testes unitários para o módulo central de Branding ZUNTO! e conversão ASS."""
import pytest
from dataclasses import FrozenInstanceError

from viralpanel.branding import (
    BrandGuidelines,
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
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
    """Valida SafeZones9x16 para 1080x1920 alinhadas ao 08-AUDIT-REPORT.md Seção 3.5 per BRND-02."""
    safe = SafeZones9x16()
    assert safe.WIDTH == 1080
    assert safe.HEIGHT == 1920

    # Margens de segurança da UI mobile
    assert safe.TOP_MARGIN == 220
    assert safe.BOTTOM_MARGIN == 340
    assert safe.RIGHT_MARGIN == 140
    assert safe.LEFT_MARGIN == 48

    # Zonas verticais calibradas para legendas
    assert safe.SUBTITLE_Y_MIN == 1080
    assert safe.SUBTITLE_Y_MAX == 1280
    assert safe.SUBTITLE_MARGIN_V == 640

    # Avatar PIP
    assert safe.AVATAR_SIZE == 300
    assert safe.AVATAR_MARGIN_RIGHT == 54
    assert safe.AVATAR_MARGIN_BOTTOM == 320

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
