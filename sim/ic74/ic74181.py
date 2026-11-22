"""74x181: 4bit ALU / function generator（動作モデル）。"""
from __future__ import annotations

from typing import NamedTuple

VERIFIED = False  # 一次資料との照合前


class Out181(NamedTuple):
    f: int        # F3..F0 のピンレベル
    cn4: int      # Cn+4 ピン
    p: int        # P（アクティブ High データ表記では X）ピン
    g: int        # G（同 Y）ピン
    aeqb: int     # A=B ピン（オープンコレクタ。F がすべて H のとき H）


def ic74181(a: int, b: int, s: int, m: int, cn: int) -> Out181:
    """ピンレベルで 74x181 を評価する。

    a, b : A3..A0 / B3..B0 のピンレベル (0..15)
    s    : S3..S0 (0..15)
    m    : M ピン (1 = 論理演算、0 = 算術演算)
    cn   : Cn ピン

    アクティブ High データとして使う場合、桁上げは負論理になる
    （cn=0 で桁上げ入力あり、cn4=0 で桁上げ出力あり）。
    """
    a &= 0xF
    b &= 0xF
    nb = ~b & 0xF
    s0, s1, s2, s3 = (s >> 0) & 1, (s >> 1) & 1, (s >> 2) & 1, (s >> 3) & 1
    # ビットごとの中間項（常に gen ⊆ prop）
    prop = a | (b if s0 else 0) | (nb if s1 else 0)
    gen = a & ((b if s3 else 0) | (nb if s2 else 0))
    cin = 0 if cn else 1

    if m:
        f = ~(prop ^ gen) & 0xF
    else:
        f = (prop + gen + cin) & 0xF

    pb = [(prop >> i) & 1 for i in range(4)]
    gb = [(gen >> i) & 1 for i in range(4)]
    group_g = (gb[3] | (pb[3] & gb[2]) | (pb[3] & pb[2] & gb[1])
               | (pb[3] & pb[2] & pb[1] & gb[0]))
    group_p = pb[3] & pb[2] & pb[1] & pb[0]
    carry = group_g | (group_p & cin)

    return Out181(
        f=f,
        cn4=0 if carry else 1,
        p=1 if gen else 0,                    # いずれかのビットで gen が立つと H
        g=1 if (group_g | group_p) else 0,    # cin=1 を仮定したときの桁上げ
        aeqb=1 if f == 0xF else 0,
    )
