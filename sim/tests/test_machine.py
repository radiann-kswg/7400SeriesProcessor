import unittest
from pathlib import Path

from sim.asm import AsmError, assemble
from sim.machine import Machine

PROGRAMS = Path(__file__).resolve().parents[1] / "programs"


def run(source: str, **kw) -> Machine:
    m = Machine(assemble(source), **kw)
    m.run()
    return m


class TestAlu8(unittest.TestCase):
    def test_add_sub_exhaustive(self):
        for a in range(256):
            for b in range(256):
                for cin in (0, 1):
                    f, c = Machine.alu(a, b, 0x9, 0, cin)
                    self.assertEqual((f, c), ((a + b + cin) & 0xFF, (a + b + cin) >> 8))
                    f, c = Machine.alu(a, b, 0x6, 0, cin)
                    t = a + (~b & 0xFF) + cin
                    self.assertEqual((f, c), (t & 0xFF, t >> 8))

    def test_logic(self):
        for a in (0x00, 0x5A, 0xA5, 0xFF, 0x3C):
            for b in (0x00, 0x0F, 0xF0, 0xFF, 0x66):
                self.assertEqual(Machine.alu(a, b, 0xB, 1, 0)[0], a & b)
                self.assertEqual(Machine.alu(a, b, 0xE, 1, 0)[0], a | b)
                self.assertEqual(Machine.alu(a, b, 0x6, 1, 0)[0], a ^ b)
                self.assertEqual(Machine.alu(a, b, 0xA, 1, 0)[0], b)
                self.assertEqual(Machine.alu(a, b, 0x0, 1, 0)[0], ~a & 0xFF)


class TestPrograms(unittest.TestCase):
    def test_basic_ops(self):
        m = run("LDI 200\nADDI 100\nST 0\nLDI 0\nADCI 0\nST 1\nLD 0\nHLT")
        self.assertEqual((m.a, m.ram_read(1)), (44, 1))
        m = run("LDI 5\nCMPI 5\nJZ eq\nLDI 0\nHLT\neq: LDI 1\nHLT")
        self.assertEqual(m.a, 1)
        m = run("LDI 3\nloop: DEC\nJNZ loop\nHLT")
        self.assertEqual((m.a, m.z), (0, 1))
        m = run("IN 2\nSHL\nOUT 3\nHLT", in_ports=[0, 0, 0x21] + [0] * 13)
        self.assertEqual(m.out[3], 0x42)

    def test_mul_nixie_demo(self):
        m = run((PROGRAMS / "mul_nixie.asm").read_text(encoding="utf-8"))
        self.assertEqual(m.nixie_text(), "00000143")

    def test_bcd_conversion_all_products(self):
        src = (PROGRAMS / "mul_nixie.asm").read_text(encoding="utf-8")
        for x in range(16):
            for y in range(16):
                m = run(src.replace("LDI 13", f"LDI {x}").replace("MULI 11", f"MULI {y}"))
                self.assertEqual(m.nixie_text(), f"{x * y:08d}", (x, y))

    def test_errors(self):
        with self.assertRaises(AsmError):
            assemble("FOO 1")
        with self.assertRaises(AsmError):
            assemble("LD 16")
        with self.assertRaises(AsmError):
            assemble("JMP nowhere")


if __name__ == "__main__":
    unittest.main()
