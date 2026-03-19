#!/usr/bin/env python3
import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List

import requests

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"
WATCH_FILE = DATA_DIR / "watchlist.json"
STATE_FILE = DATA_DIR / "state.json"

CHEAPSHARK_DEALS = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_GAMES = "https://www.cheapshark.com/api/1.0/games"


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not WATCH_FILE.exists():
        WATCH_FILE.write_text("[]", encoding="utf-8")
    if not STATE_FILE.exists():
        STATE_FILE.write_text("{}", encoding="utf-8")


def _load_watch() -> List[Dict[str, Any]]:
    _ensure()
    return json.loads(WATCH_FILE.read_text(encoding="utf-8"))


def _save_watch(items: List[Dict[str, Any]]):
    WATCH_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_state() -> Dict[str, Any]:
    _ensure()
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _save_state(state: Dict[str, Any]):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_game(query: str) -> Dict[str, Any]:
    r = requests.get(CHEAPSHARK_GAMES, params={"title": query, "limit": 10}, timeout=20)
    r.raise_for_status()
    arr = r.json()
    if not arr:
        raise SystemExit(f"未找到游戏: {query}")
    # choose first with steamAppID if possible
    best = None
    for g in arr:
        if g.get("steamAppID"):
            best = g
            break
    best = best or arr[0]
    return {
        "name": best.get("external"),
        "gameID": best.get("gameID"),
        "steamAppID": str(best.get("steamAppID") or ""),
        "thumb": best.get("thumb"),
    }


def fetch_price(steam_appid: str) -> Dict[str, Any]:
    r = requests.get(
        CHEAPSHARK_DEALS,
        params={"steamAppID": steam_appid, "sortBy": "Price", "pageSize": 1},
        timeout=20,
    )
    r.raise_for_status()
    deals = r.json()
    if not deals:
        return {"current": None, "store": None, "dealID": None}
    d = deals[0]
    return {
        "current": float(d.get("salePrice", 0) or 0),
        "normal": float(d.get("normalPrice", 0) or 0),
        "store": d.get("storeID"),
        "dealID": d.get("dealID"),
    }


def fetch_history_low(game_id: str) -> float:
    r = requests.get(CHEAPSHARK_GAMES, params={"id": game_id}, timeout=20)
    r.raise_for_status()
    obj = r.json()
    low = obj.get("cheapestPriceEver", {}).get("price")
    return float(low or 0)


def steam_link(appid: str) -> str:
    return f"https://store.steampowered.com/app/{appid}/"


def cmd_add(args):
    game = resolve_game(args.query)
    appid = game["steamAppID"]
    if not appid:
        raise SystemExit("该游戏无法解析 Steam AppID")

    watch = _load_watch()
    for w in watch:
        if w.get("steamAppID") == appid:
            print(f"已存在: {w['name']} (appid={appid})")
            return

    item = {
        "name": game["name"],
        "gameID": game["gameID"],
        "steamAppID": appid,
        "target": float(args.target) if args.target is not None else None,
        "addedAt": int(time.time()),
    }
    watch.append(item)
    _save_watch(watch)
    print(f"已添加: {item['name']} | appid={appid} | target={item['target']}")


def cmd_list(_args):
    watch = _load_watch()
    if not watch:
        print("关注列表为空")
        return
    for i, w in enumerate(watch, 1):
        print(f"{i}. {w['name']} | appid={w['steamAppID']} | target={w.get('target')}")


def cmd_remove(args):
    watch = _load_watch()
    n = len(watch)
    watch = [w for w in watch if w.get("steamAppID") != str(args.appid)]
    _save_watch(watch)
    print("已删除" if len(watch) < n else "未找到该 appid")


def format_alert(name: str, appid: str, current: float, low: float) -> str:
    diff = current - low
    sign = "+" if diff > 0 else ""
    return (
        f"🎮 {name}\n"
        f"当前价: {current:.2f}\n"
        f"史低价: {low:.2f}\n"
        f"差价: {sign}{diff:.2f}\n"
        f"链接: {steam_link(appid)}"
    )


def cmd_check(_args):
    watch = _load_watch()
    if not watch:
        print("关注列表为空")
        return

    state = _load_state()
    hits = []

    for w in watch:
        name = w["name"]
        appid = w["steamAppID"]
        game_id = w["gameID"]
        target = w.get("target")

        p = fetch_price(appid)
        if p.get("current") is None:
            continue
        current = float(p["current"])
        low = fetch_history_low(game_id)

        hit_low = low > 0 and current <= low
        hit_target = target is not None and current <= float(target)

        if hit_low or hit_target:
            key = f"{appid}:{current:.2f}:{low:.2f}:{target}"
            if state.get(appid) == key:
                continue
            hits.append(format_alert(name, appid, current, low))
            state[appid] = key

    _save_state(state)

    if not hits:
        print("Steam 史低监控：本轮无触发")
    else:
        print("\n\n".join(hits))


def main():
    parser = argparse.ArgumentParser(description="Steam 史低监控")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="添加关注")
    p_add.add_argument("--query", required=True, help="游戏名")
    p_add.add_argument("--target", type=float, default=None, help="目标价")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="列出关注")
    p_list.set_defaults(func=cmd_list)

    p_rm = sub.add_parser("remove", help="删除关注")
    p_rm.add_argument("--appid", required=True, help="Steam AppID")
    p_rm.set_defaults(func=cmd_remove)

    p_check = sub.add_parser("check", help="检查价格并输出提醒")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
