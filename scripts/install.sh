#!/usr/bin/env bash
# 依赖安装：前后端一起装；装不上时给出可读说明，并允许当场重试。
set -euo pipefail
cd "$(dirname "$0")/.."

# 交互终端里失败后问一句「是否重试」；非交互环境（CI）直接报错退出。
with_retry() {
  local label="$1"; shift
  local attempt=1
  while true; do
    if "$@"; then
      echo "[install] $label：完成"
      return 0
    fi
    echo "----------------------------------------------------------" >&2
    echo "[install] $label 安装失败（第 $attempt 次）。" >&2
    echo "  常见原因：网络不通、代理未配置、镜像源临时不可用。" >&2
    echo "  可以重试；若持续失败，请检查网络后重新运行 make install。" >&2
    if [ -t 0 ]; then
      local answer
      read -r -p "[install] 是否重试 $label 安装？[y/N] " answer
      case "$answer" in
        y|Y|yes|YES) attempt=$((attempt + 1)); continue ;;
        *) return 1 ;;
      esac
    fi
    return 1
  done
}

echo "[install] 检查运行环境..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "[install] 未找到 python3：请先安装 Python 3.10 或更高版本" >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "[install] 未找到 node/npm：请先安装 Node.js 18 或更高版本" >&2
  exit 1
fi
echo "[install] python3: $(python3 --version 2>&1) / node: $(node --version) / npm: $(npm --version)"

echo "[install] 后端依赖（backend/requirements.txt，版本已锁定）..."
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
with_retry "后端依赖" backend/.venv/bin/pip install -r backend/requirements.txt

echo "[install] 前端依赖（frontend/package-lock.json，版本已锁定）..."
with_retry "前端依赖" npm --prefix frontend install

echo "[install] 全部依赖安装完成"
