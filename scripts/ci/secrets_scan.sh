#!/usr/bin/env bash
set -euo pipefail

SCANNER=${SCANNER:-gitleaks}
ORCH_URL=${ORCH_URL:-http://localhost:8000}
RETRY_MAX=60
RETRY_SLEEP=2

echo "[wait] checking orchestrator health at $ORCH_URL/health"
for i in $(seq 1 "$RETRY_MAX"); do
  if curl -fsS "$ORCH_URL/health" >/dev/null; then
    echo "[wait] orchestrator is up"
    break
  fi
  echo "Retry $i/$RETRY_MAX..."
  sleep "$RETRY_SLEEP"
  if [ "$i" -eq "$RETRY_MAX" ]; then
    echo "Orchestrator not reachable at $ORCH_URL/health"
    exit 1
  fi
done

# 1) Сканер -> SARIF
if [ "$SCANNER" = "gitleaks" ]; then
  gitleaks detect --report-format sarif --report-path gitleaks.sarif || true
  REPORT_FILE=gitleaks.sarif
elif [ "$SCANNER" = "semgrep" ]; then
  semgrep ci --sarif --output semgrep.sarif || true
  REPORT_FILE=semgrep.sarif
else
  echo "Unknown SCANNER=$SCANNER" >&2
  exit 2
fi

# Проверить, что файл валидный JSON
jq -e . "$REPORT_FILE" >/dev/null

# 2) Токен (с выводом ошибки при фейле)
HTTP_CODE=$(curl -s -o token.json -w "%{http_code}" -X POST "$ORCH_URL/api/token")
if [ "$HTTP_CODE" != "200" ]; then
  echo "Token request failed HTTP $HTTP_CODE"
  cat token.json
  exit 1
fi
TOKEN=$(jq -r .access_token token.json)

# 3) Собрать payload и отправить (показываем тело ошибки при 4xx/5xx)
PAYLOAD=$(mktemp)
jq -c --arg tool "$SCANNER" '{tool:$tool, report:.}' "$REPORT_FILE" > "$PAYLOAD"

HTTP_CODE=$(curl -s -o analyze.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$PAYLOAD" \
  "$ORCH_URL/api/analyze")
rm -f "$PAYLOAD"

if [ "$HTTP_CODE" != "200" ]; then
  echo "Analyze failed HTTP $HTTP_CODE"
  cat analyze.json
  exit 1
fi
REPORT_ID=$(jq -r .report_id analyze.json)

# 4) Поллинг
for i in {1..30}; do
  curl -fsS -H "Authorization: Bearer $TOKEN" "$ORCH_URL/api/reports/$REPORT_ID" -o status.json
  state=$(jq -r .status status.json)
  if [ "$state" = "completed" ] || [ "$state" = "failed" ]; then break; fi
  sleep 2
done

# 5) Аннотации и summary
findings=$(jq '.findings // []' status.json)
echo "$findings" | jq -c '.[]' | while read -r f; do
  path=$(echo "$f" | jq -r '.original_location.path')
  line=$(echo "$f" | jq -r '.original_location.line // 1')
  msg=$(echo "$f" | jq -r '.secret_snippet')
  fp=$(echo "$f" | jq -r '.is_false_positive')
  echo "::warning file=$path,line=$line::[$fp] $msg"
done

tp=$(echo "$findings" | jq '[.[] | select(.is_false_positive==false)] | length')
echo "## Итоги секрет-скана" >> "$GITHUB_STEP_SUMMARY"
echo "- Найдено: $(echo "$findings" | jq 'length')" >> "$GITHUB_STEP_SUMMARY"
echo "- True positives: $tp" >> "$GITHUB_STEP_SUMMARY"

if [ "$tp" -gt 0 ]; then
  exit 1
fi
