# 清書図

見やすさを優先して配置を人が決めた図。Claude Design のキャンバス「7400sCCP8 アーキテクチャ図」で作図し、PNG に書き出したもの。

- 正本ではない。内容の正本は `hw/system.json`（ブロック・信号・LED）と `docs/design/SYSTEM.md`（制御・位相・電気規格）。食い違ったら正本を正とし、図を直す。
- 自動生成の全体図（網羅的だが配置は自動）は [`../generated/README.md`](../generated/README.md)。
- 図を直すときは、キャンバスのアートボードを直してから書き出し直す。この PNG を画像編集で直さない。

| ファイル | 内容 | 主に対応する箇所 |
|---|---|---|
| `arch_datapath.png` | データの流れ（バスと IC） | `SYSTEM.md` 1 章、`hw/system.json` の data の信号 |
| `arch_control.png` | 制御の流れ（命令語のビット、制御信号、ストローブ） | `SYSTEM.md` 4 章 |
| `arch_phase.png` | クロック位相と位相表示 LED、74x89 の書き込みタイミング | `SYSTEM.md` 5 章 |
| `arch_boards.png` | 基板の構成（本体・ローダ基板・io 基板と接続口） | `SYSTEM.md` 7.1 節 |
| `arch_leds.png` | LED 表示の一覧 | `SYSTEM.md` 7.3 節、D39 |
| `arch_nixie.png` | ニキシー表示の概念図（表示バッファ・走査・陰極ドライバ・陽極の切り替え・高圧部） | `docs/ARCHITECTURE.md` 5 章、D17〜D19・D26・D35 |
| `arch_loader.png` | ローダ基板の中の流れ（キー走査・入力レジスタ・番地カウンタ・書き込みの許可と、本体の PM-M・PM-A・RUNSYNC） | `hw/system.json` のローダ基板の信号、`SYSTEM.md` のキーの行列走査、D40 |
| `arch_io.png` | io 基板の中の流れ（ポート選択・出力ポート 0・入力ポート 0 と、本体の PM-B・GLUE・RSEL・ACC・COND） | `hw/system.json` の io 基板の信号、D31・D41 |
| `alu8_context.png` | alu8 カードとつながるカード（信号と確定期限） | `hw/cards/alu8/DESIGN.md` 1 章・6 章、`hw/system.json` の signals |
| `alu8_carry.png` | alu8 の中の桁上げの流れ（U1 → U3 → U2、ピン番号つき） | `hw/cards/alu8/card.json`、`DESIGN.md` 2〜4 章 |
| `alu8_j1.png` | alu8 の接続口 J1（暫定）の並び | `hw/cards/alu8/card.json` の connector、`DESIGN.md` 3 章 |
| `mul_context.png` | mul カードとつながるカード、中の構成（U1・U2 に同じ 2 語、RN1 のプルアップ） | `hw/cards/mul/card.json`、`DESIGN.md` 1〜3 章・6 章 |
| `mul_j1.png` | mul の接続口 J1（暫定）の並び | `hw/cards/mul/card.json` の connector、`DESIGN.md` 3 章 |

書き出し: 2026-11-23。`hw/system.json` v0.3（ブロック 53・信号 64・LED 85）に対応。`arch_phase.png`・`arch_leds.png`・`arch_boards.png` は D29 の改訂（位相 LED を Q1 = 赤・Q2 = 緑で点け、T2 黄・T3 緑。駆動は LED-PH）に合わせて同日に書き出し直した。`alu8_*.png` の 3 枚は同日、`hw/cards/alu8/card.json`（a6a88ae 時点）から作図した。

`mul_*.png` の 2 枚は 2026-11-25 に `hw/cards/mul/card.json` から作図し、書き出した（キャンバスの MulContext・MulJ1）。

`arch_nixie.png` は 2026-11-25 に `docs/ARCHITECTURE.md` 5 章の概念図（Mermaid）と D17〜D19・D26・D35 から作図し、書き出した（キャンバスの Nixie）。設計資料 PDF では、この Mermaid の図をこの図に差し替えて載せる。

`arch_loader.png`・`arch_io.png` は 2026-11-25 に `hw/system.json`（v0.3）の信号から作図し、書き出した（キャンバスの Loader・Io）。生成物の全体図（`../generated/fig_loader.svg`・`fig_io.svg`）と同じ内容を、配置を人が決めて描き直したもの。
