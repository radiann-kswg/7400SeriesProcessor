#!/usr/bin/env python3
"""システム階層の正本（hw/system.json）から、全体図と一覧表を生成する。

    python scripts/gen_system.py [--svg]

生成物（手で編集しない）: docs/design/generated/
    README.md         全体図（Mermaid。GitHub 上でそのまま描画される）、IC 一覧、基板とカード、
                      LED 一覧、基板をまたぐ信号（接続口の信号数）、信号辞書、検査結果
    fig_<名前>.mmd    全体図の Mermaid ソース
    fig_<名前>.svg    --svg 指定時（mermaid-cli の mmdc が PATH に必要）。無いときは既存の SVG を残す

pinspec の有無は hw/pinspec/ と collection/pcb-demo/_carrier/pinspec/ を見て判定する。
Python 標準ライブラリのみで動く。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "hw" / "system.json"
BUILD = ROOT / "hw" / "builds" / "default.json"
CARDS = ROOT / "hw" / "cards"
OUT = ROOT / "docs" / "design" / "generated"
PINSPEC_DIRS = [ROOT / "hw" / "pinspec", ROOT / "collection" / "pcb-demo" / "_carrier" / "pinspec"]
HEADER = "> `scripts/gen_system.py` による生成物。手で編集せず `hw/system.json` を直して再生成する。"
HUB = "main"   # ほかの基板は本体と接続口でつながる


class DefError(Exception):
    pass


def has_pinspec(part: str) -> bool:
    return any((d / f"{part}.json").is_file() for d in PINSPEC_DIRS)


def parts_of(b: dict) -> list[str]:
    return b.get("parts") or [b["part"]]


def dest(t) -> tuple[str, str | None]:
    """受け先の書き方（ブロック名だけ、または {block, label}）を (ブロック, ラベル) にそろえる。"""
    return (t["block"], t["label"]) if isinstance(t, dict) else (t, None)


class System:
    def __init__(self, doc: dict, build: dict) -> None:
        self.doc = doc
        self.build = {a["slot"]: a for a in build["assignments"]}
        self.boards = {b["id"]: b for b in doc["boards"]}
        self.cards = {c["id"]: c for c in doc["cards"]}
        self.blocks: dict[str, dict] = {}
        self.signals = {s["name"]: s for s in doc["signals"]}
        self.warnings: list[str] = []
        self._check()

    def board_of(self, bid: str) -> str:
        b = self.blocks[bid]
        return b["board"] if b.get("external") else self.cards[b["card"]]["board"]

    def _check(self) -> None:
        d = self.doc
        for c in d["cards"]:
            if c["board"] not in self.boards:
                raise DefError(f"カード {c['id']}: 基板 {c['board']} が無い")
        for b in d["blocks"]:
            if b["id"] in self.blocks:
                raise DefError(f"ブロック {b['id']} が重複している")
            self.blocks[b["id"]] = b
            if b.get("external"):
                if b["board"] not in self.boards:
                    raise DefError(f"外部 {b['id']}: 基板 {b['board']} が無い")
            elif b["card"] not in self.cards:
                raise DefError(f"ブロック {b['id']}: カード {b['card']} が無い")
        for b in self.blocks.values():
            slot = b.get("slot")
            if slot is None:
                continue
            if "device" in b:
                raise DefError(f"ブロック {b['id']}: slot を持つブロックの実型番は builds に書く（device を消す）")
            if slot not in self.build:
                self.warnings.append(f"ブロック {b['id']}: slot {slot} が構成（builds/default.json）に無い")
        for slot, a in self.build.items():
            if a.get("card"):
                path = CARDS / a["card"] / "card.json"
                if not path.is_file():
                    raise DefError(f"構成の {slot}: カード定義 {a['card']} が無い")
                devices = {c["device"] for c in json.loads(path.read_text(encoding="utf-8"))["components"] if c.get("device")}
                if a.get("device") and a["device"] not in devices:
                    raise DefError(f"構成の {slot}: 実型番 {a['device']} がカード定義 {a['card']} の device {sorted(devices)} と食い違う")
        if len(self.signals) != len(d["signals"]):
            raise DefError("信号名が重複している")
        figs = {f["id"] for f in d["figures"]} | {"none"}
        used: set[str] = set()
        for s in d["signals"]:
            if s["fig"] not in figs:
                raise DefError(f"信号 {s['name']}: 図 {s['fig']} が figures に無い")
            ends = list(s["from"]) + [dest(t)[0] for t in s["to"]]
            for e in ends:
                if e not in self.blocks:
                    raise DefError(f"信号 {s['name']}: ブロック {e} が無い")
            used |= set(ends)
            if len(s["from"]) > 1 and not s.get("shared"):
                raise DefError(f"信号 {s['name']}: 駆動元が複数あるのに shared（3state / split / select）の宣言が無い")
            boards = {self.board_of(e) for e in ends}
            if len(boards) > 1 and s["scope"] == "カード内":
                raise DefError(f"信号 {s['name']}: 基板をまたぐのに scope がカード内")
        drivers: set[str] = set()
        for c in d["cards"]:
            for led in c.get("leds", []):
                for n in led["signals"]:
                    if n not in self.signals:
                        raise DefError(f"カード {c['id']} の LED: 信号 {n} が無い")
                drv = led.get("driver")
                if drv is not None:
                    if drv not in self.blocks:
                        raise DefError(f"カード {c['id']} の LED: 駆動ブロック {drv} が無い")
                    drivers.add(drv)
        for f, extra in d.get("fig_extra", {}).items():
            for n, dests in extra.items():
                if n not in self.signals or any(x not in self.blocks for x in dests):
                    raise DefError(f"fig_extra[{f}]: 信号 {n} か、その受け先が無い")
        for b in self.blocks.values():
            if b.get("kind") == "led_driver":
                if b["id"] not in drivers:
                    self.warnings.append(f"LED 駆動ブロック {b['id']} がどのカードの LED からも参照されていない")
            elif b["id"] not in used:
                self.warnings.append(f"ブロック {b['id']} はどの信号にもつながっていない")

    # --- 図 -----------------------------------------------------------
    def node_of(self, bid: str) -> str:
        return self.blocks[bid].get("node", bid)

    def node_label(self, node: str) -> str:
        members = [b for b in self.blocks.values() if b.get("node", b["id"]) == node]
        m0 = members[0]
        if m0.get("external"):
            return f"{m0['label']}<br/>({self.boards[m0['board']]['title']})"
        refs = " + ".join(m["refs"] for m in members)
        parts = " + ".join("/".join(p.replace("74x", "") if i else p for i, p in enumerate(parts_of(m)))
                           + (f" x{m['count']}" if m["count"] > 1 else "") for m in members)
        return f"{refs}<br/>{parts}<br/>({m0['card']})"

    def figure(self, fig: dict) -> str:
        extra = self.doc.get("fig_extra", {}).get(fig["id"], {})
        edges: dict[tuple[str, str, bool], list[str]] = {}
        for s in self.doc["signals"]:
            if s["fig"] != fig["id"] and s["name"] not in extra:
                continue
            for src in s["from"]:
                for t in s["to"]:
                    dst, label = dest(t)
                    label = label or s["name"]
                    a, b = self.node_of(src), self.node_of(dst)
                    if a == b or (s["fig"] != fig["id"] and dst not in extra[s["name"]]):
                        continue
                    labels = edges.setdefault((a, b, s["width"] > 1), [])
                    if label not in labels:
                        labels.append(label)
        nodes: list[str] = []
        for a, b, _ in edges:
            for n in (a, b):
                if n not in nodes:
                    nodes.append(n)
        q = lambda t: t.replace('"', "#quot;")  # noqa: E731
        out = ["flowchart LR"] + [f'  {n}["{q(self.node_label(n))}"]' for n in nodes] + [""]
        for (a, b, bus), labels in edges.items():
            text = q(" / ".join(labels))
            out.append(f'  {a} == "{text}" ==> {b}' if bus else f'  {a} -- "{text}" --> {b}')
        return "\n".join(out) + "\n"

    def device_of(self, b: dict) -> str:
        if b.get("slot") in self.build:
            return self.build[b["slot"]].get("device") or ""
        return b.get("device", "")

    # --- 表 -----------------------------------------------------------
    def ic_rows(self) -> tuple[list[str], dict]:
        rows = ["| 参照 | 汎用型番 | 個数 | 採用実型番 | 役割 | カード | 基板 | 外すと欠ける機能 | pinspec |",
                "|---|---|---:|---|---|---|---|---|---|"]
        stat = {"total": 0, "kinds": set(), "missing": set(), "by_board": {}}
        for b in self.blocks.values():
            if b.get("external"):
                continue
            parts = parts_of(b)
            board = self.board_of(b["id"])
            if all(p.startswith("74x") for p in parts):
                stat["total"] += b["count"]
                stat["by_board"][board] = stat["by_board"].get(board, 0) + b["count"]
                stat["kinds"] |= set(parts)
                stat["missing"] |= {p for p in parts if not has_pinspec(p)}
                have = [has_pinspec(p) for p in parts]
                state = "有" if all(have) else ("一部有" if any(have) else "無")
            else:
                state = "—"
            count = ("約 " if b.get("count_approx") else "") + str(b["count"])
            role = b["role"] + (f"（{b['note']}）" if b.get("note") else "")
            rows.append(f"| {b['refs']} | {' / '.join(parts)} | {count} | {self.device_of(b)} | {role} | "
                        f"`{b['card']}` | {self.boards[board]['title']} | {b['lacks']} | {state} |")
        return rows, stat

    def board_rows(self) -> list[str]:
        rows = ["| 基板 | 中身とつなぎ方 |", "|---|---|"]
        rows += [f"| {b['title']} | {b['note']} |" for b in self.doc["boards"]]
        rows += ["", "| 基板 | カード | 層 | 載る IC | LED |", "|---|---|---|---|---:|"]
        for c in self.doc["cards"]:
            ics = [b for b in self.blocks.values() if not b.get("external") and b["card"] == c["id"]]
            ic_text = "、".join(f"{b['refs']}（{'/'.join(parts_of(b))}{' ×' + str(b['count']) if b['count'] > 1 else ''}）" for b in ics)
            leds = sum(l["count"] for l in c.get("leds", []))
            rows.append(f"| {self.boards[c['board']]['title']} | `{c['id']}` {c['title']} | {c['layer']} | {ic_text} | {leds} |")
        return rows

    def led_rows(self) -> tuple[list[str], int]:
        rows = ["| カード | 表示する信号 | 個数 | 色 | 駆動 | 補足 |", "|---|---|---:|---|---|---|"]
        total = 0
        for c in self.doc["cards"]:
            for l in c.get("leds", []):
                total += l["count"]
                drv = l.get("driver")
                drv_text = f"{self.blocks[drv]['refs']}（{self.blocks[drv]['part']}）" if drv else "なし"
                rows.append(f"| `{c['id']}` | {'、'.join('`' + n + '`' for n in l['signals'])} | {l['count']} | {l['color']} | {drv_text} | {l.get('note', '')} |")
        return rows, total

    def crossing_rows(self) -> list[str]:
        groups: dict[str, list[dict]] = {}
        for s in self.doc["signals"]:
            ends = list(s["from"]) + [dest(t)[0] for t in s["to"]]
            boards = {self.board_of(e) for e in ends}
            if len(boards) < 2:
                continue
            for other in sorted(boards - {HUB}):
                groups.setdefault(other, []).append(s)
        rows = []
        for other, sigs in groups.items():
            n = sum(s["width"] for s in sigs)
            rows += [f"### {self.boards[HUB]['title']} ↔ {self.boards[other]['title']}（信号 {n} 本 + 電源）", "",
                     "| 信号 | 幅 | 向き |", "|---|---:|---|"]
            for s in sigs:
                src = {self.board_of(f) for f in s["from"]}
                way = "双方向" if len(src) > 1 else f"{self.boards[src.pop()]['title']} から"
                rows.append(f"| `{s['name']}` | {s['width']} | {way} |")
            rows.append("")
        return rows

    def signal_rows(self) -> list[str]:
        rows = ["| 信号 | 幅 | 極性 | 駆動元 | 受け先 | 区分 | 確定期限 | 内容 |", "|---|---:|---|---|---|---|---|---|"]
        ref = lambda i: self.blocks[i].get("refs") or self.blocks[i]["label"]  # noqa: E731
        for s in self.doc["signals"]:
            to = "、".join(ref(blk) + (f"（{lbl}）" if lbl else "") for blk, lbl in map(dest, s["to"]))
            rows.append(f"| `{s['name']}` | {s['width']} | {s['polarity']} | {'、'.join(ref(f) for f in s['from'])} | "
                        f"{to} | {s['scope']} | {s['deadline']} | {s['desc']} |")
        return rows


def export_svg(mmd: Path) -> bool:
    cli = os.environ.get("MMDC") or shutil.which("mmdc")
    if not cli:
        return False
    cmd = [cli, "-i", str(mmd), "-o", str(mmd.with_suffix(".svg")), "-b", "white"]
    if os.environ.get("MMDC_PUPPETEER_CONFIG"):
        cmd += ["-p", os.environ["MMDC_PUPPETEER_CONFIG"]]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--svg", action="store_true", help="mmdc で SVG を書き出す")
    args = ap.parse_args()
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    try:
        sy = System(doc, json.loads(BUILD.read_text(encoding="utf-8")))
    except DefError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    keep = {f"fig_{f['id']}.{x}" for f in doc["figures"] for x in ("mmd", "svg")} | {"README.md"}
    stale = sorted(p.name for p in OUT.iterdir() if p.name not in keep)
    md = ["# システム階層の生成物", "", HEADER, "",
          f"- 正本: `hw/system.json`（版 {doc['version']}）。実型番は `hw/builds/default.json` から引く", "- 解説: [`../SYSTEM.md`](../SYSTEM.md)",
          f"- 電源: {doc['power']['input']}。{doc['power']['note']}", "", "## 全体図", ""]
    for fig in doc["figures"]:
        text = sy.figure(fig)
        mmd = OUT / f"fig_{fig['id']}.mmd"
        mmd.write_text(text, encoding="utf-8", newline="\n")
        if args.svg and not export_svg(mmd):
            sy.warnings.append(f"図 {fig['id']}: mmdc が見つからないか失敗したため SVG を書き出していない")
        md += [f"### {fig['title']}", "", fig.get("note", ""), ""]
        if mmd.with_suffix(".svg").is_file():
            md += [f"SVG: [`fig_{fig['id']}.svg`](fig_{fig['id']}.svg)", ""]
        md += ["```mermaid", text.rstrip("\n"), "```", ""]
    ic, stat = sy.ic_rows()
    leds, led_total = sy.led_rows()
    by_board = "、".join(f"{sy.boards[b]['title']} {n} 個" for b, n in stat["by_board"].items())
    md += ["## IC 一覧", "", *ic, "",
           f"74 シリーズは {stat['total']} 個（{by_board}）、汎用型番で {len(stat['kinds'])} 種。"
           f"pinspec の無い型番: {'、'.join(sorted(stat['missing'], key=lambda p: int(p[3:]))) or 'なし'}。", "",
           "## 基板とカード", "", *sy.board_rows(), "",
           "## LED 一覧", "", *leds, "", f"LED は合計 {led_total} 個（フルカラーは 1 個と数える）。", "",
           "## 基板をまたぐ信号", "", "ローダ基板と io 基板は本体と接続口でつながる。接続口のピン数は、この信号数に電源と GND を足して決める。", "",
           *sy.crossing_rows(),
           "## 信号辞書", "", *sy.signal_rows(), "", "## 検査結果", ""]
    if stale:
        sy.warnings.append(f"使われていない生成物が残っている（削除してよい）: {'、'.join(stale)}")
    md += [f"- 警告: {w}" for w in sy.warnings] or ["- 警告なし"]
    (OUT / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(f"ok  ブロック {len(sy.blocks)} / 信号 {len(doc['signals'])} / 74 シリーズ {stat['total']} 個・{len(stat['kinds'])} 種 "
          f"/ LED {led_total} / 警告 {len(sy.warnings)}")
    for w in sy.warnings:
        print("  警告:", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
