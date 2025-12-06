Опишу как живой сценарий “DevSecOps кидает JSON → мы всё прогоняем → он забирает результат”.

---

## 0. Общие договорённости

* Везде есть **`report_id` (UUID)** — главный ключ.
* Статусы в таблице `reports`:

  * `created → ingested → processing → done/error`.
* Логи бывают двух типов:

  * **технические** – обычный `logging` в stdout;
  * **audit-события** – пишутся через сервис Audit в таблицу `audit_events` Operational DB.

---

## 1. DevSecOps отправляет отчёт

### 1.1. Запрос

DevSecOps делает:

```http
POST /reports
Content-Type: application/json
```

Тело:

```json
{
  "scanner_type": "trufflehog",
  "report_format": "json",
  "report": { ... сырой JSON от сканера ... }
}
```

### 1.2. Orchestrator: приём запроса

1. Генерируется:

   * `request_id` (для логов),
   * `report_id` (UUID).

2. **Тех. лог Orchestrator (stdout)**:

```text
[INFO] request_id=..., report_id=... 
POST /reports received, scanner_type=trufflehog, size=123KB
```

3. **Запись в Operational DB (таблица `reports`)**:

* `id = report_id`
* `scanner_type = 'trufflehog'`
* `status = 'created'`
* `created_at / updated_at`
* `raw_report = JSONB(report)`  *(в MVP храним прямо в БД)*

4. **Audit-событие** (через сервис Audit → `audit_events`):

```json
{
  "event_type": "REPORT_CREATED",
  "report_id": "report_id",
  "service": "orchestrator",
  "payload": {
    "scanner_type": "trufflehog"
  }
}
```

---

## 2. Orchestrator → Report Ingestor

### 2.1. Вызов Ingestor’а

Orchestrator делает внутренний запрос:

```http
POST http://report-ingestor/ingest
```

```json
{
  "report_id": "report_id",
  "scanner_type": "trufflehog",
  "report_format": "json",
  "report": { ... тот же сырой JSON ... }
}
```

### 2.2. Report Ingestor: парсинг

1. **Тех. лог Ingestor’а**:

```text
[INFO] report_id=... POST /ingest, scanner_type=trufflehog
```

2. Выбор парсера: `parse_trufflehog(report)`.

3. Парсер превращает сырой JSON в список нормализованных `findings`:

```json
[
  {
    "id": "finding-1",
    "scanner_type": "trufflehog",
    "path": "src/config/prod.yml",
    "line": 42,
    "kind": "possible_secret",
    "value_preview": "AKIA....",
    "raw_metadata": { "rule": "AWS Access Key", "severity": "HIGH" }
  },
  ...
]
```

4. В случае ошибки:

   * лог `ERROR` в stdout,
   * ответ с ошибкой назад Orchestrator’у.

5. В случае успеха:

**Тех. лог:**

```text
[INFO] report_id=... ingest_ok, findings_count=17
```

**Ответ Orchestrator’у:**

```json
{
  "report_id": "report_id",
  "findings": [ ... ]
}
```

### 2.3. Orchestrator: сохранение результатов ingestion

1. **Тех. лог:**

```text
[INFO] report_id=... ingestion_success, findings_count=17
```

2. **DB: вставка в таблицу `findings`** (bulk insert):

Для каждого finding:

* `id`
* `report_id`
* `path`, `line`, `kind`, `value_preview`, `scanner_type`, `raw_metadata`
* колонки модерации (`risk`, `reason`, `source`) пока `NULL`.

3. **Обновление статуса отчёта** в `reports`:

* `status: 'created' → 'ingested'`,
* `updated_at = now()`.

4. **Audit-событие**:

```json
{
  "event_type": "REPORT_INGESTED",
  "report_id": "report_id",
  "service": "orchestrator",
  "payload": {
    "findings_count": 17
  }
}
```

---

## 3. Orchestrator → Moderator

### 3.1. Статус “processing”

Перед вызовом Moderator’а Orchestrator:

* обновляет `reports.status: 'ingested' → 'processing'`,
* пишет Audit:

```json
{
  "event_type": "REPORT_PROCESSING_STARTED",
  "report_id": "report_id",
  "service": "orchestrator"
}
```

### 3.2. Вызов Moderator’а

В MVP проще всего передать findings прямо в теле:

```http
POST http://moderator/moderate
```

```json
{
  "report_id": "report_id",
  "findings": [ ... те же 17 штук ... ]
}
```

*(более продвинутый вариант — Moderator сам читает findings из БД по `report_id`, но для MVP можно не усложнять)*

### 3.3. Moderator: модерация

1. **Тех. лог Moderator’а:**

```text
[INFO] report_id=... POST /moderate, findings_count=17
```

2. Для каждого finding:

* `heuristics_engine`:

  * regex по типу AWS keys, private keys и т.п.
* `ml_classifier`:

  * если есть, отдаёт вероятность, что это реальный секрет.
* `llm_client`:

  * для спорных кейсов отправляет краткий контекст в LLM API
    (LLM-токены берутся из Secret Manager при старте сервиса).

3. Формируется финальный вывод по каждому finding:

```json
{
  "id": "finding-1",
  "risk": "high",
  "reason": "Matches AWS key pattern and located in prod config",
  "source": "heuristic"   // или ml / llm
}
```

4. **Тех. логи**:

   * старт/окончание LLM-вызова (без “слива” секретов),
   * суммарная статистика: сколько high/medium/low.

```text
[INFO] report_id=... moderation_done, high=3, medium=5, low=9
```

5. **Ответ Orchestrator’у:**

```json
{
  "report_id": "report_id",
  "findings": [
    { "id": "finding-1", "risk": "high", "reason": "...", "source": "heuristic" },
    ...
  ]
}
```

6. **Audit-событие** (через Audit-сервис):

```json
{
  "event_type": "REPORT_MODERATED",
  "report_id": "report_id",
  "service": "moderator",
  "payload": {
    "high": 3,
    "medium": 5,
    "low": 9
  }
}
```

---

## 4. Orchestrator: запись результата модерации и ответ

### 4.1. Обновление БД

В Orchestrator:

1. **Тех. лог:**

```text
[INFO] report_id=... moderation_result_received, high=3, medium=5, low=9
```

2. **Обновление `findings`**:

Для каждого id в ответе Moderator’а:

* проставляем `risk`, `reason`, `source`.

3. **Обновление отчёта** в `reports`:

* `status: 'processing' → 'done'`,
* поле `summary` (JSON) — например:

```json
{
  "high": 3,
  "medium": 5,
  "low": 9
}
```

4. **Audit-событие**:

```json
{
  "event_type": "REPORT_DONE",
  "report_id": "report_id",
  "service": "orchestrator",
  "payload": {
    "summary": { "high": 3, "medium": 5, "low": 9 }
  }
}
```

### 4.2. Ответ на `POST /reports`

В MVP мы делаем синхронный пайплайн (всё прошло до конца), поэтому Orchestrator возвращает:

```json
{
  "report_id": "report_id",
  "status": "done",
  "summary": {
    "high": 3,
    "medium": 5,
    "low": 9
  }
}
```

DevSecOps сразу видит, что всё отработало и сколько критичных находок.

---

## 5. DevSecOps позже делает `GET /reports/{id}`

### 5.1. Запрос

```http
GET /reports/{report_id}
```

### 5.2. Orchestrator: чтение из БД

1. **Тех. лог:**

```text
[INFO] report_id=... GET /reports/{id}
```

2. Чтение из Operational DB:

* таблица `reports`:

  * статус, summary, scanner_type, timestamps.
* join с `findings`:

  * полный список findings, уже с полями `risk`, `reason`, `source`.

3. Формирование ответа:

```json
{
  "report_id": "report_id",
  "status": "done",
  "scanner_type": "trufflehog",
  "summary": {
    "high": 3,
    "medium": 5,
    "low": 9
  },
  "findings": [
    {
      "id": "finding-1",
      "path": "src/config/prod.yml",
      "line": 42,
      "kind": "possible_secret",
      "value_preview": "AKIA...",
      "risk": "high",
      "reason": "...",
      "source": "heuristic"
    },
    ...
  ]
}
```

4. (Опционально) **Audit-событие**:

```json
{
  "event_type": "REPORT_VIEWED",
  "report_id": "report_id",
  "service": "orchestrator"
}
```

---

## 6. Где какие логи и данные

**Тех. логи (stdout):**

* Orchestrator:

  * приём POST/GET,
  * вызов /ingest, /moderate,
  * статусы: ingestion_success, moderation_result_received, ошибки.
* Report Ingestor:

  * ingress запросов, результат парсинга, ошибки.
* Moderator:

  * старт/конец модерации,
  * LLM-запросы по метаданным (без секретов),
  * итоговая статистика.

**Operational DB:**

* `reports`:

  * статусный жизненный цикл + summary + raw_report (в MVP).
* `findings`:

  * нормализованные находки + результат модерации.
* `audit_events`:

  * бизнес-события по ключевым шагам (created, ingested, processing_started, moderated, done, errors, viewed).

---

Это и есть полный путь:
**JSON отчёт → Orchestrator → Ingestor → Moderator → Operational DB → ответ DevSecOps + возможность достать всё позже.**

Если нужно, дальше могу оформить это в виде небольшой диаграммы состояний + таблички “событие → кто логирует → какие таблицы трогаем” для отчёта.
