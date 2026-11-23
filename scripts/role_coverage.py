#!/usr/bin/env python3
"""手持ちの汎用型番が hw/slots.json のどの役割に割り当てられるかを集計する（ローカル専用）。

    python scripts/role_coverage.py [--history <入手履歴 JSON>] [--unassigned]

入手履歴は非公開情報なので、このリポジトリにもサブモジュールにも含まれない。
パスは --history か、Git 管理外の .private/config.json の "acquisition_history" で与える。
結果は標準出力にだけ出す（ファイルへ保存しない・コミットしない）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history", type=Path)
    ap.add_argument("--unassigned", action="store_true", help="役割の無い手持ち型番を列挙する")
    args = ap.parse_args()

    history = args.history
    cfg = ROOT / ".private" / "config.json"
    if history is None and cfg.is_file():
        history = ROOT / json.loads(cfg.read_text(encoding="utf-8"))["acquisition_history"]   # 相対パスはリポジトリ基準
    if history is None or not history.is_file():
        print("入手履歴 JSON が見つからない（--history か .private/config.json で指定する）", file=sys.stderr)
        return 2

    owned = {e["PartNumber"] for e in json.loads(history.read_text(encoding="utf-8"))
             if any(e.get(k) for k in ("GottenItemsMN_CMOS", "GottenItemsMN_TTL", "GottenItemsMN_Other"))}
    slots = json.loads((ROOT / "hw" / "slots.json").read_text(encoding="utf-8"))["slots"]
    build = json.loads((ROOT / "hw" / "builds" / "default.json").read_text(encoding="utf-8"))
    adopted = {p for a in build["assignments"] for p in a["parts"]}

    assigned: set[str] = set()
    print(f"{'slot':<10}{'layer':<12}{'候補':>4}{'手持ち':>5}  手持ちの候補")
    for s in slots:
        have = sorted(set(s["candidates"]) & owned, key=lambda p: int(p[3:]))
        assigned |= set(have)
        print(f"{s['id']:<10}{s['layer']:<12}{len(s['candidates']):>4}{len(have):>6}  {' '.join(p[3:] for p in have)}")
    rest = sorted(owned - assigned, key=lambda p: (not p.startswith("74x"), len(p), p))   # 74x 以外（SRAM など）も落とさない
    print(f"\n手持ち {len(owned)} 種 / 役割候補あり {len(assigned)} 種 / 役割なし {len(rest)} 種 / "
          f"既定構成で採用済み {len(adopted & owned)} 種")
    empty = [s["id"] for s in slots if not set(s["candidates"]) & owned]
    if empty:
        print("手持ちで埋められない役割:", " ".join(empty))
    if args.unassigned:
        print("役割なし:", " ".join(rest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
