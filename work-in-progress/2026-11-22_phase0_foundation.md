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

## 追記: 方針の確定（同日）

- 質疑の続きで D12〜D25 を確定し、方針レベルの未決事項が無くなった（`docs/REQUIREMENTS.md` v0.2）。名称は 7400sCCP8。
- 表示は既存の自作ドライバ基板 ND712Mk00 の構造（74x141 互換 1 個 + フォトカプラ陽極切り替えのダイナミック点灯）を流用。ネットリストと写真・動画で 7 桁 + 小数点の点灯実績を確認。
- プログラム入力は TTM8 にならい 16 進キーパッド + SRAM。TTM8 のプログラムボードはマイコンを使うが、本機のローダは 74 シリーズだけで組む。
- `hw/slots.json` を 42 役割に更新（表示走査・表示バッファ・ローダの役割を追加、ROM を PMEM に改称）。`sim/` のニキシー表示を 8 桁に変更。テスト 15 件通過。
- 上記を 93ff1f4 として push 済み。
- D26 を追加: NIXIE の役割カードは K155ID1 と 74x141 を換装可能にする。リスク R9（一次資料未入手）を追加。
- データシート収集の dry-run（Collection の `fetch_missing_datasheets.py --dry-run --part`）: 74x89 / 74x284 / 74x285 は取得計画あり（登録済み URL に公式ドメイン以外が含まれるため、取得元はユーザー確認待ち）。74x141 は取得計画なし。`--report` に相対パスを渡すと最後の表示で例外になる（Collection 側の不具合）。

## 追記: 希少 IC の一次資料照合（同日）

- Collection の `datasheets/_download/TI(TexasInstruments)/` にある TI の資料 4 点（SN7489 / SN74284・SN74285 / SN74S181 / SN74S182）を画像化して目視し、`hw/pinspec/` に 74x89 / 74x284 / 74x285 / 74x181 / 74x182 の pinspec を作成。いずれもパッケージ図・論理記号・表の 3 か所でピン番号が一致し、読み取り信頼度 95%。
- `sim/ic74/` の 74x181（機能表 Table 2・大小比較の表）、74x182（論理式）、74x89（機能表）、74x284/285（積と重み）を照合し `VERIFIED = True` に変更。モデルの修正は不要だった。大小比較の表のテストを追加（計 16 件）。
- 未照合で残るもの: 74x181 の P・G 出力の個別論理（論理図）、74x284/285 のイネーブル無効時の出力（記号からの解釈）、74x141 一式。
- 電気特性の読み取り: 74x89 は出力耐圧 5.5 V・書き込みパルス幅 40 ns 以上・代表 375 mW。74x284/285 は出力耐圧 5.5 V・IOL 16 mA・ICC 代表 92 mA（最大 130 mA）・語入力からの遅延 代表 40 ns（最大 60 ns）。
- Collection 側の更新候補（未実施）: `datasheet_sources.json` の 74x89・74x284・74x285 の Notes が「PDF 未保存」のまま、収集状況 JSON が「収集予定」のまま、`usage/` のチートシートのチェック欄が未更新。
