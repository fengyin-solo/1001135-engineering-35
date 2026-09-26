"""端口探测：从期望端口开始找下一个可用端口，被占用时顺延而不是直接起不来。

命令行用法：``python -m app.ports 8000``，打印一个可用端口，供启动脚本拼接。
"""
from __future__ import annotations

import socket
import sys


def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_free_port(host: str, preferred: int, attempts: int = 50) -> int:
    """从 preferred 起最多向后探 attempts 个端口，返回第一个可用的。"""
    for offset in range(attempts):
        candidate = preferred + offset
        if is_port_free(host, candidate):
            return candidate
    raise RuntimeError(
        f"端口 {preferred} 起连续 {attempts} 个端口都被占用，请手动指定其他端口"
    )


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(find_free_port("127.0.0.1", start))
