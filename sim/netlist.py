"""カード定義（hw/cards/<card>/card.json）の配線どおりに IC モデルをつないで評価する（信号レベルのモデル）。

ピン番号 → ピン名は pinspec から引き、IC モデルにはピン名で値を渡す。組み合わせ回路だけを扱い、
入力がそろった IC から順に評価する。VCC へのプルアップ抵抗（集合抵抗は共通端子が VCC のもの）がつながる
ネットは、どの出力も駆動しなければ H とする。
"""
from __future__ import annotations

import json
from pathlib import Path

from .ic74 import ic74181, ic74182, ic74284, ic74285

ROOT = Path(__file__).resolve().parents[1]
PINSPEC_DIRS = [ROOT / "hw" / "pinspec", ROOT / "collection" / "pcb-demo" / "_carrier" / "pinspec"]


def _bus(v: dict, prefix: str, n: int = 4) -> int:
    return sum(v[f"{prefix}{i}"] << i for i in range(n))


def _m181(v: dict) -> dict:
    o = ic74181(_bus(v, "A"), _bus(v, "B"), _bus(v, "S"), v["M"], v["Cn"])
    return {**{f"F{i}": (o.f >> i) & 1 for i in range(4)}, "Cn+4": o.cn4, "X": o.p, "Y": o.g, "A=B": o.aeqb}


def _m182(v: dict) -> dict:
    o = ic74182(v["Cn"], [v[f"P{i}"] for i in range(4)], [v[f"G{i}"] for i in range(4)])
    return {"Cn+x": o.cnx, "Cn+y": o.cny, "Cn+z": o.cnz, "P": o.p, "G": o.g}


def _word(v: dict, w: str) -> int:
    return sum(v[f"{w}{c}"] << i for i, c in enumerate("ABCD"))


def _m284(v: dict) -> dict:
    y = ic74284(_word(v, "1"), _word(v, "2"), v["GA"], v["GB"])
    return {f"Y{4 + i}": (y >> i) & 1 for i in range(4)}


def _m285(v: dict) -> dict:
    y = ic74285(_word(v, "1"), _word(v, "2"), v["GA"], v["GB"])
    return {f"Y{i}": (y >> i) & 1 for i in range(4)}


MODELS = {"74x181": _m181, "74x182": _m182, "74x284": _m284, "74x285": _m285}


def _pinspec(part: str) -> dict:
    for d in PINSPEC_DIRS:
        p = d / f"{part}.json"
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"{part} の pinspec が無い")


class Card:
    def __init__(self, name: str):
        data = json.loads((ROOT / "hw" / "cards" / name / "card.json").read_text(encoding="utf-8"))
        self.ics, self.pullups = [], set()
        for c in data["components"]:
            if "kind" in c:
                pins = c["pins"]  # R はどちらかの端子、RN（集合抵抗）は 1 番の共通端子が VCC のときプルアップ
                if (c["kind"] == "R" and "VCC" in pins.values()) or (c["kind"] == "RN" and pins["1"] == "VCC"):
                    self.pullups |= set(pins.values()) - {"VCC"}
                continue
            names = {num: p["name"] for num, p in _pinspec(c["part"])["pins"].items()}
            self.ics.append((MODELS[c["part"]], {names[num]: net for num, net in c["pins"].items()}))

    def eval(self, inputs: dict[str, int]) -> dict[str, int]:
        """inputs（ネット名 → 0/1）を与え、全ネットの値を返す。"""
        # プルアップのネットを先に H と置き、オープンコレクタ出力の値で上書きする
        # ponytail: 1 本のネットを複数のオープンコレクタ出力で共有する（ワイヤード AND）のは未対応
        nets = {"VCC": 1, "GND": 0, **dict.fromkeys(self.pullups, 1), **inputs}
        todo = self.ics
        while todo:
            left = []
            for model, pins in todo:
                try:
                    out = model({p: nets[n] for p, n in pins.items() if n in nets})
                except KeyError:  # 入力がまだそろっていない
                    left.append((model, pins))
                    continue
                nets.update({pins[p]: v for p, v in out.items() if pins.get(p, "NC") != "NC"})
            if len(left) == len(todo):
                raise ValueError("入力のそろわない IC が残った（未駆動のネットかループがある）")
            todo = left
        return nets
