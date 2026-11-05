# Phase 6 Research: Publicação Direta nas APIs Oficiais

## 1. Escopo & Requisitos
- **PUBL-01**: Publicação e agendamento de vídeo no **TikTok** via **TikTok Content Posting API** oficial (`/v2/post/publish/video/init/`).
- **PUBL-02**: Publicação no **Instagram Reels** via **Meta Graph API** oficial (`/media` com `media_type=REELS` e container upload + `/media_publish`).
- **PUBL-03**: Publicação no **YouTube Shorts** via **YouTube Data API v3** (`/upload/youtube/v3/videos` com `#Shorts` e formato vertical).
- **PUBL-04**: Geração inteligente de metadados específicos para cada plataforma:
  - Título atraente (máx. 100 caracteres)
  - Descrição com gancho
  - Hashtags do nicho (#desenvolvimentopessoal, #motivacao, #foco, #shorts, #reels)
  - Persistência na tabela `publications` com status `scheduled`/`published` e respectivo URL final.

## 2. Decisões Técnicas e Arquitetura
1. **Modelagem de Tokens & Autenticação (`src/viralpanel/publishing/auth.py`)**:
   - `PlatformCredentials`: gerenciador de chaves e tokens OAuth2 das 3 plataformas (lidos de `.env` ou settings).
   - Suporte a verificação de expiração e refresh tokens.
2. **Formatador de Metadados Multiplataforma (`src/viralpanel/publishing/metadata.py`)**:
   - `MetadataGenerator`: recebe `Script` e gera `PostMetadata` contendo título, descrição, hashtags e limites de caracteres para cada rede (TikTok, Instagram, YouTube).
3. **Publicadores Modulares (`src/viralpanel/publishing/publishers/`)**:
   - `BasePublisher(ABC)` com método `publish(video_path: Path, metadata: PostMetadata, scheduled_for: datetime | None) -> PublicationResult`.
   - `TikTokPublisher` (TikTok Content Posting API)
   - `InstagramPublisher` (Meta Graph API)
   - `YouTubePublisher` (YouTube Data API v3)
   - `MockPublisher` determinístico para testes unitários offline e execução local.
4. **Serviço Orquestrador de Publicação (`src/viralpanel/publishing/service.py`)**:
   - `PublishingService`:
     - Disparado após aprovação (`approval_status == 'approved'`).
     - Distribui a postagem em paralelo ou sequencialmente para as 3 redes habilitadas.
     - Cria registros em `Publication` vinculados ao `Asset` final com status `published` ou `scheduled`.
     - Notifica o criador no Telegram com os links publicados.
5. **Integração no Celery (`src/viralpanel/tasks.py`)**:
   - Estágio final do pipeline `publishing`, fechando o ciclo autônomo completo de 6 vídeos diários.

## 3. Divisão de Planos
- **06-01-PLAN.md (Wave 1)**: Gerenciamento de credenciais OAuth2 das 3 plataformas e gerador de metadados/hashtags específicos (`MetadataGenerator`).
- **06-02-PLAN.md (Wave 2)**: Contrato `BasePublisher` e implementação dos publicadores TikTok, Instagram Reels e YouTube Shorts (com suporte a Mock).
- **06-03-PLAN.md (Wave 3)**: `PublishingService`, persistência na tabela `publications`, integração com Telegram e conexão no pipeline Celery `trigger_daily_pipeline`.
