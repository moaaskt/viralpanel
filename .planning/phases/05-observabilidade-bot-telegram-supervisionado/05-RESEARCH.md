# Phase 5 Research: Observabilidade & Bot Telegram Supervisionado

## 1. Escopo & Requisitos
- **TELE-01**: Envio de notificações estruturadas em tempo real para o criador via Telegram Bot (status de início de run, discovery concluído, roteiro gerado, renderização pronta ou eventuais erros).
- **TELE-02**: Envio de preview do vídeo vertical 9:16 final diretamente no chat do Telegram acompanhado de teclado inline com botões interativos `Aprovar ✅` e `Rejeitar ❌`.
- **TELE-03**: Modo supervisionado configurável (`SUPERVISED_MODE=true/false`): quando ativo, a esteira entra em espera por decisão humana (armazenada no banco / Redis) antes de liberar a etapa de agendamento e publicação da Fase 6.

## 2. Decisões Técnicas e Arquitetura
1. **Cliente Telegram REST Nativo (`src/viralpanel/telegram/client.py`)**:
   - Para manter a arquitetura lean e sem dependências pesadas externas, implementar cliente HTTP sobre `urllib.request` interagindo diretamente com a Telegram Bot API oficial:
     - `send_message(chat_id, text, reply_markup=None)`
     - `send_video(chat_id, video_path, caption, reply_markup=None)`
     - `answer_callback_query(callback_query_id, text)`
   - Suporte a `MockTelegramClient` para testes unitários offline e execução local determinística sem token real.
2. **Serviço de Observabilidade & Notificações (`src/viralpanel/telegram/notifier.py`)**:
   - `TelegramNotifier`: formatação rica com MarkdownV2 ou HTML para relatórios de progresso do pipeline diário, tempos de execução e métricas de viralidade do vídeo selecionado.
3. **Mecanismo de Aprovação Supervisionada (`src/viralpanel/telegram/approval.py` & `service.py`)**:
   - Armazena estado da aprovação (`pending`, `approved`, `rejected`) vinculado ao `PipelineRun` e `Asset` final.
   - Callback handler para processar cliques de botão do criador: `approve:{run_id}` ou `reject:{run_id}`.
   - Polling / Webhook handler para receber updates da Telegram Bot API.
4. **Integração com Celery (`src/viralpanel/tasks.py`)**:
   - Novo estágio `supervision`:
     - Se `supervised_mode=False`: aprovação automática direta.
     - Se `supervised_mode=True`: envia vídeo preview ao Telegram com botões e aguarda aprovação humana (ou marca status como `awaiting_approval`).

## 3. Divisão de Planos
- **05-01-PLAN.md (Wave 1)**: Cliente Telegram Bot nativo, configurações em `Settings` e `TelegramNotifier` estruturado com suporte a Mock.
- **05-02-PLAN.md (Wave 2)**: Teclado inline com Aprovar/Rejeitar, envio de preview de vídeo 9:16, polling de callbacks e integração na task Celery com flag de modo supervisionado.

