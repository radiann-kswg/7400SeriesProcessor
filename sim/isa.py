"""命令セット草案 v0.1 の符号化定義（docs/ARCHITECTURE.md と対応）。

命令語は 16bit: [15:12] OP / [11:8] FN / [7:0] OPERAND。
FN は ALU 系命令では 74x181 の S3..S0 にそのまま渡る（アクティブ High データの機能コード）。
"""
from __future__ import annotations

# OP コード
LOGI, LOGM = 0x0, 0x1      # A <- 論理(FN; A, src)            Z
ARNI, ARNM = 0x2, 0x3      # A <- 算術(FN; A, src)            C Z   桁上げ入力なし
ARPI, ARPM = 0x4, 0x5      # A <- 算術(FN; A, src) + 1        C Z   桁上げ入力あり
ARCI, ARCM = 0x6, 0x7      # A <- 算術(FN; A, src) + C        C Z   桁上げ入力 = C フラグ
TSTI, TSTM = 0x8, 0x9      # 算術(FN; A, src) + 1 のフラグだけ更新（A は不変）
MULI, MULM = 0xA, 0xB      # A <- A[3:0] × src[3:0]           Z
ST = 0xC                   # RAM[OPERAND[3:0]] <- A
OUT = 0xD                  # OUT[FN] <- A
IN = 0xE                   # A <- IN[FN]                      Z
JP = 0xF                   # FN = 条件、OPERAND = 飛び先

# 74x181 機能コード（アクティブ High データ）
F_NOT_A, F_ZERO, F_XOR, F_B, F_AND, F_ONES, F_OR, F_A = 0x0, 0x3, 0x6, 0xA, 0xB, 0xC, 0xE, 0xF
F_A_ARITH, F_A_MINUS_B, F_A_PLUS_B, F_A_PLUS_A, F_A_MINUS_1 = 0x0, 0x6, 0x9, 0xC, 0xF

# 分岐条件（JP の FN）。5〜7 は予約（分岐しない）、FN の最上位（IR11）が 1 の 8〜F は停止（D32）
COND_ALWAYS, COND_Z, COND_NZ, COND_C, COND_NC, COND_HALT = 0x0, 0x1, 0x2, 0x3, 0x4, 0xF
COND_RESERVED = (0x5, 0x6, 0x7)
HALT_BIT = 0x8

# 「即値 / メモリ」の対を持つ別名: 名前 -> (即値側 OP, FN)。メモリ側は OP + 1
PAIRED = {
    "LD": (LOGI, F_B),
    "AND": (LOGI, F_AND),
    "OR": (LOGI, F_OR),
    "XOR": (LOGI, F_XOR),
    "ADD": (ARNI, F_A_PLUS_B),
    "SUB": (ARPI, F_A_MINUS_B),
    "ADC": (ARCI, F_A_PLUS_B),
    "SBC": (ARCI, F_A_MINUS_B),
    "CMP": (TSTI, F_A_MINUS_B),
    "MUL": (MULI, 0x0),
}

# オペランドを取らない別名: 名前 -> (OP, FN, OPERAND)
IMPLIED = {
    "NOT": (LOGI, F_NOT_A, 0),
    "CLR": (LOGI, F_ZERO, 0),
    "NOP": (LOGI, F_A, 0),
    "INC": (ARPI, F_A_ARITH, 0),
    "DEC": (ARNI, F_A_MINUS_1, 0),
    "SHL": (ARNI, F_A_PLUS_A, 0),
    "HLT": (JP, COND_HALT, 0),
}

# FN を明示する生の形式: 名前 -> OP（書式: NAME fn, operand）
RAW = {
    "LOGI": LOGI, "LOGM": LOGM, "ARNI": ARNI, "ARNM": ARNM, "ARPI": ARPI,
    "ARPM": ARPM, "ARCI": ARCI, "ARCM": ARCM, "TSTI": TSTI, "TSTM": TSTM,
}

JUMPS = {"JMP": COND_ALWAYS, "JZ": COND_Z, "JNZ": COND_NZ, "JC": COND_C, "JNC": COND_NC}


def encode(op: int, fn: int, operand: int) -> int:
    return ((op & 0xF) << 12) | ((fn & 0xF) << 8) | (operand & 0xFF)


def decode(word: int) -> tuple[int, int, int]:
    return (word >> 12) & 0xF, (word >> 8) & 0xF, word & 0xFF
