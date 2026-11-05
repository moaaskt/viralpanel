<!-- GSD:project-start source:PROJECT.md -->

## Project

**ViralPanel**

ViralPanel é um pipeline autônomo de geração e publicação de conteúdo viral para criadores solo. Ele automatiza 100% do ciclo de produção: descobre diariamente os vídeos em maior ascensão no TikTok dentro do nicho de desenvolvimento pessoal e motivação, extrai o tema e estrutura com Whisper, cria roteiros originais e persuasivos via Gemini 2.5 Flash, produz áudio com voz clonada (XTTS), monta o vídeo final vertical (9:16) com avatar virtual em formato reaction e legendas via FFmpeg, e agenda a publicação diretamente nas APIs oficiais do TikTok, Instagram Reels e YouTube Shorts.

**Core Value:** Automatizar 100% do ciclo de descoberta, produção e publicação de vídeos curtos de alta qualidade com consistência diária (meta de 6 vídeos por dia) e controle de qualidade supervisionado via Telegram, liberando o criador solo da rotina de produção manual.

### Constraints

- **Tech Stack**: Python 3.12, PostgreSQL, Redis, Celery, FFmpeg, React, Chakra UI, Docker Compose
- **LLM**: Google Gemini 2.5 Flash para geração de roteiros originais e estruturados
- **Áudio & Vídeo**: XTTS v2 para clonagem de voz, Whisper para transcrição, FFmpeg para renderização 9:16 e composição
- **Publicação**: APIs oficiais diretas (TikTok, Meta Graph API, YouTube Data API v3)
- **Design de UI**: Chakra UI com paleta limpa e profissional, estritamente sem neon

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
