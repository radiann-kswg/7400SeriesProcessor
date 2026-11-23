"""カード生成器の参照名・直流駆動経路検査。"""
import unittest
from unittest.mock import patch

from scripts.gen_card import CardError, check_card


class TestCardValidation(unittest.TestCase):
    def test_connector_ref_must_be_unique(self):
        data = {"components": [{"ref": "J1"}], "connector": {"ref": "J1", "signals": []}}
        with self.assertRaisesRegex(CardError, "参照名が重複"):
            check_card(data)

    def check_input_path(self, second_terminal, *, kind="R", connector=None, extra_resistor=False):
        components = [
            {"ref": "U1", "part": "TEST", "pins": {"1": "FLOAT", "2": "OUT"}},
            {"ref": "X1", "kind": kind, "pins": {"1": "FLOAT", "2": second_terminal}},
        ]
        if second_terminal == "NC":
            components[1]["nc"] = {"2": "intentionally unconnected"}
        if extra_resistor:
            components.append({
                "ref": "X2", "kind": "R", "pins": {"1": "NC", "2": "VCC"},
                "nc": {"1": "intentionally unconnected"},
            })
        data = {
            "components": components,
            "nets": {"FLOAT": "入力", "OUT": "出力"},
        }
        if connector:
            data["connector"] = connector
        pinspec = {"pins": {
            "1": {"name": "IN", "dir": "input"},
            "2": {"name": "OUT", "dir": "output"},
        }}
        with patch("scripts.gen_card.load_pinspec", return_value=(pinspec, None)):
            return check_card(data)[2]

    def test_capacitor_does_not_provide_dc_drive(self):
        warnings = self.check_input_path("VCC", kind="C")
        self.assertTrue(any("FLOAT に駆動元が無い（直流経路なし）" in w for w in warnings))

    def test_resistor_to_supply_provides_dc_drive(self):
        warnings = self.check_input_path("VCC")
        self.assertFalse(any("FLOAT に駆動元が無い" in w for w in warnings))

    def test_resistor_to_output_provides_dc_drive(self):
        warnings = self.check_input_path("OUT")
        self.assertFalse(any("FLOAT に駆動元が無い" in w for w in warnings))

    def test_resistor_to_connector_provides_dc_drive(self):
        warnings = self.check_input_path("EXT", connector={"ref": "J1", "signals": ["EXT"]})
        self.assertFalse(any("FLOAT に駆動元が無い" in w for w in warnings))

    def test_unconnected_resistor_terminal_does_not_create_dc_path(self):
        warnings = self.check_input_path("NC", extra_resistor=True)
        self.assertTrue(any("FLOAT に駆動元が無い（直流経路なし）" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
