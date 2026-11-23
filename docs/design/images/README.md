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

書き出し: 2026-11-23。`hw/system.json` v0.3（ブロック 53・信号 64・LED 85）に対応。`arch_phase.png`・`arch_leds.png`・`arch_boards.png` は D29 の改訂（位相 LED を Q1 = 赤・Q2 = 緑で点け、T2 黄・T3 緑。駆動は LED-PH）に合わせて同日に書き出し直した。
