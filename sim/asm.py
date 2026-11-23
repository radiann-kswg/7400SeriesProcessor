"""アセンブラ（命令セット草案 v0.1）。

書式:
    [ラベル:] ニーモニック [オペランド[, オペランド]]   ; コメント
    .equ 名前 値
数値は 10 進 / 0x.. / 0b..。ニーモニックは sim.isa と docs/ARCHITECTURE.md を参照。
"""
from __future__ import annotations

import re

from . import isa


class AsmError(Exception):
    pass


def _parse_lines(source: str):
    for lineno, raw in enumerate(source.splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        if line:
            yield lineno, line


def assemble(source: str) -> list[int]:
    symbols: dict[str, int] = {}
    items: list[tuple[int, str, list[str]]] = []

    for lineno, line in _parse_lines(source):                    # パス 1: ラベル収集
        m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", line)
        if m:
            name = m.group(1)
            if name in symbols:
                raise AsmError(f"{lineno} 行: ラベル {name} の重複")
            symbols[name] = len(items)
            line = m.group(2).strip()
            if not line:
                continue
        parts = line.split(None, 1)
        mnemonic = parts[0].upper()
        args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
        if mnemonic == ".EQU":
            eq = parts[1].split() if len(parts) > 1 else []
            if len(eq) != 2:
                raise AsmError(f"{lineno} 行: .equ 名前 値")
            if eq[0] in symbols:
                raise AsmError(f"{lineno} 行: シンボル {eq[0]} の重複")
            try:
                symbols[eq[0]] = int(eq[1], 0)
            except ValueError:
                raise AsmError(f"{lineno} 行: .equ の値 {eq[1]} が数値でない") from None
            continue
        items.append((lineno, mnemonic, args))

    if len(items) > 256:
        raise AsmError("プログラムが 256 語を超えた")

    def value(lineno: int, text: str, limit: int) -> int:
        try:
            v = int(text, 0)
        except ValueError:
            if text not in symbols:
                raise AsmError(f"{lineno} 行: 未定義のシンボル {text}") from None
            v = symbols[text]
        if not 0 <= v <= limit:
            raise AsmError(f"{lineno} 行: {text} = {v} が範囲 0..{limit} の外")
        return v

    def need(lineno: int, mnemonic: str, args: list[str], n: int) -> None:
        if len(args) != n:
            raise AsmError(f"{lineno} 行: {mnemonic} のオペランドは {n} 個")

    words: list[int] = []
    for lineno, mn, args in items:                               # パス 2: 符号化
        if mn in isa.IMPLIED:
            need(lineno, mn, args, 0)
            words.append(isa.encode(*isa.IMPLIED[mn]))
        elif mn in isa.RAW:
            need(lineno, mn, args, 2)
            op = isa.RAW[mn]
            limit = 15 if (op & 1) else 255
            words.append(isa.encode(op, value(lineno, args[0], 15), value(lineno, args[1], limit)))
        elif mn in isa.PAIRED:                                   # メモリ形式
            need(lineno, mn, args, 1)
            op, fn = isa.PAIRED[mn]
            words.append(isa.encode(op + 1, fn, value(lineno, args[0], 15)))
        elif mn.endswith("I") and mn[:-1] in isa.PAIRED:         # 即値形式
            need(lineno, mn, args, 1)
            op, fn = isa.PAIRED[mn[:-1]]
            limit = 15 if op == isa.MULI else 255
            words.append(isa.encode(op, fn, value(lineno, args[0], limit)))
        elif mn == "ST":
            need(lineno, mn, args, 1)
            words.append(isa.encode(isa.ST, 0, value(lineno, args[0], 15)))
        elif mn in ("OUT", "IN"):
            need(lineno, mn, args, 1)
            op = isa.OUT if mn == "OUT" else isa.IN
            words.append(isa.encode(op, value(lineno, args[0], 15), 0))
        elif mn in isa.JUMPS:
            need(lineno, mn, args, 1)
            words.append(isa.encode(isa.JP, isa.JUMPS[mn], value(lineno, args[0], 255)))
        else:
            raise AsmError(f"{lineno} 行: 未知のニーモニック {mn}")
    return words
