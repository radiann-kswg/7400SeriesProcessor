; 74x284/285 で 13 × 11 を計算し、引き算の繰り返しで BCD 3 桁に直して
; ニキシー表示ポート（OUT 0 = 十の位:一の位、OUT 1 = 百の位）へ出力する。
.equ VALUE 0
.equ HUNDREDS 1
.equ TENS 2

        LDI 13
        MULI 11             ; A = 143（A の下位 4bit × 即値の下位 4bit）
        ST VALUE
        CLR
        ST HUNDREDS
        ST TENS
h_loop: LD VALUE
        CMPI 100
        JNC h_done          ; A < 100
        SUBI 100
        ST VALUE
        LD HUNDREDS
        INC
        ST HUNDREDS
        JMP h_loop
h_done: LD VALUE
t_loop: CMPI 10
        JNC t_done          ; A < 10
        SUBI 10
        ST VALUE
        LD TENS
        INC
        ST TENS
        LD VALUE
        JMP t_loop
t_done: LD TENS
        SHL
        SHL
        SHL
        SHL
        OR VALUE            ; 上位ニブル = 十の位、下位ニブル = 一の位
        OUT 0
        LD HUNDREDS
        OUT 1
        HLT
