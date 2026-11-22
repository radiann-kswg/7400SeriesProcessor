"""74x284 / 74x285: 4bit × 4bit 並列乗算器（上位 4bit / 下位 4bit）の動作モデル。

2 個 1 組で 8bit の積を得る。出力はオープンコレクタで、イネーブル入力（L アクティブ 2 本）が
どちらも L のときだけ有効。無効時は出力 H（オフ）とする。
"""
from __future__ import annotations

VERIFIED = False  # 一次資料との照合前


def _product(a: int, b: int) -> int:
    return (a & 0xF) * (b & 0xF)


def ic74284(a: int, b: int, ga: int = 0, gb: int = 0) -> int:
    """積の上位 4bit（Y7..Y4）を返す。"""
    if ga or gb:
        return 0xF
    return (_product(a, b) >> 4) & 0xF


def ic74285(a: int, b: int, ga: int = 0, gb: int = 0) -> int:
    """積の下位 4bit（Y3..Y0）を返す。"""
    if ga or gb:
        return 0xF
    return _product(a, b) & 0xF
