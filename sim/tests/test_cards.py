"""カード定義の配線どおりに組んだモデルを、命令レベルエミュレータ（sim/machine.py）と突き合わせる。"""
import random
import unittest

from sim.machine import Machine
from sim.netlist import Card


def bits(prefix: str, value: int, n: int, start: int = 0) -> dict:
    return {f"{prefix}{start + i}": (value >> i) & 1 for i in range(n)}


class TestAlu8Card(unittest.TestCase):
    def test_matches_machine_alu(self):
        card = Card("alu8")
        rnd = random.Random(7400)
        pairs = [(0, 0), (0xFF, 0xFF), (0, 0xFF), (0xFF, 0), (0x0F, 0x01), (0xF0, 0x10), (0x7F, 0x01), (0x80, 0x80)]
        pairs += [(rnd.randrange(256), rnd.randrange(256)) for _ in range(100)]
        for s in range(16):
            for m in (0, 1):
                for cn_n in (0, 1):
                    for a, b in pairs:
                        v = card.eval({**bits("A", a, 8), **bits("B", b, 8), **bits("IR", s, 4, 8),
                                       "M": m, "CN_n": cn_n})
                        f = sum(v[f"F{i}"] << i for i in range(8))
                        want_f, want_c = Machine.alu(a, b, s, m, 1 - cn_n)
                        self.assertEqual((f, v["COUT_n"]), (want_f, 1 - want_c), (a, b, s, m, cn_n))


if __name__ == "__main__":
    unittest.main()
