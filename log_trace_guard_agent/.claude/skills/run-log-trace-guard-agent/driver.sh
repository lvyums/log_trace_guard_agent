#!/bin/bash
# 日志溯源卫士智能体 — 冒烟测试驱动
# 启动服务 → 等待就绪 → 测试所有 API 端点 → 清理
# 用法: bash driver.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
LOG_FILE="/tmp/log-trace-guard-server.log"
PID_FILE="/tmp/log-trace-guard-server.pid"
PASS=0
FAIL=0

# 颜色
GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

pass() { PASS=$((PASS+1)); echo -e "  ${GREEN}OK${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}FAIL${NC} $1"; }

# 等待就绪函数
wait_for_ready() {
  local timeout=30
  local url="http://127.0.0.1:$PORT/health"
  for i in $(seq 1 $timeout); do
    if curl -s "$url" > /dev/null 2>&1; then
      pass "服务就绪 (${i}s)"
      return 0
    fi
    sleep 1
  done
  return 1
}

# ── 清理 ──
cleanup() {
  if [ -f "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
}
trap cleanup EXIT

# ── 1. 启动服务 ──
echo "=== 启动服务 ==="
cd "$APP_DIR"
python -m uvicorn app.main:app --host "$HOST" --port "$PORT" &> "$LOG_FILE" &
echo $! > "$PID_FILE"

# ── 2. 等待就绪 ──
echo "=== 等待服务就绪 (端口 $PORT) ==="
if ! wait_for_ready; then
  fail "服务启动超时"
  tail -5 "$LOG_FILE"
  exit 1
fi

# ── 3. 健康检查 ──
echo "=== 健康检查 ==="
RESP=$(curl -s "http://${HOST}:${PORT}/")
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('status')=='running'" 2>/dev/null; then
  pass "GET / → status=running"
else
  fail "GET / → $RESP"
fi

RESP=$(curl -s "http://${HOST}:${PORT}/health")
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('status')=='healthy'" 2>/dev/null; then
  pass "GET /health → status=healthy"
else
  fail "GET /health → $RESP"
fi

# ── 4. 日志识别 ──
echo "=== 日志识别 ==="
RESP=$(curl -s -X POST "http://${HOST}:${PORT}/api/v1/log-parse/identify" \
  -H "Content-Type: application/json" \
  -d '{"log_line":"Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"}')
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('data',{}).get('device_type')=='ssh'" 2>/dev/null; then
  pass "识别 SSH 日志 → device_type=ssh"
else
  fail "识别 SSH 日志 → $RESP"
fi

RESP=$(curl -s -X POST "http://${HOST}:${PORT}/api/v1/log-parse/identify" \
  -H "Content-Type: application/json" \
  -d '{"log_line":"192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] \"GET /index.html HTTP/1.1\" 200 2326"}')
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('data',{}).get('device_type')=='web'" 2>/dev/null; then
  pass "识别 Web 日志 → device_type=web"
else
  fail "识别 Web 日志 → $RESP"
fi

# ── 5. 日志解析 ──
echo "=== 日志解析 ==="
RESP=$(curl -s -X POST "http://${HOST}:${PORT}/api/v1/log-parse/parse" \
  -H "Content-Type: application/json" \
  -d '{"log_line":"Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"}')
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('data',{}).get('src_ip')=='192.168.1.1'" 2>/dev/null; then
  pass "解析 SSH 日志 → src_ip=192.168.1.1"
else
  fail "解析 SSH 日志 → $RESP"
fi

RESP=$(curl -s -X POST "http://${HOST}:${PORT}/api/v1/log-parse/parse" \
  -H "Content-Type: application/json" \
  -d '{"log_line":"192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] \"GET /index.html HTTP/1.1\" 200 2326 \"-\" \"Mozilla/5.0\""}')
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('data',{}).get('method')=='GET'" 2>/dev/null; then
  pass "解析 Web 日志 → method=GET"
else
  fail "解析 Web 日志 → $RESP"
fi

# ── 6. 风险研判 ──
echo "=== 风险研判 ==="
RESP=$(curl -s -X POST "http://${HOST}:${PORT}/api/v1/log-parse/assess" \
  -H "Content-Type: application/json" \
  -d '{"log_line":"Mar 15 10:31:00 server sshd[1235]: Failed password for admin from 10.0.0.5 port 22"}')
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert 'attack_type' in d.get('data',{})" 2>/dev/null; then
  pass "风险研判 SSH 失败登录 → 有攻击类型"
else
  fail "风险研判 SSH 失败登录 → $RESP"
fi

# ── 7. 字段释义 ──
echo "=== 字段释义 ==="
RESP=$(curl -s -X POST "http://${HOST}:${PORT}/api/v1/log-parse/explain" \
  -H "Content-Type: application/json" \
  -d '{"field_name":"src_ip"}')
if echo "$RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert 'field' in d.get('data',{})" 2>/dev/null; then
  pass "字段释义 src_ip → 有 field 字段"
else
  fail "字段释义 src_ip → $RESP"
fi

# ── 8. 汇总 ──
echo ""
echo "=== 结果汇总 ==="
echo -e "  通过: ${GREEN}${PASS}${NC}  失败: ${RED}${FAIL}${NC}"
if [ "$FAIL" -gt 0 ]; then
  echo -e "  ${RED}部分测试失败${NC}"
  exit 1
else
  echo -e "  ${GREEN}全部通过${NC}"
fi