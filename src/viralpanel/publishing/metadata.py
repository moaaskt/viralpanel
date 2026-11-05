from pydantic import BaseModel, Field
from viralpanel.models import Script


class PostMetadata(BaseModel):
    platform: str
    title: str = Field(max_length=120)
    description: str
    hashtags: list[str] = Field(default_factory=list)
    formatted_caption: str


class MetadataGenerator:
    DEFAULT_HASHTAGS = [
        "desenvolvimentopessoal",
        "motivacao",
        "disciplina",
        "mentalidade",
        "foco",
    ]

    PLATFORM_SPECIFIC_TAGS = {
        "tiktok": ["fyp", "paravoce", "viral"],
        "instagram": ["reels", "reelsbrasil", "motivacaodiaria"],
        "youtube": ["Shorts", "shortsbrasil"],
    }

    def generate(
        self,
        script: Script | str,
        platform: str,
        hook: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> PostMetadata:
        plat = platform.lower()
        if plat in ("reels", "insta"):
            plat = "instagram"
        elif plat in ("shorts", "yt"):
            plat = "youtube"

        if isinstance(script, Script):
            raw_text = script.script_text or script.hook or ""
            hook_text = hook or script.hook or ""
        else:
            raw_text = str(script)
            hook_text = hook or (raw_text.split("\n")[0] if raw_text else "")

        # Clean title from hook or first line
        title = hook_text.strip() or "Segredo para evoluir todos os dias"
        if len(title) > 90:
            title = title[:87] + "..."

        # Assemble hashtags
        tags = list(self.DEFAULT_HASHTAGS)
        if plat in self.PLATFORM_SPECIFIC_TAGS:
            tags.extend(self.PLATFORM_SPECIFIC_TAGS[plat])
        if extra_tags:
            tags.extend(extra_tags)

        # Unique tags preserving order
        seen = set()
        unique_tags = []
        for t in tags:
            clean_t = t.lstrip("#").strip()
            if clean_t and clean_t.lower() not in seen:
                seen.add(clean_t.lower())
                unique_tags.append(clean_t)

        hash_str = " ".join(f"#{t}" for t in unique_tags)

        if plat == "youtube":
            # YouTube Shorts requires or highly benefits from #Shorts in title/description
            yt_title = f"{title} #Shorts"
            if len(yt_title) > 100:
                yt_title = f"{title[:90]} #Shorts"
            description = f"{raw_text}\n\nInscreva-se no canal para vídeos diários!\n\n{hash_str}"
            caption = f"{yt_title}\n\n{description}"
            return PostMetadata(
                platform="youtube",
                title=yt_title,
                description=description,
                hashtags=unique_tags,
                formatted_caption=caption,
            )

        elif plat == "instagram":
            # Instagram Reels caption
            caption = f"{title}\n\n{raw_text}\n\nSiga para mais insights diários.\n\n{hash_str}"
            if len(caption) > 2200:
                caption = caption[:2197] + "..."
            return PostMetadata(
                platform="instagram",
                title=title,
                description=raw_text,
                hashtags=unique_tags,
                formatted_caption=caption,
            )

        else:  # tiktok default
            caption = f"{title} | {hash_str}"
            if len(caption) > 2200:
                caption = caption[:2197] + "..."
            return PostMetadata(
                platform="tiktok",
                title=title,
                description=raw_text,
                hashtags=unique_tags,
                formatted_caption=caption,
            )
