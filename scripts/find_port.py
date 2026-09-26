"""从指定端口起找到第一个空闲端口并打印。

供启动脚本调用：python3 scripts/find_port.py 8000
"""
from __future__ import annotations

import socket
import sys


def find_free_port(start: int, host: str = "127.0.0.1", limit: int = 100) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # 与服务器的监听行为保持一致：TIME_WAIT 的残留连接不算占用，
            # 只有真正在监听的进程才会让 bind 失败
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise SystemExit(f"从 {start} 起连续 {limit} 个端口都被占用，请手动指定其他端口")


if __name__ == "__main__":
    base = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(find_free_port(base))
