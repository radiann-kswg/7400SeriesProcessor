"""74x141（K155ID1 互換）: BCD → 10 進デコーダ／ニキシー管ドライバの動作モデル。"""
from __future__ import annotations

VERIFIED = False  # 一次資料との照合前


def ic74141(bcd: int) -> int | None:
    """L に引かれる出力（点灯する数字 0..9）を返す。

    入力が 10..15 のときはどの出力も引かない（消灯）ものとして None を返す。
    """
    bcd &= 0xF
    return bcd if bcd <= 9 else None
