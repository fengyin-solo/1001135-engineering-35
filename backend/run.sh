#!/usr/bin/env bash
# 后端启动：确保依赖可用 → 端口被占用时自动顺延并打印 → 起 uvicorn。
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python

if [ ! -d .venv ]; then
  echo "[backend] 未发现 .venv，先创建虚拟环境"
  python3 -m venv .venv
fi

if ! "$PY" -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "[backend] 安装后端依赖..."
  if ! .venv/bin/pip install -r requirements.txt; then
    echo "[backend] 依赖安装失败：请检查网络/代理后重试，或在仓库根目录运行 make install（支持交互重试）" >&2
    exit 1
  fi
fi

BASE_PORT=${APP_PORT:-8000}
PORT=$("$PY" ../scripts/find_port.py "$BASE_PORT")
if [ "$PORT" != "$BASE_PORT" ]; then
  echo "[backend] 端口 $BASE_PORT 被占用，自动改用 $PORT"
fi

mkdir -p .runtime
echo "$PORT" > .runtime/backend.port

echo "[backend] 接口地址: http://127.0.0.1:$PORT （健康检查: http://127.0.0.1:$PORT/api/health）"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
