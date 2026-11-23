#!/usr/bin/env python3
"""カード定義（hw/cards/<card>/card.json）から配線表と KiCad 回路図を生成する。

    python scripts/gen_card.py <card> [<card> ...]   指定カードだけ
    python scripts/gen_card.py --all [--svg] [--erc]

生成物（手で編集しない）:
    hw/cards/<card>/WIRING.md          IC ごとのピン配線表とネット一覧
    hw/cards/<card>/<card>.kicad_sch   実ピン配置どおりの DIP 箱シンボル + ネットラベルの回路図
    hw/cards/<card>/svg/<card>.svg     --svg 指定時（kicad-cli が必要）

ピン情報は pinspec（一次資料を目視照合した JSON）からだけ取る。pinspec が無い型番を含む
カードは生成しない。探す順は hw/pinspec/ → collection/pcb-demo/_carrier/pinspec/。
受動部品（kind が R / C / CP）は 2 端子の部品として扱い、pinspec は要らない。
Python 標準ライブラリのみで動く。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "hw" / "cards"
PINSPEC_DIRS = [ROOT / "hw" / "pinspec", ROOT / "collection" / "pcb-demo" / "_carrier" / "pinspec"]
NC = "NC"
POWER_NETS = {"power": "VCC", "ground": "GND"}
KICAD_PIN_TYPE = {
    "input": "input", "output": "output", "tri_state": "tri_state",
    "open_collector": "open_collector", "bidirectional": "bidirectional",
    "nc": "no_connect", "power": "power_in", "ground": "power_in", "passive": "passive",
}
# 受動部品の種類 → (1 番の名前, 2 番の名前)。CP は有極性コンデンサで 1 番が +
PASSIVES = {"R": ("1", "2"), "C": ("1", "2"), "CP": ("+", "-")}
DEFAULT_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
_NS = uuid.UUID("7400c0de-0000-4000-8000-000000000000")


class CardError(Exception):
    pass


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_pinspec(part: str) -> tuple[dict, Path]:
    for d in PINSPEC_DIRS:
        p = d / f"{part}.json"
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")), p
    raise CardError(f"{part}: pinspec が無い（一次資料の照合が済むまで生成しない）")


def load_card(card: str) -> dict:
    path = CARDS / card / "card.json"
    if not path.is_file():
        raise CardError(f"{rel(path)} が無い")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("card") != card:
        raise CardError(f"{card}: card.json の card がフォルダ名と一致しない")
    return data


def passive_spec(kind: str) -> dict:
    if kind not in PASSIVES:
        raise CardError(f"受動部品の種類 {kind} は未対応（{' / '.join(PASSIVES)}）")
    return {"package_pins": 2, "pins": {str(i): {"name": n, "dir": "passive"}
                                        for i, n in enumerate(PASSIVES[kind], 1)}}


def net_purposes(data: dict) -> dict[str, str]:
    """card.json の nets（ネット → 用途）。"A0..7" のような範囲は 1 本ずつに展開する。"""
    out = {}
    for key, text in data.get("nets", {}).items():
        m = re.fullmatch(r"(.*?)(\d+)\.\.(\d+)", key)
        out.update(dict.fromkeys([f"{m[1]}{i}" for i in range(int(m[2]), int(m[3]) + 1)] if m else [key], text))
    return out


def check_card(data: dict) -> tuple[list[dict], dict[str, list[str]], list[str]]:
    """定義を検証し、(部品リスト, ネット→接続先, 警告) を返す。"""
    comps, nets, dirs, warnings = [], {}, {}, []
    refs = [c["ref"] for c in data["components"]]
    if data.get("connector"):
        refs.append(data["connector"]["ref"])
    dup = sorted({r for r in refs if refs.count(r) > 1})
    if dup:
        raise CardError(f"参照名が重複している: {dup}")
    for comp in data["components"]:
        spec, spec_path = (passive_spec(comp["kind"]), None) if "kind" in comp else load_pinspec(comp["part"])
        pins, why = spec["pins"], comp.get("nc", {})
        missing = sorted(set(pins) - set(comp["pins"]), key=int)
        extra = sorted(set(comp["pins"]) - set(pins), key=int)
        if missing or extra:
            raise CardError(f"{comp['ref']}: 未割当ピン {missing} / pinspec に無いピン {extra}")
        for num, pin in pins.items():
            net, at = comp["pins"][num], f"{comp['ref']} ピン {num}（{pin['name']}）"
            want = POWER_NETS.get(pin["dir"])
            if want and net != want:
                raise CardError(f"{at}は {want} に接続する")
            if not want and net in POWER_NETS.values() and pin["dir"] not in ("input", "passive"):
                raise CardError(f"{at}・{pin['dir']} を {net} に直結している")
            if net == NC:
                if pin["dir"] == "input":
                    warnings.append(f"{at}は入力なのに未接続")
                if not why.get(num):
                    warnings.append(f"{at}の未接続に理由（nc）が無い")
                continue
            nets.setdefault(net, []).append(f"{comp['ref']}.{num}（{pin['name']}）")
            dirs.setdefault(net, []).append(pin["dir"])
        comps.append({"def": comp, "spec": spec, "spec_path": spec_path})
    for sig in data.get("connector", {}).get("signals", []):
        if sig not in nets:
            warnings.append(f"コネクタ信号 {sig} はどの IC にも接続されていない")
        nets.setdefault(sig, []).append(f"{data['connector']['ref']}（コネクタ）")
        dirs.setdefault(sig, []).append("connector")
    resistor_paths = {}
    for c in comps:
        d = c["def"]
        if d.get("kind") == "R":
            a, b = d["pins"]["1"], d["pins"]["2"]
            if NC in (a, b):
                continue
            resistor_paths.setdefault(a, set()).add(b)
            resistor_paths.setdefault(b, set()).add(a)
    driven = set(POWER_NETS.values())
    driven.update(net for net, d in dirs.items() if any(x in ("output", "connector") for x in d))
    purpose = net_purposes(data)
    for net, ends in sorted(nets.items()):
        if len(ends) == 1:
            warnings.append(f"ネット {net} の接続先が 1 か所だけ（{ends[0]}）")
        if net in POWER_NETS.values():
            continue
        if not purpose.get(net):
            warnings.append(f"ネット {net} に用途（nets）が書かれていない")
        d = dirs[net]
        if d.count("output") > 1:
            warnings.append(f"ネット {net} にトーテムポール出力が {d.count('output')} 個つながっている")
        if "input" in d:
            reached, pending = set(), [net]
            while pending:
                current = pending.pop()
                if current in reached:
                    continue
                reached.add(current)
                if current in driven:
                    break
                pending.extend(resistor_paths.get(current, set()) - reached)
            if not reached & driven:
                warnings.append(f"ネット {net} に駆動元が無い（直流経路なし）")
    warnings += [f"用途だけ書かれたネット {n}（どこにもつながっていない）" for n in purpose if n not in nets]
    return comps, nets, warnings


# --- 配線表 -----------------------------------------------------------
def write_wiring(card: str, data: dict, comps, nets, warnings) -> Path:
    out = [f"# {card} 配線表", "",
           "> `scripts/gen_card.py` による生成物。手で編集せず `card.json` を直して再生成する。", "",
           f"- 名称: {data.get('title', '')}",
           f"- 実装する役割: {', '.join(data.get('roles', []))}",
           f"- 状態: {data.get('status', 'draft')}"]
    out += [f"- 回路図: [`{card}.kicad_sch`]({card}.kicad_sch) / [`svg/{card}.svg`](svg/{card}.svg)"]
    if data.get("notes"):
        out += ["", *[f"- 補足: {n}" for n in data["notes"]]]
    for c in comps:
        d, spec = c["def"], c["spec"]
        if "kind" in d:
            continue
        src = spec.get("source", {})
        out += ["", f"## {d['ref']} — {d['part']}（{d.get('device', '実型番未定')}）", "",
                f"- 役割: {d.get('role', '')}",
                f"- pinspec: `{rel(c['spec_path'])}`（{src.get('doc_id', '?')} / 照合日 {src.get('checked', '?')}"
                f" / 読み取り信頼度 {src.get('confidence', '?')}%）", "",
                "| ピン | 名称 | 方向 | 接続ネット |", "|---:|---|---|---|"]
        for num in sorted(spec["pins"], key=int):
            pin = spec["pins"][num]
            name = pin["name"] + ("（L アクティブ）" if "active_low" in pin.get("attr", []) else "")
            net = d["pins"][num]
            shown = f"（未接続: {d.get('nc', {}).get(num, '理由なし')}）" if net == NC else f"`{net}`"
            out.append(f"| {num} | {name} | {pin['dir']} | {shown} |")
    passives = [c["def"] for c in comps if "kind" in c["def"]]
    if passives:
        out += ["", "## 受動部品", "", "| 参照名 | 種類 | 値 | 1 番 | 2 番 | 役割 |", "|---|---|---|---|---|---|"]
        out += [f"| {p['ref']} | {p['kind']} | {p.get('value', '')} | `{p['pins']['1']}` | `{p['pins']['2']}` | "
                f"{p.get('role', '')} |" for p in passives]
    conn = data.get("connector")
    if conn:
        out += ["", f"## {conn['ref']} — カードコネクタ（{conn.get('note', '')}）", "",
                "| 端子 | 信号 |", "|---:|---|"]
        out += [f"| {i} | `{s}` |" for i, s in enumerate(conn["signals"], 1)]
    purpose = {"VCC": "5 V 電源", "GND": "グラウンド", **net_purposes(data)}
    out += ["", "## ネット一覧", "", "| ネット | 用途 | 接続先 |", "|---|---|---|"]
    out += [f"| `{n}` | {purpose.get(n, '')} | {'、'.join(ends)} |" for n, ends in sorted(nets.items())]
    out += ["", "## 検査結果", ""]
    out += [f"- 警告: {w}" for w in warnings] or ["- 警告なし"]
    path = CARDS / card / "WIRING.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return path


# --- KiCad 回路図 -----------------------------------------------------
PITCH, HALF_W, PIN_LEN, STUB = 2.54, 10.16, 5.08, 2.54
FONT = "(effects (font (size 1.27 1.27)))"


def _uid(*key: str) -> str:
    return str(uuid.uuid5(_NS, "/".join(key)))


def _f(v: float) -> str:
    return f"{round(v, 4):g}"


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lib_symbol(name: str, ref_prefix: str, left: list, right: list,
                half_w: float = HALF_W) -> tuple[str, dict, float]:
    """left / right は上から順の (番号, 名称, 種別)。戻り値は (S 式, ピン座標, 半高)。"""
    rows = max(len(left), len(right), 1)
    half_h = rows * PITCH / 2 + PITCH / 2
    top = (rows - 1) * PITCH / 2
    pos, pins = {}, []
    for side, plist in (("L", left), ("R", right)):
        for i, (num, pname, ptype) in enumerate(plist):
            x = -(half_w + PIN_LEN) if side == "L" else half_w + PIN_LEN
            y = top - i * PITCH
            pos[num] = (x, y, side)
            pins.append(f'        (pin {ptype} line (at {_f(x)} {_f(y)} {0 if side == "L" else 180}) '
                        f'(length {_f(PIN_LEN)}) (name {_q(pname)} {FONT}) (number {_q(num)} {FONT}))')
    body = "\n".join([
        f'    (symbol {_q("card:" + name)} (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
        f'      (property "Reference" {_q(ref_prefix)} (at 0 {_f(half_h + 1.27)} 0) {FONT})',
        f'      (property "Value" {_q(name)} (at 0 {_f(-half_h - 1.27)} 0) {FONT})',
        '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        f'      (symbol {_q(name + "_0_1")}',
        f'        (rectangle (start {_f(-half_w)} {_f(half_h)}) (end {_f(half_w)} {_f(-half_h)}) '
        '(stroke (width 0.254) (type default)) (fill (type background))))',
        f'      (symbol {_q(name + "_1_1")}', *pins, "      ))"])
    return body, pos, half_h


def write_schematic(card: str, data: dict, comps) -> Path:
    root_uuid = _uid(card, "root")
    libs, body = [], []
    conn = data.get("connector")
    big = sum("kind" not in c["def"] for c in comps) > 2
    paper, col_w, row_h, per_row = ("A3", 88.9, 114.3, 4) if big else ("A4", 88.9, 114.3, 2)
    x0 = 127.0 if conn else 63.5

    def place(lib_name, ref, value, pos, half_h, cx, cy, nets_by_pin, datasheet="", mpn=""):
        hide = f'(at {_f(cx)} {_f(cy)} 0) (effects (font (size 1.27 1.27)) hide)'
        body.append("\n".join([
            f'  (symbol (lib_id {_q("card:" + lib_name)}) (at {_f(cx)} {_f(cy)} 0) (unit 1)',
            '    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
            f'    (uuid {_q(_uid(card, ref))})',
            f'    (property "Reference" {_q(ref)} (at {_f(cx)} {_f(cy - half_h - 1.27)} 0) {FONT})',
            f'    (property "Value" {_q(value)} (at {_f(cx)} {_f(cy + half_h + 1.27)} 0) {FONT})',
            f'    (property "Footprint" "" {hide})',
            f'    (property "Datasheet" {_q(datasheet)} {hide})',
            *([f'    (property "MPN" {_q(mpn)} {hide})'] if mpn else []),
            *[f'    (pin {_q(n)} (uuid {_q(_uid(card, ref, "pin", n))}))' for n in pos],
            f'    (instances (project {_q(card)} (path {_q("/" + root_uuid)} (reference {_q(ref)}) (unit 1))))',
            '  )']))
        for num, (px, py, side) in pos.items():
            net = nets_by_pin[num]
            x, y = cx + px, cy - py
            if net == NC:
                body.append(f'  (no_connect (at {_f(x)} {_f(y)}) (uuid {_q(_uid(card, ref, "nc", num))}))')
                continue
            x2 = x - STUB if side == "L" else x + STUB
            body.append(f'  (wire (pts (xy {_f(x)} {_f(y)}) (xy {_f(x2)} {_f(y)})) '
                        f'(stroke (width 0) (type default)) (uuid {_q(_uid(card, ref, "w", num))}))')
            angle, just = (180, "right") if side == "L" else (0, "left")
            body.append(f'  (label {_q(net)} (at {_f(x2)} {_f(y)} {angle}) '
                        f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) '
                        f'(uuid {_q(_uid(card, ref, "l", num))}))')

    if conn:
        seen, right = set(), []
        for i, sig in enumerate(conn["signals"], 1):
            ptype = "power_out" if sig in POWER_NETS.values() and sig not in seen else "passive"
            seen.add(sig)
            right.append((str(i), sig, ptype))
        name = f"CONN_{len(right)}"
        sym, pos, half_h = _lib_symbol(name, "J", [], right)
        libs.append(sym)
        place(name, conn["ref"], conn.get("value", name), pos, half_h, 50.8, 101.6,
              {str(i): s for i, s in enumerate(conn["signals"], 1)})

    done = set()
    ics = [c for c in comps if "kind" not in c["def"]]
    for idx, c in enumerate(ics):
        d, spec = c["def"], c["spec"]
        n = int(spec["package_pins"])
        nums = [str(i) for i in range(1, n + 1)]
        info = lambda k: (k, spec["pins"][k]["name"], KICAD_PIN_TYPE[spec["pins"][k]["dir"]])  # noqa: E731
        left = [info(k) for k in nums[: n // 2]]
        right = [info(k) for k in reversed(nums[n // 2:])]
        sym, pos, half_h = _lib_symbol(d["part"], "U", left, right)
        if d["part"] not in done:
            libs.append(sym)
            done.add(d["part"])
        cx = x0 + (idx % per_row) * col_w
        cy = 101.6 + (idx // per_row) * row_h
        place(d["part"], d["ref"], d.get("device", d["part"]), pos, half_h, cx, cy, d["pins"],
              d.get("datasheet") or c["spec"].get("source", {}).get("doc_id", ""), d.get("device", ""))

    # 受動部品は IC の下に 1 列に並べる（2 端子の小さな箱。左が 1 番）
    y = 101.6 + ((len(ics) - 1) // per_row) * row_h + 50.8
    for i, c in enumerate(c for c in comps if "kind" in c["def"]):
        d = c["def"]
        n1, n2 = PASSIVES[d["kind"]]
        sym, pos, half_h = _lib_symbol(d["kind"], d["kind"][0], [("1", n1, "passive")], [("2", n2, "passive")], 2.54)
        if d["kind"] not in done:
            libs.append(sym)
            done.add(d["kind"])
        place(d["kind"], d["ref"], d.get("value", ""), pos, half_h, x0 + i * 38.1, y, d["pins"])

    purpose = data.get("nets", {})
    if purpose:  # ネットの用途を回路図の左下に書く
        note = "Nets:\n" + "\n".join(f"{n}: {purpose[n]}" for n in sorted(purpose))
        body.append(f'  (text {_q(note).replace(chr(10), chr(92) + "n")} (exclude_from_sim no) '
                    f'(at 12.7 {_f(y + 25.4)} 0) (effects (font (face "Yu Gothic") (size 1.27 1.27)) '
                    f'(justify left top)) (uuid {_q(_uid(card, "nets"))}))')

    text = "\n".join([
        '(kicad_sch (version 20231120) (generator "gen_card") (generator_version "0.1")',
        f'  (uuid {_q(root_uuid)})', f'  (paper {_q(paper)})',
        f'  (title_block (title {_q(card)}) (rev {_q(str(data.get("status", "draft")))}) '
        '(comment 1 "Generated by scripts/gen_card.py from card.json - do not edit by hand"))',
        '  (lib_symbols', *libs, '  )', *body,
        '  (sheet_instances (path "/" (page "1")))', ')', ''])
    path = CARDS / card / f"{card}.kicad_sch"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


# --- kicad-cli --------------------------------------------------------
def find_cli() -> str | None:
    for c in (os.environ.get("KICAD_CLI"), shutil.which("kicad-cli"), DEFAULT_CLI):
        if c and Path(c).is_file():
            return c
    return None


def export_svg(cli: str, sch: Path) -> None:
    out = sch.parent / "svg"
    out.mkdir(exist_ok=True)
    subprocess.run([cli, "sch", "export", "svg", "--exclude-drawing-sheet", "--no-background-color",
                    "--output", str(out), str(sch)], check=True, stdout=subprocess.DEVNULL)


def run_erc(cli: str, sch: Path) -> int:
    tmp = ROOT / ".temp" / "erc"
    tmp.mkdir(parents=True, exist_ok=True)
    rpt = tmp / f"{sch.stem}.json"
    subprocess.run([cli, "sch", "erc", "--severity-all", "--format", "json", "--output", str(rpt), str(sch)],
                   check=True, stdout=subprocess.DEVNULL)
    report = json.loads(rpt.read_text(encoding="utf-8"))
    # lib_symbol_issues は「シンボルを回路図に埋め込んでいてライブラリ表に無い」ことの通知なので数えない
    items = [v for sheet in report.get("sheets", []) for v in sheet.get("violations", [])
             if v.get("type") != "lib_symbol_issues"]
    for v in items:
        print(f"    ERC {v.get('severity')}: {v.get('type')} - {v.get('description')}")
    return len(items)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards", nargs="*")
    ap.add_argument("--all", action="store_true", help="hw/cards/ 以下のすべて")
    ap.add_argument("--svg", action="store_true", help="kicad-cli で SVG を書き出す")
    ap.add_argument("--erc", action="store_true", help="kicad-cli で ERC を実行する")
    args = ap.parse_args()
    names = sorted(p.parent.name for p in CARDS.glob("*/card.json")) if args.all else args.cards
    if not names:
        ap.error("カード名か --all を指定する")
    cli = find_cli() if (args.svg or args.erc) else None
    if (args.svg or args.erc) and not cli:
        print("kicad-cli が見つからない（KICAD_CLI を設定する）", file=sys.stderr)
        return 2
    failed = 0
    for card in names:
        try:
            data = load_card(card)
            comps, nets, warnings = check_card(data)
        except CardError as e:
            print(f"[skip] {card}: {e}")
            failed += 1
            continue
        write_wiring(card, data, comps, nets, warnings)
        sch = write_schematic(card, data, comps)
        n_ic = sum("kind" not in c["def"] for c in comps)
        print(f"[ok]   {card}: IC {n_ic} 個 / 受動部品 {len(comps) - n_ic} 個 / ネット {len(nets)} 本 / 警告 {len(warnings)} 件")
        if args.svg:
            export_svg(cli, sch)
        if args.erc:
            n = run_erc(cli, sch)
            print(f"    ERC 違反 {n} 件")
            failed += 1 if n else 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
