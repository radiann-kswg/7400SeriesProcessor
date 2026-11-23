"""信号レベルのモデル（sim.structural）と命令レベルのエミュレータ（sim.machine）の突き合わせ。"""
import random
import unittest

from sim import isa
from sim.machine import Machine
from sim.structural import Structural


def random_program(rng: random.Random) -> list[int]:
    rom = []
    for k in range(16):                                   # RAM を全番地初期化してから始める
        rom += [isa.encode(isa.LOGI, isa.F_B, rng.randrange(256)), isa.encode(isa.ST, 0, k)]
    while len(rom) < 256:
        op = rng.randrange(16)
        if op == isa.JP:
            fn = rng.randrange(16) if rng.random() < 0.05 else rng.randrange(8)
        else:
            fn = rng.randrange(16)
        rom.append(isa.encode(op, fn, rng.randrange(256)))
    return rom


class TestStructuralMatchesMachine(unittest.TestCase):
    def test_random_programs(self):
        rng = random.Random(7400)
        ops = set()
        for trial in range(150):
            rom = random_program(rng)
            inp = [rng.randrange(256) for _ in range(16)]
            m, s = Machine(rom, inp), Structural(rom, inp)
            for _ in range(500):
                if m.halted:
                    break
                ops.add(isa.decode(rom[m.pc])[0])
                m.step()
                s.cycle()
                ram_s = (s.ram_lo.mem, s.ram_hi.mem)       # 未書き込みの番地は None のまま比べる
                ram_m = (m.ram_lo.mem, m.ram_hi.mem)
                self.assertEqual((m.pc, m.a, m.c, m.z, m.out, ram_m),
                                 (s.pc, s.a, s.c, s.z, s.out, ram_s), f"試行 {trial} / {m.cycles} 命令目")
        self.assertEqual(ops, set(range(16)), "全 OP を実行していない")


class TestJpCondition(unittest.TestCase):
    """JP の FN（D32）: 8〜F は停止、5〜7 は予約で分岐しない。"""

    def test_jp_reserved_and_halt(self):
        for fn in range(16):
            rom = [isa.encode(isa.JP, fn, 0x10)]
            m = Machine(rom)
            m.step()
            if fn & isa.HALT_BIT:
                self.assertTrue(m.halted, fn)
            elif fn in isa.COND_RESERVED:
                self.assertEqual((m.halted, m.pc), (False, 1), fn)


if __name__ == "__main__":
    unittest.main()
