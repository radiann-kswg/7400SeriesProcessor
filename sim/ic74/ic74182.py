"""74x182: 桁上げ先見発生器（動作モデル）。"""
from __future__ import annotations

from typing import NamedTuple, Sequence

VERIFIED = True  # 照合済み（2026-11-22）: 論理式（SDLS206 1 頁）


class Out182(NamedTuple):
    cnx: int   # Cn+x
    cny: int   # Cn+y
    cnz: int   # Cn+z
    p: int     # グループ P
    g: int     # グループ G


def ic74182(cn: int, p: Sequence[int], g: Sequence[int]) -> Out182:
    """ピンレベルで 74x182 を評価する。p[i], g[i] は P_i / G_i ピン（i=0..3）。

    74x181 の P / G / Cn ピンをそのまま接続する前提（負論理の P・G）。
    未使用の段は p=1, g=1 とする。
    """
    n = lambda v: 0 if v else 1  # noqa: E731
    p0, p1, p2, p3 = (1 if v else 0 for v in p)
    g0, g1, g2, g3 = (1 if v else 0 for v in g)
    c = 1 if cn else 0
    cnx = n(g0) | (n(p0) & c)
    cny = n(g1) | (n(p1) & n(g0)) | (n(p1) & n(p0) & c)
    cnz = (n(g2) | (n(p2) & n(g1)) | (n(p2) & n(p1) & n(g0))
           | (n(p2) & n(p1) & n(p0) & c))
    gp = p3 | p2 | p1 | p0
    gg = g3 & (p3 | g2) & (p3 | p2 | g1) & (p3 | p2 | p1 | g0)
    return Out182(cnx, cny, cnz, gp, gg)
