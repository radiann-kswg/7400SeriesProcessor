"""アセンブルして実行する。  python -m sim.run プログラム.asm [--trace] [--in ポート=値 ...]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import isa
from .asm import assemble
from .machine import Machine


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("--trace", action="store_true", help="1 命令ごとに状態を表示")
    ap.add_argument("--in", dest="inputs", action="append", default=[], metavar="PORT=VALUE")
    ap.add_argument("--max-cycles", type=int, default=100_000)
    args = ap.parse_args(argv)

    rom = assemble(args.source.read_text(encoding="utf-8"))
    ports = [0xFF] * 16                       # 未接続のポートは R バスのプルアップで FF（D31）
    for item in args.inputs:
        port, val = item.split("=", 1)
        ports[int(port, 0)] = int(val, 0)
    m = Machine(rom, ports)
    while not m.halted and m.cycles < args.max_cycles:
        pc = m.pc
        op, fn, operand = isa.decode(m.rom[pc])
        m.step()
        if args.trace:
            print(f"{m.cycles:5d} pc={pc:02X} ir={op:X}{fn:X}{operand:02X} "
                  f"A={m.a:02X} C={m.c} Z={m.z}")
    if not m.halted:
        print(f"{args.max_cycles} サイクルで打ち切り", file=sys.stderr)
        return 1
    print(f"words={len(rom)} cycles={m.cycles} A={m.a:02X} C={m.c} Z={m.z}")
    print("OUT:", " ".join(f"{v:02X}" for v in m.out[:4]), "...")
    print("NIXIE:", m.nixie_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
