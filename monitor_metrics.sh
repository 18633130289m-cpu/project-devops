#!/bin/bash
# 监控采集脚本：调用后端监控接口并写入本地记录

set -euo pipefail

API_URL=${API_URL:-"http://127.0.0.1/api/metrics"}
OUT_FILE=${OUT_FILE:-"./logs/monitor_metrics.jsonl"}

mkdir -p "$(dirname "$OUT_FILE")"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl 未安装，无法采集监控数据"
  exit 1
fi

result=$(curl -s "$API_URL")
echo "$result" >> "$OUT_FILE"
echo "[$(date '+%F %T')] monitor snapshot appended to $OUT_FILE"
