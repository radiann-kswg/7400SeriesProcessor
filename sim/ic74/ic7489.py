"""74x89: 64bit RAM（16 語 × 4bit、反転出力・オープンコレクタ）の動作モデル。"""
from __future__ import annotations

VERIFIED = True  # 照合済み（2026-11-22）: 機能表（D1416 5-3 頁）


class Ic7489:
    """ME（メモリイネーブル）と WE（ライトイネーブル）はどちらも L アクティブ。

    出力は記憶内容の反転。オープンコレクタなので、出力 H は「引いていない」状態を表す
    （実回路ではプルアップ抵抗が必要）。電源投入直後の内容は不定のため、
    モデルでは未書き込み語の読み出しを例外にする（strict=True のとき）。
    """

    def __init__(self, strict: bool = True) -> None:
        self.mem: list[int | None] = [None] * 16
        self.strict = strict

    def eval(self, addr: int, d: int, me: int, we: int) -> int:
        """1 回の評価。戻り値は出力ピン 4 本のレベル (0..15)。"""
        addr &= 0xF
        d &= 0xF
        if me == 0 and we == 0:          # 書き込み。出力はデータ入力の反転
            self.mem[addr] = d
            return ~d & 0xF
        if me == 0 and we == 1:          # 読み出し。記憶内容の反転
            v = self.mem[addr]
            if v is None:
                if self.strict:
                    raise ValueError(f"未書き込みの番地 {addr} を読み出した")
                v = 0
            return ~v & 0xF
        if me == 1 and we == 0:          # 書き込み禁止。出力はデータ入力の反転
            return ~d & 0xF
        return 0xF                       # 非選択。出力はすべて H（オフ）
