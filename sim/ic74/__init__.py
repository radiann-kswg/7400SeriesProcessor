"""IC 単位の動作モデル。

すべて「ピンの電圧レベル（H=1 / L=0）」を入出力とする。データの正論理／負論理の
解釈は呼び出し側（sim.machine）で行う。

注意: ここにあるモデルは機能表の一般知識から組んだもので、Phase 0 時点では
一次資料（データシート）との照合前である。照合結果は docs/REQUIREMENTS.md の
リスク R1 と hw/pinspec/ で管理し、照合後に各モジュールの VERIFIED を更新する。
"""
from .ic74181 import ic74181, Out181
from .ic74182 import ic74182, Out182
from .ic7489 import Ic7489
from .ic74284_285 import ic74284, ic74285
from .ic74141 import ic74141

__all__ = ["ic74181", "Out181", "ic74182", "Out182", "Ic7489",
           "ic74284", "ic74285", "ic74141"]
