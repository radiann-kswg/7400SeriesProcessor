import unittest

from sim.ic74 import Ic7489, ic74141, ic74181, ic74182, ic74284, ic74285

M4 = 0xF
N = lambda v: ~v & M4  # noqa: E731

# 74x181 機能表（アクティブ High データ）。動作モデルとは別に、表として書き下したもの。
LOGIC = [
    lambda a, b: N(a), lambda a, b: N(a | b), lambda a, b: N(a) & b, lambda a, b: 0,
    lambda a, b: N(a & b), lambda a, b: N(b), lambda a, b: a ^ b, lambda a, b: a & N(b),
    lambda a, b: N(a) | b, lambda a, b: N(a ^ b), lambda a, b: b, lambda a, b: a & b,
    lambda a, b: M4, lambda a, b: a | N(b), lambda a, b: a | b, lambda a, b: a,
]
ARITH = [  # 桁上げ入力なしのときの値（mod 16 前）
    lambda a, b: a, lambda a, b: a | b, lambda a, b: a | N(b), lambda a, b: -1,
    lambda a, b: a + (a & N(b)), lambda a, b: (a | b) + (a & N(b)),
    lambda a, b: a - b - 1, lambda a, b: (a & N(b)) - 1,
    lambda a, b: a + (a & b), lambda a, b: a + b,
    lambda a, b: (a | N(b)) + (a & b), lambda a, b: (a & b) - 1,
    lambda a, b: a + a, lambda a, b: (a | b) + a, lambda a, b: (a | N(b)) + a,
    lambda a, b: a - 1,
]


class Test74181(unittest.TestCase):
    def test_logic_table(self):
        for s in range(16):
            for a in range(16):
                for b in range(16):
                    for cn in (0, 1):
                        self.assertEqual(ic74181(a, b, s, 1, cn).f, LOGIC[s](a, b) & M4, (s, a, b))

    def test_arith_table(self):
        for s in range(16):
            for a in range(16):
                for b in range(16):
                    for cin in (0, 1):
                        out = ic74181(a, b, s, 0, 0 if cin else 1)
                        self.assertEqual(out.f, (ARITH[s](a, b) + cin) & M4, (s, a, b, cin))

    def test_add_sub_carry(self):
        for a in range(16):
            for b in range(16):
                for cin in (0, 1):
                    add = ic74181(a, b, 0x9, 0, 0 if cin else 1)
                    self.assertEqual(add.cn4, 0 if a + b + cin > 15 else 1)
                    sub = ic74181(a, b, 0x6, 0, 0 if cin else 1)
                    self.assertEqual(sub.cn4, 0 if a + (~b & M4) + cin > 15 else 1)

    def test_lookahead_matches_ripple(self):
        """P・G を 74x182 に通した桁上げが、181 自身の Cn+4 と一致する。"""
        for s in range(16):
            for a in range(16):
                for b in range(16):
                    for cn in (0, 1):
                        out = ic74181(a, b, s, 0, cn)
                        cla = ic74182(cn, (out.p, 1, 1, 1), (out.g, 1, 1, 1))
                        self.assertEqual(cla.cnx, out.cn4, (s, a, b, cn))

    def test_magnitude_table(self):
        """減算モード（S=LHHL）での Cn / Cn+4 と大小関係の表（アクティブ High データ）。"""
        for a in range(16):
            for b in range(16):
                self.assertEqual(ic74181(a, b, 0x6, 0, 1).cn4, 1 if a <= b else 0)   # Cn=H
                self.assertEqual(ic74181(a, b, 0x6, 0, 0).cn4, 1 if a < b else 0)    # Cn=L

    def test_a_equals_b(self):
        for a in range(16):
            for b in range(16):
                self.assertEqual(ic74181(a, b, 0x6, 0, 1).aeqb, int(a == b))


class Test74182(unittest.TestCase):
    def test_four_stage_chain(self):
        """4 段の P・G から得た桁上げが、段ごとに順送りした結果と一致する。"""
        for bits in range(1 << 9):
            cn = bits & 1
            p = [(bits >> (1 + i)) & 1 for i in range(4)]
            g = [(bits >> (5 + i)) & 1 for i in range(4)]
            c = cn
            ripple = []
            for i in range(4):
                c = (0 if g[i] else 1) | ((0 if p[i] else 1) & c)
                ripple.append(c)
            out = ic74182(cn, p, g)
            self.assertEqual([out.cnx, out.cny, out.cnz], ripple[:3], bits)


class TestOthers(unittest.TestCase):
    def test_multiplier(self):
        for a in range(16):
            for b in range(16):
                self.assertEqual(ic74285(a, b) | (ic74284(a, b) << 4), a * b)
        self.assertEqual(ic74284(15, 15, ga=1), 0xF)
        self.assertEqual(ic74285(15, 15, gb=1), 0xF)

    def test_ram(self):
        ram = Ic7489()
        for addr in range(16):
            self.assertEqual(ram.eval(addr, addr ^ 0x5, me=0, we=0), ~(addr ^ 0x5) & M4)
        for addr in range(16):
            self.assertEqual(ram.eval(addr, 0, me=0, we=1), ~(addr ^ 0x5) & M4)
        self.assertEqual(ram.eval(3, 0x0, me=1, we=1), 0xF)
        ram.eval(3, 0x0, me=1, we=0)                      # 書き込み禁止
        self.assertEqual(ram.eval(3, 0, me=0, we=1), ~(3 ^ 0x5) & M4)
        with self.assertRaises(ValueError):
            Ic7489().eval(0, 0, me=0, we=1)

    def test_nixie_driver(self):
        self.assertEqual([ic74141(v) for v in range(10)], list(range(10)))
        self.assertTrue(all(ic74141(v) is None for v in range(10, 16)))


if __name__ == "__main__":
    unittest.main()
