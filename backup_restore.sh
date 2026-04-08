#!/bin/bash
# 备份恢复脚本：调用 API 创建备份或恢复指定备份

set -euo pipefail

BASE_URL=${BASE_URL:-"http://127.0.0.1"}
ACTION=${1:-""}

usage() {
  echo "Usage: $0 create [note] | restore <backup_id>"
}

if ! command -v curl >/dev/null 2>&1; then
  echo "curl 未安装，无法调用备份接口"
  exit 1
fi

case "$ACTION" in
  create)
    NOTE=${2:-"manual backup"}
    curl -s -X POST "$BASE_URL/api/backups" -H "Content-Type: application/x-www-form-urlencoded" -d "note=$NOTE"
    echo
    ;;
  restore)
    BACKUP_ID=${2:-""}
    if [ -z "$BACKUP_ID" ]; then
      usage
      exit 1
    fi
    curl -s -X POST "$BASE_URL/api/backups/$BACKUP_ID/restore"
    echo
    ;;
  *)
    usage
    exit 1
    ;;
esac
