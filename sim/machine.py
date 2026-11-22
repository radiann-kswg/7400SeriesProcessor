"""命令レベルエミュレータ（単一サイクル・ハーバード構成の草案 v0.1）。

データパスは sim.ic74 の IC モデルを実回路と同じつなぎ方で呼び出して評価する。
構成（どの役割をどの IC で実装するか）が変わったら、ここの組み立て部分を差し替える。
"""
from __future__ import annotations

from . import isa
from .ic74 import Ic7489, ic74141, ic74181, ic74182, ic74284, ic74285


class Machine:
    def __init__(self, rom: list[int], in_ports: list[int] | None = None) -> None:
        if len(rom) > 256:
            raise ValueError("プログラムは 256 語まで")
        self.rom = list(rom)
        self.pc = 0
        self.a = 0
        self.c = 0
        self.z = 0
        self.ram_lo = Ic7489()
        self.ram_hi = Ic7489()
        self.out = [0] * 16
        self.in_ports = list(in_ports) if in_ports else [0] * 16
        self.halted = False
        self.cycles = 0

    # --- データパス -------------------------------------------------
    @staticmethod
    def alu(a: int, b: int, s: int, m: int, carry_in: int) -> tuple[int, int]:
        """74x181 × 2 + 74x182 の 8bit ALU。戻り値は (F, 桁上げ出力)。"""
        cn = 0 if carry_in else 1
        lo = ic74181(a & 0xF, b & 0xF, s, m, cn)
        cla = ic74182(cn, (lo.p, 1, 1, 1), (lo.g, 1, 1, 1))
        hi = ic74181((a >> 4) & 0xF, (b >> 4) & 0xF, s, m, cla.cnx)
        return lo.f | (hi.f << 4), 0 if hi.cn4 else 1

    def ram_read(self, addr: int) -> int:
        lo = ~self.ram_lo.eval(addr, 0, me=0, we=1) & 0xF   # 反転出力を戻す
        hi = ~self.ram_hi.eval(addr, 0, me=0, we=1) & 0xF
        return lo | (hi << 4)

    def ram_write(self, addr: int, value: int) -> None:
        self.ram_lo.eval(addr, value & 0xF, me=0, we=0)
        self.ram_hi.eval(addr, (value >> 4) & 0xF, me=0, we=0)

    @staticmethod
    def multiply(a: int, b: int) -> int:
        return ic74285(a, b) | (ic74284(a, b) << 4)

    # --- 実行 -------------------------------------------------------
    def step(self) -> None:
        if self.halted:
            return
        if self.pc >= len(self.rom):
            raise RuntimeError(f"PC={self.pc:#04x} がプログラムの外に出た")
        op, fn, operand = isa.decode(self.rom[self.pc])
        next_pc = (self.pc + 1) & 0xFF

        if op <= isa.MULM:
            src = self.ram_read(operand & 0xF) if (op & 1) else operand
            group = op >> 1
            if group == 0:                                   # 論理
                self.a, _ = self.alu(self.a, src, fn, 1, 0)
                self.z = int(self.a == 0)
            elif group in (1, 2, 3):                         # 算術
                cin = (0, 1, self.c)[group - 1]
                self.a, self.c = self.alu(self.a, src, fn, 0, cin)
                self.z = int(self.a == 0)
            elif group == 4:                                 # 比較（A は不変）
                f, self.c = self.alu(self.a, src, fn, 0, 1)
                self.z = int(f == 0)
            else:                                            # 乗算
                self.a = self.multiply(self.a & 0xF, src & 0xF)
                self.z = int(self.a == 0)
        elif op == isa.ST:
            self.ram_write(operand & 0xF, self.a)
        elif op == isa.OUT:
            self.out[fn] = self.a
        elif op == isa.IN:
            self.a = self.in_ports[fn] & 0xFF
            self.z = int(self.a == 0)
        else:                                                # JP
            if fn == isa.COND_HALT:
                self.halted = True
                next_pc = self.pc
            else:
                taken = {
                    isa.COND_ALWAYS: True,
                    isa.COND_Z: bool(self.z),
                    isa.COND_NZ: not self.z,
                    isa.COND_C: bool(self.c),
                    isa.COND_NC: not self.c,
                }.get(fn)
                if taken is None:
                    raise RuntimeError(f"未定義の分岐条件 {fn:#x}（PC={self.pc:#04x}）")
                if taken:
                    next_pc = operand
        self.pc = next_pc
        self.cycles += 1

    def run(self, max_cycles: int = 100_000) -> int:
        while not self.halted:
            if self.cycles >= max_cycles:
                raise RuntimeError(f"{max_cycles} サイクル以内に停止しなかった")
            self.step()
        return self.cycles

    # --- 表示 -------------------------------------------------------
    def nixie_digits(self, ports: tuple[int, ...] = (0, 1)) -> list[int | None]:
        """出力ポートの各ニブルを 74x141 に通した結果。添字 0 が最下位桁。"""
        digits: list[int | None] = []
        for p in ports:
            digits.append(ic74141(self.out[p] & 0xF))
            digits.append(ic74141((self.out[p] >> 4) & 0xF))
        return digits

    def nixie_text(self, ports: tuple[int, ...] = (0, 1)) -> str:
        return "".join("_" if d is None else str(d) for d in reversed(self.nixie_digits(ports)))
