#!/usr/bin/env bash
set -euo pipefail

SCANNER=${SCANNER:-gitleaks}
ORCH_URL=${ORCH_URL:-http://localhost:8000}

# 1) Запустить сканер → SARIF
if [ "$SCANNER" = "gitleaks" ]; then
  gitleaks detect --report-format sarif --report-path gitleaks.sarif || true
  REPORT_FILE=gitleaks.sarif
elif [ "$SCANNER" = "semgrep" ]; then
  semgrep ci --sarif --output semgrep.sarif || true
  REPORT_FILE=semgrep.sarif
else
  echo "Неизвестный SCANNER=$SCANNER" >&2
  exit 2
fi

# 2) Получить токен
TOKEN=$(curl -s -X POST "$ORCH_URL/api/token" | jq -r .access_token)

# 3) Отправить отчёт
REPORT=$(cat "$REPORT_FILE" | jq -c .)
RESP=$(curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"tool\":\"$SCANNER\",\"report\":$REPORT}" \
  "$ORCH_URL/api/analyze")
echo "$RESP" > analyze.json
REPORT_ID=$(jq -r .report_id analyze.json)

# 4) Поллинг
for i in {1..30}; do
  STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" "$ORCH_URL/api/reports/$REPORT_ID")
  echo "$STATUS" > status.json
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
