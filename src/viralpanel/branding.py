"""Módulo Central de Identidade Visual e Safe Zones da marca ZUNTO!.

Fonte única de verdade para constantes visuais, cores oficiais, safe zones 9:16
e conversão de cores para legendas e composição FFmpeg.
"""
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ZuntoPalette:
    """Paleta de cores oficial da marca ZUNTO!."""

    DEEP_BLACK: Final[str] = "#0A0A0A"     # Preto profundo (fundo, caixas opacas)
    IMPACT_YELLOW: Final[str] = "#FACC15"  # Amarelo de alto impacto (destaques, bordas, ênfases)
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

    # Margens de segurança da UI mobile (cabeçalho, barra inferior e botões laterais)
    TOP_MARGIN: Final[int] = 220       # Evitar ícones de busca, abas 'Seguindo/Para Você'
    BOTTOM_MARGIN: Final[int] = 340    # Evitar descrição, áudio giratório e barra de navegação
    RIGHT_MARGIN: Final[int] = 140     # Evitar botões de like, comentários, salvar e compartilhar
    LEFT_MARGIN: Final[int] = 48       # Margem lateral esquerda segura

    # Zonas verticais calibradas (homologadas na Seção 3.5 do 08-AUDIT-REPORT.md)
    # Legenda ZUNTO!: Y ≈ 1080px a 1280px (MarginV ≈ 640 a partir da base)
    SUBTITLE_Y_MIN: Final[int] = 1080
    SUBTITLE_Y_MAX: Final[int] = 1280
    SUBTITLE_MARGIN_V: Final[int] = 640

    # Avatar Reaction: Canto inferior direito acima da barra do TikTok
    # Posicionado em Y ≈ 1320px a 1660px, X ≈ 692px a 1032px (size=340px)
    AVATAR_SIZE: Final[int] = 340
    AVATAR_MARGIN_RIGHT: Final[int] = 48
    AVATAR_MARGIN_BOTTOM: Final[int] = 260


@dataclass(frozen=True)
class BrandGuidelines:
    """Diretrizes editoriais e slogan da marca ZUNTO!."""

    BRAND_NAME: Final[str] = "ZUNTO!"
    SLOGAN: Final[str] = "Você não sabia. Agora sabe."
    TONE_OF_VOICE: Final[str] = "Direto, maduro, confiante, provocativo e livre de clichês motivacionais rasos."


_HEX_CHARS = set("0123456789abcdefABCDEF")


def hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str:
    """Converte cor Hex (#RRGGBB ou #RRGGBBAA) para formato ASS BGR (&HAABBGGRR&).

    Args:
        hex_color: String contendo cor hexadecimal (ex: "#FACC15", "FACC15", "#FACC1580").
        alpha_hex: Canal alpha opcional de 2 dígitos em hexadecimal (padrão "00" = opaco no ASS).

    Returns:
        String formatada no padrão ASS BGR com delimitadores: &HAABBGGRR&.

    Raises:
        ValueError: Caso o formato hexadecimal seja inválido ou contenha caracteres não-hexadecimais.
    """
    cleaned = hex_color.strip().lstrip("#")
    if not cleaned or not all(c in _HEX_CHARS for c in cleaned):
        raise ValueError(
            f"Formato de cor Hex inválido: {hex_color!r}. Esperado #RRGGBB ou #RRGGBBAA com caracteres válidos."
        )

    if len(cleaned) == 6:
        r, g, b = cleaned[0:2], cleaned[2:4], cleaned[4:6]
        raw_a = alpha_hex.strip().lstrip("&Hh")
        if len(raw_a) == 2 and all(c in _HEX_CHARS for c in raw_a):
            a = raw_a
        else:
            a = "00"
    elif len(cleaned) == 8:
        r, g, b, a = cleaned[0:2], cleaned[2:4], cleaned[4:6], cleaned[6:8]
    else:
        raise ValueError(
            f"Formato de cor Hex inválido: {hex_color!r}. Esperado comprimento de 6 ou 8 dígitos hexadecimais."
        )

    return f"&H{a.upper()}{b.upper()}{g.upper()}{r.upper()}&"
