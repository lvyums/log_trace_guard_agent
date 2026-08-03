#!/usr/bin/env bash
# ============================================================
# 日志溯源卫士智能体 — 数据备份脚本
# 备份内容: 向量库(chroma_db) / 环境配置(.env) / 规则数据(rule_data)
#           / 应用日志(logs)
# 用法:
#   ./backup.sh                 # 备份到 ./backups/ 默认保留 7 份
#   BACKUP_DIR=/data/backup ./backup.sh   # 自定义备份目录
#   KEEP=30 ./backup.sh         # 保留最近 30 份
#
# 定时策略(生产建议, 每天凌晨 2 点执行, 保留 30 天):
#   0 2 * * * /opt/log-trace-guard/backup.sh >> /var/log/log-guard-backup.log 2>&1
# ============================================================

set -euo pipefail

# 项目根目录(脚本所在目录)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
KEEP="${KEEP:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/log-guard-backup-$TIMESTAMP.tar.gz"

# 需要备份的路径(相对于项目根)
BACKUP_PATHS=(
    "data/chroma_db"
    "data/rule_data"
    "data/case_data"
    ".env"
    "logs"
)

mkdir -p "$BACKUP_DIR"

# 过滤掉 ChromaDB 临时文件(每次启动生成的临时目录, 无需备份)
EXCLUDE_ARGS=(
    --exclude="data/chroma_db/*-tmp-*"
    --exclude="__pycache__"
    --exclude="*.pyc"
)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份 → $TARGET"

# 打包
tar czf "$TARGET" "${EXCLUDE_ARGS[@]}" -C "$PROJECT_DIR" "${BACKUP_PATHS[@]}"

SIZE="$(du -h "$TARGET" | cut -f1)"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成: $TARGET ($SIZE)"

# 清理旧备份, 保留最近 KEEP 份
COUNT=$(ls -1 "$BACKUP_DIR"/log-guard-backup-*.tar.gz 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$KEEP" ]; then
    ls -1t "$BACKUP_DIR"/log-guard-backup-*.tar.gz | tail -n $((COUNT - KEEP)) | while read -r old; do
        rm -f "$old"
        echo "  清理旧备份: $old"
    done
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完成, 当前备份数: $(ls -1 "$BACKUP_DIR"/log-guard-backup-*.tar.gz 2>/dev/null | wc -l)/$KEEP"
