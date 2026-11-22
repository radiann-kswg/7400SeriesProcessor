# 2026-11-22 Phase 0: 設計基盤の作成

## 経緯

- 依頼: TD4 / TTM8 のような自作 CPU を、74x89 / 74x141 / 74x181 / 74x182 / 74x284 / 74x285 とニキシー管を構成部品にした「動作するコレクション」として設計する。Collection と Structures をサブモジュールに持つ新規リポジトリで進める。
- 追加要件: 手持ちの IC を可能な限り多種類使い、新しい型番が入り次第構成を変更できるようにする。配線と回路を確認できるよう回路図を生成する工程を持つ。
- 質問と回答で D1〜D11 を確定（`docs/REQUIREMENTS.md`）。

## 作ったもの

- リポジトリ骨格（README / AGENTS.md / CLAUDE.md / LICENSE / サブモジュール 2 つ）。
- `docs/REQUIREMENTS.md`、`docs/ARCHITECTURE.md`（命令セット草案 v0.1）。
- `hw/slots.json`（役割 36 個）、`hw/builds/default.json`、実証カード `hw/cards/reg8_574/`。
- `scripts/gen_card.py`（配線表・KiCad 回路図・SVG の生成と検査）、`scripts/role_coverage.py`（ローカル専用）。
- `sim/`（IC 動作モデル 6 種、エミュレータ、アセンブラ、デモプログラム、テスト 15 件）。

## 確認したこと

- `python -m unittest discover -s sim/tests -t .` が 15 件すべて通過（VM の Python 3.10）。
- `python -m sim.run sim/programs/mul_nixie.asm` が `NIXIE: 0143` を出力（13 × 11）。
- `python scripts/gen_card.py --all --svg --erc`（Windows・KiCad 10.0.3）で `reg8_574` を生成。ERC は `lib_symbol_issues`（埋め込みシンボルの通知）以外 0 件。PDF に書き出して目視し、ピン番号・名称・ラベルが pinspec と一致することを確認。

## 未了・次にやること

- 未決事項 O1〜O7 の確定。
- 希少 6 型番のデータシート収集と pinspec 作成（R1）。それまで該当カードは作らない。
- `sim/ic74/` の各モデルは一次資料との照合前（`VERIFIED = False`）。
- Collection のマスターデータで、機能説明が空か、実際の IC と合っていない疑いのある型番がある（74x54 / 74x274 / 74x276 / 74x804 / 74x841 / 74x845 など）。`hw/slots.json` の候補には入れていない。Collection 側で要確認。
