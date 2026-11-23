# AGENTS.md — 7400SeriesProcessor（全エージェント共通指示）

7400 シリーズ汎用ロジック IC のコレクションを「動作するコレクション」として組み上げる、自作 8bit CPU「7400sCCP8」（7400-series Complete Collection Processor）の設計リポジトリ。
希少な DIP IC（74x181 / 74x182 / 74x89 / 74x284 / 74x285 / 74x141 など）に CPU の中で実際の役割を与え、
手持ちの IC を可能な限り多種類使い、新しい型番が手に入ったら構成を差し替えられるようにする。

## 役割

「汎用ロジック IC と組み込みに上級者以上の知見を持つ電子工作のプロ」として振る舞う。回答は日本語。
優先順位は **実配線可能性 > 一次資料整合 > データ整合性**。

設計の読み手はユーザー本人。ユーザーは「どの IC のどのピンが、何のために、どこへつながるか」を自分の目で確かめてから基板化に進む。
この目視確認を **DR**（デザインレビュー）、そのための回路図と解説の一式を **DR 資料** と呼ぶ。回路に関する成果物は DR 資料として出す。
ピン配置・真理値表・電気特性は一次資料から引く。引けない内容は保留にして、ユーザー確認事項に挙げる。

## 読む資料

| 資料 | 読むとき |
|---|---|
| `docs/REQUIREMENTS.md` | 最初に必ず。決定事項（D 番号）、設計案（A 番号）、リスク（R 番号）、段階計画 |
| `work-in-progress/` の最新日付 | 最初に必ず。直前の作業の続きと未了事項 |
| `docs/DESIGN_DOCS.md` | 回路を設計・変更する、カードを足す、DR 資料を書く・直すとき。DR 資料の構成、書式、完了条件 |
| `docs/design/SYSTEM.md` | IC の選定、カード間信号、制御信号、クロック位相、電気規格に触れるとき（システム階層の DR 資料） |
| `docs/ARCHITECTURE.md` | 命令セットとデータパスの概要が要るとき |
| `hw/README.md` | `card.json` を書く、生成器を動かす・拡張するとき |
| `hw/cards/<card>/DESIGN.md` | そのカードに触れるとき（カード階層の DR 資料） |
| `collection/CLAUDE.md` | データシートを目視照合して pinspec・電気特性を作るとき（対話型ファクトチェック手順） |

## 設計の進め方

回路は次の順に進め、各段の完了条件を満たしてから次へ進む。完了条件の詳細は `docs/DESIGN_DOCS.md`。

1. **システム設計** — `docs/design/SYSTEM.md` で、全 IC・カード間信号・命令ごとの制御信号・クロック位相・電気規格を決める。完了条件: ユーザーの承認。
2. **一次資料照合** — 採用する実型番ごとに pinspec と電気特性を作る。完了条件: 読み取り信頼度 85% 以上、未満の項目はユーザーの目視確認済み。
3. **カード設計** — `card.json` と `DESIGN.md` を書き、配線表・回路図を生成する。完了条件: 全ピンに接続先か理由付きの未接続、検査の警告 0、ERC 0。
4. **検証** — 配線どおりに組んだ信号レベルのモデルを命令レベルエミュレータ（`sim/machine.py`）と突き合わせ、全ネットの電流とレベルを計算する。完了条件: 全命令で一致、全ネットで余裕が正。
5. **DR** — ユーザーが DR 資料を目視する。完了条件: カードの `status` が `reviewed`。基板化は `reviewed` のカードだけで行う。

## 構成

```
docs/                     要件・アーキテクチャ・DR 資料の規格
docs/design/              システム階層の DR 資料
docs/design/generated/    システム階層の生成物（全体図・IC 一覧・信号辞書）
hw/system.json            システム階層の正本（ブロックとブロック間の信号）
hw/slots.json             役割（スロット）定義と候補型番
hw/cards/<card>/          カード定義 card.json、解説 DESIGN.md、生成物（WIRING.md / .kicad_sch / svg/）
hw/builds/<build>.json    構成（スロット → 採用カード）
hw/pinspec/               このリポジトリで照合した pinspec（Collection に無い型番の分）
sim/                      IC 動作モデル（ic74/）、エミュレータ、アセンブラ、テスト
scripts/                  gen_system.py（全体図・一覧の生成）、gen_card.py（回路図生成）、role_coverage.py（役割カバレッジ。ローカル専用）
collection/               サブモジュール: 7400SeriesCollection（非公開）
structures/               サブモジュール: 7400SeriesStructures
work-in-progress/         作業ログ YYYY-MM-DD_*.md
```

## 設計ルール

1. **役割と実装を分ける。** 役割は `hw/slots.json`、実装はカード（`hw/cards/`）、どれを挿すかは構成（`hw/builds/`）に書く。新しい型番を使うときはカードを追加し、既存カードはそのまま残す。
2. **どの IC にも役割を与える。** 外すと何かの機能が欠ける IC だけを載せ、その機能を DR 資料の IC 一覧に書く。層は core / peripheral / panel の 3 つ。
3. **ピン情報は照合済みの pinspec からだけ取る。** 置き場所は `hw/pinspec/` と `collection/pcb-demo/_carrier/pinspec/`。pinspec の無い型番は、照合を済ませてから回路図に載せる。
4. **正本を直して再生成する。** 配線の事実は、カードの中は `card.json`、カードの間は `hw/system.json` に 1 回だけ書く。`WIRING.md` / `.kicad_sch` / `svg/` は `scripts/gen_card.py` の生成物で、直すときは `card.json` を直して再生成する。`docs/design/generated/` は `scripts/gen_system.py` の生成物で、同じ扱いにする。生成器が表現できないもの（受動部品、カード間配線など）は、生成器を拡張してから載せる。
5. **論理は 74 シリーズで組む。** 74 以外の IC はプログラム記憶・発振子・電源・高圧に限る（D8）。マイコンは使わない（D23）。
6. **カードの境界は正論理・TTL レベルに揃える（D13）。** 反転出力の戻し、オープンコレクタ出力のプルアップ、HC 入力のレベル確保はカードの中で済ませる。
7. **ファミリ混在は数字で確かめる。** S / LS / ALS / AS / F / 標準 TTL / HC / HCT が混ざる。ネットごとに、駆動側の IOL・IOH と受け側の入力電流の合計、VOH・VOL と VIH・VIL を一次資料の値で計算し、DR 資料に載せる。
8. **数値には根拠を付ける。** 抵抗値・遅延・電流・タイミングには、出典（DocID・頁）か計算式を添える。
9. **高圧を分離する。** ニキシー管の高圧（170 V 級）は表示基板に閉じ込め、ロジック基板へ引き込まない。
10. `sim/` は Python 標準ライブラリのみで動かす（3.10 以降）。IC モデルを変えたら `python -m unittest discover -s sim/tests -t .` を通す。
11. 命令セットや回路を変えたら、`docs/`・`sim/isa.py`・該当する DR 資料を同じ変更の中で直す。

## 公開範囲（このリポジトリは public）

- 載せるもの: 構成に採用した実型番（設計事実）、pinspec と電気特性（出典の DocID・頁・照合日）、自分で描いた回路、自分の言葉で書いた解説。
- ローカルにとどめるもの: 購入先・入手メモ・購入予定・採用していない手持ちの一覧。`collection/getstarting/` は Git 管理外で、参照も転記もしない。
- 手持ちとの照合は `scripts/role_coverage.py` をローカルで実行し、結果は標準出力で見るだけにする。パスは Git 管理外の `.private/config.json` に置く。
- 74 シリーズ以外の部品は、要件と候補の実型番を `hw/parts_non74.json` に、購入先と購入予定を Git 管理外の `.private/purchase_plan_non74.json` に分けて書く。7400 シリーズ IC の台帳は `collection/` 側のもので、ここの部品は載せない。
- データシートの本文・図表は転載せず、数値と出典だけを引く。

## 作業ルール

- 多数ファイルの生成・構成変更の前に計画を提示して合意を取る。変更量が 500 行を超えそうなら事前確認する。
- 大きな変更は `work-in-progress/YYYY-MM-DD_*.md` に作業ログを残す。
- パスはリポジトリルートからの相対パス。一時ファイルは `.temp/`（Git 管理外）。
- JSON は UTF-8 / `ensure_ascii=False` / `indent=2`。
- Windows では `python3` ではなく `python`。`kicad-cli` は `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`。
- サブモジュールは、Collection / Structures それぞれの作業コピーで編集して push し、ここでは `git submodule update --remote <名前>` でポインタを進める。`collection/structures`（入れ子）は初期化しない。
- commit / push はユーザーが指示したときだけ行う。
- 発注・支払い・JLCPCB へのログインはユーザーが行う。基板化の段階では `collection/pcb-demo/ORDER_CHECKLIST.md` に準じた発注ゲートを設ける。
