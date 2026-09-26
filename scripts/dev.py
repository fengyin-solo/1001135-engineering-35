#!/usr/bin/env python3
"""一条命令拉起本地开发环境：装依赖 → 探端口 → 起前后端 → 自检。

用法：
    python3 scripts/dev.py        # 或 make dev

做的事：
1. 后端：没有 .venv 就建一个，再 pip install -r requirements.txt；
   前端：npm install。装不上时打印可读的原因说明，并允许就地重试。
2. 端口从 8000 / 5173 开始探测，被占用就顺延到下一个可用端口并打印出来。
3. 同时拉起后端 uvicorn 与前端 vite，日志加前缀输出，Ctrl+C 一起停。
4. 后端健康检查通过后打印访问地址与数据概况，确认示例数据已就绪。
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_DIR = BACKEND_DIR / ".venv"

sys.path.insert(0, str(BACKEND_DIR))
from app.ports import find_free_port  # noqa: E402

BACKEND_PORT_PREFERRED = int(os.environ.get("APP_PORT", "8000"))
FRONTEND_PORT_PREFERRED = int(os.environ.get("VITE_PORT", "5173"))

children: list[subprocess.Popen] = []
stopping = False


def info(message: str) -> None:
    print(message, flush=True)


def ask_retry(prompt: str) -> bool:
    """交互终端下询问是否重试；非交互环境（CI 等）直接放弃。"""
    if not sys.stdin.isatty():
        info("[依赖] 当前不是交互终端，无法询问，直接退出。修好上面的问题后重新执行即可。")
        return False
    answer = input(f"{prompt} [输入 r 重试，其他键退出] ").strip().lower()
    return answer == "r"


def run_quiet(cmd: list[str], cwd: Path) -> int:
    """静默执行，只回传退出码；失败细节由调用方提示如何手动复现。"""
    return subprocess.run(
        cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode


def venv_ready() -> bool:
    """venv 目录存在不代表可用（ensurepip 缺失时会留下没有 pip 的残缺目录）。"""
    return (VENV_DIR / "bin" / "pip").is_file()


def ensure_backend_deps() -> None:
    pip = VENV_DIR / "bin" / "pip"
    tips = (
        "[依赖] 后端依赖安装失败，常见原因与处理：\n"
        "  · 网络不通或代理未生效 —— 可换镜像源手动执行：\n"
        f"    {pip} install -r {BACKEND_DIR / 'requirements.txt'}"
        " -i https://pypi.tuna.tsinghua.edu.cn/simple\n"
        f"  · Python 版本过低 —— 需要 3.11+，当前为 {sys.version.split()[0]}\n"
        "  安装是幂等的，修好后重试或重新执行 make dev 即可。"
    )
    while True:
        if not venv_ready():
            if VENV_DIR.is_dir():
                info("[依赖] 检测到残缺的 backend/.venv（缺少 pip），清理后重建……")
                shutil.rmtree(VENV_DIR, ignore_errors=True)
            info("[依赖] 未发现可用的 backend/.venv，正在创建虚拟环境……")
            created = run_quiet([sys.executable, "-m", "venv", str(VENV_DIR)], BACKEND_DIR)
            if created != 0 or not venv_ready():
                info(
                    "[依赖] 虚拟环境创建失败：通常是缺少 python3-venv 组件，\n"
                    "  Debian/Ubuntu 可执行 sudo apt install python3.11-venv 后重试。"
                )
                if not ask_retry("[依赖] 虚拟环境创建失败。"):
                    raise SystemExit(1)
                continue
        info("[依赖] 安装后端依赖（pip install -r backend/requirements.txt）……")
        if run_quiet([str(pip), "install", "-r", "requirements.txt"], BACKEND_DIR) == 0:
            return
        info(tips)
        if not ask_retry("[依赖] 后端依赖安装失败。"):
            raise SystemExit(1)


def ensure_frontend_deps() -> None:
    npm = shutil.which("npm")
    if npm is None:
        info(
            "[依赖] 找不到 npm，请先安装 Node.js 20（https://nodejs.org/），"
            "装好后重新执行 make dev。"
        )
        raise SystemExit(1)
    tips = (
        "[依赖] 前端依赖安装失败，常见原因与处理：\n"
        "  · 网络不通或代理未生效 —— 可换镜像源手动执行：\n"
        "    cd frontend && npm install --registry=https://registry.npmmirror.com\n"
        "  · Node 版本过低 —— 需要 20+，可用 node --version 查看\n"
        "  安装是幂等的，修好后重试或重新执行 make dev 即可。"
    )
    while True:
        info("[依赖] 安装前端依赖（npm install）……")
        if run_quiet([npm, "install", "--no-audit", "--no-fund"], FRONTEND_DIR) == 0:
            return
        info(tips)
        if not ask_retry("[依赖] 前端依赖安装失败。"):
            raise SystemExit(1)


def start_process(label: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,  # 独立进程组，停止时整组一起收
    )
    children.append(proc)

    def pump() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(f"[{label}] {line}", end="", flush=True)

    threading.Thread(target=pump, daemon=True).start()


def stop_children() -> None:
    global stopping
    if stopping:
        return
    stopping = True
    for proc in children:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
    deadline = time.monotonic() + 5
    for proc in children:
        remaining = deadline - time.monotonic()
        try:
            proc.wait(timeout=max(remaining, 0.1))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


def wait_for_health(port: int, timeout: float = 30.0) -> dict:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout
    last_error = "无响应"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - 自检阶段任何异常都汇总成一句话
            last_error = str(exc)
            time.sleep(0.5)
    info(f"[自检] 后端健康检查未通过（{url}）：{last_error}")
    stop_children()
    raise SystemExit(1)


def fetch_overview(port: int) -> dict:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/api/overview", timeout=5
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    info("==> 1/3 检查并安装依赖")
    ensure_backend_deps()
    ensure_frontend_deps()

    info("==> 2/3 探测可用端口")
    backend_port = find_free_port("127.0.0.1", BACKEND_PORT_PREFERRED)
    frontend_port = find_free_port("127.0.0.1", FRONTEND_PORT_PREFERRED)
    if backend_port != BACKEND_PORT_PREFERRED:
        info(f"[端口] {BACKEND_PORT_PREFERRED} 被占用，后端改用 {backend_port}")
    if frontend_port != FRONTEND_PORT_PREFERRED:
        info(f"[端口] {FRONTEND_PORT_PREFERRED} 被占用，前端改用 {frontend_port}")

    info("==> 3/3 启动前后端服务")
    backend_env = dict(os.environ, APP_PORT=str(backend_port))
    start_process(
        "backend",
        [
            str(VENV_DIR / "bin" / "uvicorn"),
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
        ],
        BACKEND_DIR,
        backend_env,
    )
    frontend_env = dict(
        os.environ,
        VITE_PROXY_TARGET=f"http://127.0.0.1:{backend_port}",
    )
    start_process(
        "frontend",
        [
            "npm",
            "run",
            "dev",
            "--",
            "--port",
            str(frontend_port),
            "--strictPort",
            "--host",
            "127.0.0.1",
        ],
        FRONTEND_DIR,
        frontend_env,
    )

    info("[自检] 等待后端健康检查……")
    health = wait_for_health(backend_port)
    overview = fetch_overview(backend_port)
    cards = {card["label"]: card["value"] for card in overview.get("cards", [])}
    db_path = health.get("database", "未知")
    info("")
    info("=" * 60)
    info("本地环境已就绪：")
    info(f"  前端页面  http://127.0.0.1:{frontend_port}/  （浏览器打开这个）")
    info(f"  后端接口  http://127.0.0.1:{backend_port}/api/health")
    info(f"  数据文件  {db_path}")
    info(
        "  数据概况  "
        f"模块 {cards.get('业务模块', '?')} 个 / "
        f"记录 {cards.get('今日新增', '?')} 条 / "
        f"待处理 {cards.get('待处理', '?')} / "
        f"异常 {cards.get('异常量', '?')}"
    )
    info("  停止服务  Ctrl+C（前后端一起停）")
    info("=" * 60)

    def handle_signal(signum: int, _frame: object) -> None:
        info(f"\n[退出] 收到信号 {signum}，正在停止前后端……")
        stop_children()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while True:
        for proc, label in zip(children, ("backend", "frontend")):
            code = proc.poll()
            if code is not None and not stopping:
                info(f"[退出] {label} 进程意外退出（退出码 {code}），一并停止其余服务。")
                stop_children()
                raise SystemExit(1)
        if stopping:
            return
        time.sleep(0.3)


if __name__ == "__main__":
    main()
