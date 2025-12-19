# Secrets Moderation Pipeline

## Overview
- Пайплайн принимает отчёты сканеров секретов (SARIF/JSON: gitleaks, semgrep и др.), приводит их к единому формату и запускает модерацию, чтобы отфильтровать ложные срабатывания.
- Сервисы: orchestrator (FastAPI, выдаёт JWT, ставит задачи, вызывает нормализацию и модерацию), 
report_injestor (нормализует отчёты разных сканеров), moderator (эвристики + CharCNN ONNX + опционально Qwen LLM), audit (собирает аудиты в logs/audit.jsonl).
- Все сервисы поднимаются через docker-compose, общаются по HTTP внутри сети mws-network и могут логировать единый 	race_id.

## Data
- CredData: основной репозиторий с датасетом и подготовкой артефактов моделей — https://github.com/Samsung/CredData.
- Готовые train/test и артефакты моделей лежат на Я.Диске: https://disk.yandex.ru/d/HqokzI5PNlMHAQ.

## How to use
### Требования
- Docker + Docker Compose.
- Переменные окружения (для docker-compose): QWEN_API_KEY (ключ для LLM), JWT_SECRET_KEY/JWT_EXPIRATION_HOURS, CNN_MODEL_DIR, CNN_MAX_LEN, CNN_THRESHOLD, REPORT_INJESTOR_DEBUG.

### Сборка образов

`bash
docker compose build
`

### Запуск сервисов

`bash
QWEN_API_KEY="<your_token>" \
JWT_SECRET_KEY="<secret>" \
docker compose up -d
`

Порты по умолчанию: orchestrator 8000, moderator 8001, report-injector 8002, audit 8003.

### Отправка отчёта на анализ
1) Получить токен:

`bash
TOKEN=
`
3) Отправить SARIF/JSON:

`bash
curl -s -X POST http://localhost:8000/api/analyze \
  -H "Authorization: Bearer " \
  -H "Content-Type: application/json" \
  -d ""
`

Ответ вернёт report_id.
Поллинг статуса:

`bash
curl -s -H "Authorization: Bearer " http://localhost:8000/api/reports/<report_id>
`
4) Для CI есть готовый скрипт scripts/ci/secrets_scan.sh — он ждёт readiness orchestrator, запускает gitleaks/semgrep, отправляет отчёт и выводит сводку.

### Мониторинг и логи
- Health endpoints: http://localhost:8000/health, 8001/health, 8002/health, 8003/health.
- Логи контейнеров: docker logs -f mws-orchestrator (и аналогично для остальных).
- Аудит: 	ail -f logs/audit.jsonl (файл монтируется volume в audit сервисе).
- Для трейсинга можно передавать/читать X-Trace-Id в запросах.

### Остановка и очистка
`bash
docker compose down
`
Добавьте -v, если нужно убрать примонтированные тома/логи.

### Если ничего не работает
`
have fun
`
