#!/usr/bin/env bash
# 本地一条链：装依赖 → 起后端（端口自检/顺延）→ 数据自检 → 起前端。
# 用法：make dev   （跳过依赖安装：SKIP_INSTALL=1 make dev）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -x backend/.venv/bin/python ]; then
  PY=backend/.venv/bin/python
else
  PY=python3
fi

if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  bash scripts/install.sh
fi

BACKEND_BASE=${APP_PORT:-8000}
FRONTEND_BASE=${FRONTEND_PORT:-5173}
BACKEND_PORT=$("$PY" scripts/find_port.py "$BACKEND_BASE")
FRONTEND_PORT=$("$PY" scripts/find_port.py "$FRONTEND_BASE")

mkdir -p backend/.runtime
rm -f backend/.runtime/backend.port  # 清掉上一次的端口记录，避免读到过期值
BACKEND_LOG=backend/.runtime/backend.log

echo "[dev] 启动后端（日志：$BACKEND_LOG）..."
APP_PORT=$BACKEND_PORT bash backend/run.sh > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 等后端健康检查通过；run.sh 可能把端口顺延，以它写出的实际端口为准
ACTUAL_PORT=""
for _ in $(seq 1 60); do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[dev] 后端进程退出，日志如下：" >&2
    tail -n 20 "$BACKEND_LOG" >&2
    exit 1
  fi
  if [ -s backend/.runtime/backend.port ]; then
    ACTUAL_PORT=$(cat backend/.runtime/backend.port)
    if curl -sf "http://127.0.0.1:$ACTUAL_PORT/api/health" >/dev/null 2>&1; then
      break
    fi
  fi
  sleep 0.5
done

if [ -z "$ACTUAL_PORT" ] || ! curl -sf "http://127.0.0.1:$ACTUAL_PORT/api/health" >/dev/null 2>&1; then
  echo "[dev] 后端 30 秒内未就绪，日志如下：" >&2
  tail -n 20 "$BACKEND_LOG" >&2
  exit 1
fi

echo "[dev] 后端已就绪：http://127.0.0.1:$ACTUAL_PORT"
echo "[dev] 数据自检：核对各模块列表与运营概览..."
"$PY" scripts/smoke.py "http://127.0.0.1:$ACTUAL_PORT"

echo "=========================================================="
echo " 后端接口:  http://127.0.0.1:$ACTUAL_PORT"
echo " 前端页面:  http://127.0.0.1:$FRONTEND_PORT"
echo " 数据文件:  backend/data/app.sqlite3（删掉后重启可重新生成示例数据）"
echo " 停止:      Ctrl+C（前后端一起退出）"
echo "=========================================================="

cd frontend
VITE_PROXY_TARGET="http://127.0.0.1:$ACTUAL_PORT" npm run dev -- --port "$FRONTEND_PORT"
