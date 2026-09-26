#!/usr/bin/env bash
# 后端单服务启动：装依赖（失败给出可读说明）、端口被占用时顺延并打印实际端口。
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/pip ]; then
  # 目录存在但 pip 缺失说明上次创建失败（常见于缺 python3-venv），清掉重建
  [ -d .venv ] && rm -rf .venv
  echo "[backend] 未发现可用的 .venv，正在创建虚拟环境……"
  if ! python3 -m venv .venv || [ ! -x .venv/bin/pip ]; then
    echo "[backend] 虚拟环境创建失败：通常是缺少 python3-venv 组件，" >&2
    echo "  Debian/Ubuntu 可执行 sudo apt install python3.11-venv 后重试。" >&2
    exit 1
  fi
fi

if ! .venv/bin/pip install -q -r requirements.txt; then
  cat >&2 <<'TIP'
[backend] 依赖安装失败，常见原因与处理：
  1. 网络不通或代理未配置：检查网络，或给 pip 配代理/镜像后再试，例如
     .venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  2. Python 版本过低：需要 3.11 及以上，当前为 $(python3 --version 2>&1)
修好以后重新执行 ./run.sh 即可，安装是幂等的。
TIP
  exit 1
fi

PREFERRED="${APP_PORT:-8000}"
PORT="$(.venv/bin/python -m app.ports "$PREFERRED")"
if [ "$PORT" != "$PREFERRED" ]; then
  echo "[backend] 端口 $PREFERRED 被占用，改用 $PORT"
fi
echo "[backend] 后端地址：http://127.0.0.1:$PORT （健康检查 /api/health）"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
