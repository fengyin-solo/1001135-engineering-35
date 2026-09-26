"""数据自检：运营概览的数字必须和各模块列表接口对得上。

用法：python3 scripts/smoke.py http://127.0.0.1:8000
任何一项对不上都会打印明细并以非零码退出。
"""
from __future__ import annotations

import json
import sys
import urllib.request

PAGE_SIZE = 200  # 后端单页上限


def get_json(base: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=10) as resp:
        return json.load(resp)


def fetch_all(base: str, module: str) -> tuple[list[dict], int]:
    """翻页拿全量，避免行数超过单页上限时统计口径不一致。"""
    items: list[dict] = []
    page = 1
    while True:
        payload = get_json(base, f"/api/{module}?page={page}&size={PAGE_SIZE}")
        items.extend(payload["items"])
        total = int(payload["total"])
        if len(items) >= total or not payload["items"]:
            return items, total
        page += 1


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    failures: list[str] = []

    health = get_json(base, "/api/health")
    if not health.get("ok"):
        failures.append(f"健康检查未通过：{health}")

    overview = get_json(base, "/api/overview")
    modules = overview["modules"]
    cards = {card["label"]: int(card["value"]) for card in overview["cards"]}

    print(f"[smoke] 共 {len(modules)} 个业务模块，逐模块核对列表与概览数字：")
    for module in modules:
        name = module["name"]
        items, total = fetch_all(base, name)
        pending = sum(1 for item in items if item.get("pending"))
        abnormal = sum(1 for item in items if item.get("abnormal"))
        expected = (int(module["created"]), int(module["pending"]), int(module["abnormal"]))
        actual = (total, pending, abnormal)
        if actual != expected:
            failures.append(
                f"模块 {name} 对不上：列表统计 新增/待处理/异常={actual}，概览={expected}"
            )
            print(f"  ✗ {name}: 列表={actual} 概览={expected}")
        else:
            print(f"  ✓ {name}: 新增 {total} / 待处理 {pending} / 异常 {abnormal}")

    card_checks = {
        "业务模块": len(modules),
        "今日新增": sum(int(m["created"]) for m in modules),
        "待处理": sum(int(m["pending"]) for m in modules),
        "异常量": sum(int(m["abnormal"]) for m in modules),
    }
    for label, expected in card_checks.items():
        if cards.get(label) != expected:
            failures.append(f"概览卡片「{label}」应为 {expected}，实际 {cards.get(label)}")

    if failures:
        print("[smoke] 自检未通过：")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("[smoke] 自检通过：运营概览与各模块列表数字一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
