---
phase: 06-publica-o-direta-nas-apis-oficiais
plan: 01
status: success
requirements: [PUBL-04]
---
# Plan 06-01 Summary: Credenciais e Gerador de Metadados Multiplataforma

## Resultados Executados
- **Credenciais**: `PlatformCredentials` em `src/viralpanel/publishing/auth.py` gerenciando e validando disponibilidade de tokens para TikTok, Instagram (Meta Graph API) e YouTube (Data API v3) a partir de variáveis de ambiente.
- **Metadados & Hashtags**: `MetadataGenerator` em `src/viralpanel/publishing/metadata.py` gerando `PostMetadata` customizado por plataforma (limite de 100 caracteres e tag `#Shorts` para YouTube Shorts, legendas longas com `#reels` para Instagram e tags `#fyp`/`#viral` para TikTok).
- **Testes**: `tests/test_publishing_metadata.py` (2/2 passando).
