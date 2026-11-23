"""信号レベルのモデル（docs/design/SYSTEM.md 4 章の制御の論理式と 5 章の位相）。

制御カードの論理式（74x154 のデコード、74x151 の表引き、グルーのゲート）と、
T2 で書き込み・T3 の終わりで更新する位相をピンのレベルで組み、1 命令ずつ進める。
sim.machine（命令レベル）と突き合わせることで、制御の論理式が命令セットどおりかを確かめる。
回路を変えたら、このモデルと docs/design/SYSTEM.md を同じ変更の中で直す。
"""
from __future__ import annotations

from . import isa
from .ic74 import Ic7489, ic74181, ic74182, ic74284, ic74285


def _nand(*x: int) -> int:
    return 0 if all(x) else 1


def _and(*x: int) -> int:
    return 1 if all(x) else 0


class Structural:
    """状態を持つ素子: PC（74x161 × 2）、A（74x374）、C・Z（74x74 の Q）、RAM（74x89 × 2）、出力ポート。"""

    def __init__(self, rom: list[int], in_ports: list[int] | None = None) -> None:
        self.rom = list(rom)
        self.in_ports = list(in_ports) if in_ports else [0xFF] * 16   # 未接続のポートは R バスのプルアップで FF（D31）
        self.pc = 0
        self.a = 0
        self.cq = 1      # C の Q = C_n。COUT_n をそのまま取り込む。リセットでプリセット（C = 0）
        self.zq = 1      # Z の Q = Z_n。ZERO_n をそのまま取り込む。リセットでプリセット（Z = 0）
        self.ram_lo = Ic7489(strict=False)
        self.ram_hi = Ic7489(strict=False)
        self.out = [0] * 16

    @property
    def c(self) -> int:
        return 1 - self.cq

    @property
    def z(self) -> int:
        return 1 - self.zq

    def ram_read(self, addr: int) -> int:
        lo = ~self.ram_lo.eval(addr, 0, me=0, we=1) & 0xF
        hi = ~self.ram_hi.eval(addr, 0, me=0, we=1) & 0xF
        return lo | (hi << 4)

    def cycle(self) -> None:
        """T0〜T3 の 1 命令分。"""
        op, fn, opd = isa.decode(self.rom[self.pc])
        ir11 = (fn >> 3) & 1
        y = [0 if k == op else 1 for k in range(16)]                 # IDEC（74x154）の出力 Yk_n

        # --- T0・T1: 組み合わせ回路が整定する ---
        do = self.ram_read(opd & 0xF)                                  # RAM-B（74x240）で反転を戻した値
        b = do if (op & 1) else opd                                    # BSEL: 選択 = IR12
        m = _nand(y[0], y[1])                                          # M
        cn_n = (1, 1, 0, self.cq, 0, 1, 1, 1)[op >> 1]                # CSEL（74x151）: 選択 = IR15..13
        lo = ic74181(self.a & 0xF, b & 0xF, fn, m, cn_n)
        cla = ic74182(cn_n, (lo.p, 1, 1, 1), (lo.g, 1, 1, 1))
        hi = ic74181(self.a >> 4, b >> 4, fn, m, cla.cnx)
        f = lo.f | (hi.f << 4)
        p = ic74285(self.a & 0xF, b & 0xF) | (ic74284(self.a & 0xF, b & 0xF) << 4)
        sel_mul = _nand(y[10], y[11])                                  # SEL_MUL
        in_ = 1 - y[14]                                                # IN（RSEL の出力を切る）
        r = (self.in_ports[fn] & 0xFF) if in_ else (p if sel_mul else f)    # R バス
        zero_n = 0 if r == 0 else 1                                    # ZDET（74x521）
        a_ld = _and(y[8], y[9], y[12], y[13], y[15])
        c_ld = _nand(*y[2:10])                                         # 74x30（8 入力 NAND）
        z_ld = _and(y[12], y[13], y[15])
        g_n = y[15] | ir11                                             # COND（74x151）のストローブ
        data = (1, self.z, self.zq, self.c, self.cq, 0, 0, 0)          # COND の D0〜D7（5〜7 は予約で L）
        pc_ld_n = 1 if g_n else 1 - data[fn & 7]                       # 反転出力 W
        pc_en = _nand(1 - y[15], ir11)                                 # HLT で計数を止める

        # --- T2: 書き込みストローブ（WR_n・OSTB_n） ---
        if y[12] == 0:
            self.ram_lo.eval(opd & 0xF, self.a & 0xF, me=0, we=0)
            self.ram_hi.eval(opd & 0xF, self.a >> 4, me=0, we=0)
        if y[13] == 0:
            self.out[fn] = self.a

        # --- T3 の終わり: 更新ストローブ（ACK・CCK・ZCK・PCK）で同時に更新 ---
        if a_ld:
            self.a = r
        if c_ld:
            self.cq = hi.cn4                                           # COUT_n
        if z_ld:
            self.zq = zero_n
        if pc_ld_n == 0:
            self.pc = opd
        elif pc_en:
            self.pc = (self.pc + 1) & 0xFF
