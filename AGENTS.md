# AGENTS.md — 7400SeriesProcessor（全エージェント共通指示）

7400 シリーズ汎用ロジック IC のコレクションを「動作するコレクション」として組み上げる、自作 8bit CPU「7400sCCP8」（7400-series Complete Collection Processor）の設計リポジトリ。
希少な DIP IC（74x181 / 74x182 / 74x89 / 74x284 / 74x285 / 74x141 など）に CPU の中で実際の役割を与え、
手持ちの IC を可能な限り多種類使い、新しい型番が手に入ったら構成を差し替えられるようにする。

## 指示ファイルの構成（SSOT）

共通の指示はこの `AGENTS.md` にだけ書く（単一の正本）。エージェントごとのファイルには、その道具でしか通じないこと（ツール名・実行環境）だけを書き、ここの内容を写さない。

| エージェント | 読むファイル | エージェント別の補足 |
|---|---|---|
| Codex（CLI・アプリ・GitHub のコードレビュー） | `AGENTS.md`（変更したファイルに近いフォルダに `AGENTS.md` があれば、それも） | 置かない。レビューの観点はこのファイルの「Code Review Rules」 |
| Claude Code・Claude（Cowork） | `CLAUDE.md`（先頭の `@AGENTS.md` でこのファイルを読み込む） | `CLAUDE.md` |
| GitHub Copilot（コーディングエージェント・コードレビュー・VS Code） | ルートの `AGENTS.md` | 置かない（`.github/copilot-instructions.md` は作らない） |

- 共通の指示を変えるときは、このファイルだけを直す。
- 複数のエージェントが交互に作業する。判断・決定・未了の事項は会話にだけ残さず、`work-in-progress/` の作業ログと該当する DR 資料に書く。作業ログの終わりには「未了」を置く。
- 閲覧用の図面（設計ルール 12）は Claude Design で作るので、Claude だけが直せる。ほかのエージェントは閲覧用の図面を作らない。正本を変えて図面が古くなったら、作業ログの「未了」に書く。

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
| `collection/AGENTS.md` の「対話型ファクトチェック手順」 | データシートを目視照合して pinspec・電気特性を作るとき |

## 設計の進め方

回路は次の順に進め、各段の完了条件を満たしてから次へ進む。完了条件の詳細は `docs/DESIGN_DOCS.md`。

1. **システム設計** — `docs/design/SYSTEM.md` で、全 IC・カード間信号・命令ごとの制御信号・クロック位相・電気規格を決める。完了条件: ユーザーの承認。
2. **一次資料照合** — 採用する実型番ごとに pinspec と電気特性を作る。完了条件: 読み取り信頼度 85% 以上、未満の項目はユーザーの目視確認済み。
3. **カード設計** — `card.json` と `DESIGN.md` を書き、配線表・回路図を生成する。完了条件: 全ピンに接続先か理由付きの未接続、検査の警告 0、ERC 0。
4. **検証** — 配線どおりに組んだ信号レベルのモデルを命令レベルエミュレータ（`sim/machine.py`）と突き合わせ、全ネットの電流とレベルを計算する。完了条件: 全命令で一致、全ネットで余裕が正。
5. **DR** — ユーザーが DR 資料を目視する。完了条件: カードの `status` が `reviewed`。基板化は `reviewed` のカードだけで行う。

## スキルとプラグイン

段ごとに次を使う。その環境に無いものは、手順を本文で読んで同じことをするか、下の表の代わりの手段で進める（作業は止めない）。

| 段 | 使うもの | 使い方 |
|---|---|---|
| 全段 | ponytail（既定 `full`） | 下の「ponytail との併用」に従う |
| 要件・アーキテクチャの推敲 | mattpocock-skills の grilling・grill-with-docs。Claude では engineering の architecture・system-design も | 未決事項は推奨つきの質問で詰め、決まったら `docs/REQUIREMENTS.md` の D 番号にする |
| 一次資料照合 | kicad-happy の datasheets、PartsPlan、`collection/AGENTS.md` の「対話型ファクトチェック手順」 | 抜き出した数値は該当頁を目視してから採用する。信頼度 85% 未満はユーザーに確認する |
| カード設計 | kicad-happy の kicad・spice（RC の時定数など）、KiCad MCP（ERC・回路図の確認） | 回路図は `card.json` から生成する。MCP で回路図を直接描かない |
| 検証 | mattpocock-skills の tdd、Wolfram | テストを先に書く。グルー論理は真理値表の総当たりで確かめ、Wolfram は簡単化と等価性の証明に使う（証明はカードのフォルダに `verify.wl` として残す） |
| レビュー | ponytail-review（過剰設計）、mattpocock-skills の code-review（規約と仕様）、kicad-happy の kicad（回路の誤り） | 過剰設計と正しさは別々に見る |
| 基板化 | kicad-happy の jlcpcb・bom・emc | 発注ゲートの前に使う |

エージェントごとに使えるもの（2026-11-23 時点。Windows 機 halvan）:

| 道具 | Claude Code | Claude（Cowork） | Codex | 無いときの代わり |
|---|---|---|---|---|
| ponytail | プラグイン | プラグインの `SKILL.md` を読む（`CLAUDE.md`） | プラグイン | 下の「ponytail との併用」だけを守る |
| mattpocock-skills | プラグイン | プラグイン | プラグイン | — |
| kicad-happy | プラグイン | プラグイン | 無い | `scripts/gen_card.py` の検査と ERC。回路図の解析が要るときは Claude に回し、作業ログに書く |
| KiCad MCP | あり | あり | あり | `kicad-cli` |
| PartsPlan・Wolfram・Claude Design | 無い | あり | 無い | 照合は PDF の目視、論理の確認は `sim/` のテスト |

### ponytail との併用

ponytail（「要るか・既にあるか・もっと少なくできるか」を先に問う）は、このリポジトリでは次のように読む。

- 減らすのは設計の量で、確かめる量ではない。DR 資料の章立て、一次資料の照合、完了条件の検査、`Rd` などの保護素子は省かない。
- IC・ゲート・抵抗・スクリプト・文書を足すのは、外すと欠ける機能を言えるときだけ（設計ルール 2）。飾りの IC、「あとで使うかも」の回路や引数は置かない。
- 既にあるものを先に使う。生成器は `scripts/gen_card.py` と `scripts/gen_system.py` を直し、新しいスクリプトや依存を増やさない（`sim/` は標準ライブラリのみ）。
- 実物で決める値には調整の余地を残す（速度のボリューム、LED の抵抗値など）。
- 「説明は短く」はコードと会話に当てはめる。ユーザーが読む DR 資料（`DESIGN.md` の各章）は省かない。
- 単純化で上限を作ったときは、そこに `ponytail:` で始まる注記を書き、上限と広げ方を残す。

ponytail は Claude Code と Codex ではプラグイン（`ponytail`、`ponytail-review`）で使う。プラグインの無い環境では、そのプラグインの `skills/ponytail/SKILL.md` と `skills/ponytail-review/SKILL.md` を読んで従う。

## 構成

```
docs/                     要件・アーキテクチャ・DR 資料の規格
docs/design/              システム階層の DR 資料
docs/design/generated/    システム階層の生成物（全体図・IC 一覧・信号辞書）
docs/design/images/       閲覧用の図面（Claude Design で作図して書き出した PNG。設計ルール 12）
docs/handouts/            公開用の資料（handout）と設計資料 PDF の構成ファイル、書き下ろしの章。PDF は置かない
hw/system.json            システム階層の正本（ブロックとブロック間の信号）
hw/slots.json             役割（スロット）定義と候補型番
hw/cards/<card>/          カード定義 card.json、解説 DESIGN.md、生成物（WIRING.md / .kicad_sch / svg/）
hw/builds/<build>.json    構成（スロット → 採用カード）
hw/pinspec/               このリポジトリで照合した pinspec（Collection に無い型番の分）
sim/                      IC 動作モデル（ic74/）、エミュレータ、アセンブラ、テスト
scripts/                  gen_system.py（全体図・一覧の生成）、gen_card.py（回路図生成）、build_handout.py（handout の PDF 組版）、role_coverage.py（役割カバレッジ。ローカル専用）
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
12. **閲覧用の図面は Claude Design で作図する。** 回路図（`*.kicad_sch`・`svg/`）と `docs/design/generated/` の図は正本からの生成物で、手で描かない。それとは別に、構造や流れを人が読み取るための図面（アーキテクチャ、カードの中の構造（例: alu8 の桁上げの流れ）、クロック位相、基板の構成、LED 表示など。DR 資料や配布用の PDF に載せる図を含む）は、Claude Design のキャンバスで作図し、`docs/design/images/` に PNG で書き出して、一覧と書き出し日を同じフォルダの `README.md` に書く。Mermaid・手書きの SVG・画像編集で代わりの図面を作らない。図面の内容が正本と食い違ったら正本を正とし、図面を直す。

## 検証のコマンド

変更したら、関係するものを実行して、結果を作業ログか PR に書く。Windows では `python3` を `python` に読み替える。

| 対象 | コマンド | 通る条件 |
|---|---|---|
| `sim/`・IC モデル・カードの配線 | `python3 -m unittest discover -s sim/tests -t .` | 全件 OK |
| `hw/system.json`・`hw/builds/` | `python3 scripts/gen_system.py` | 警告 0。`docs/design/generated/` に差分が出ない（出たら生成物も同じ変更に含める） |
| `hw/cards/*/card.json` | `python3 scripts/gen_card.py --all`（ERC は `--erc`。kicad-cli が要る） | 警告 0、ERC 0。生成物に差分が出ない |
| カードの論理の証明 | `hw/cards/<card>/verify.wl` を Wolfram で評価 | 全項目 True。Wolfram が無い環境では省き、省いたと書く |
| `docs/handouts/`、handout が取り込む文書 | `python3 scripts/build_handout.py <名前>` | PDF ができる（`include` の見出し・表・行が正本に残っている）。pandoc が無い環境では省き、省いたと書く |

- `collection/` は非公開のサブモジュールで、取得できない環境（クラウドのレビューなど）がある。そのときは Collection の pinspec を使うカード（`reg8_574` など）の生成を省き、`gen_system.py` の IC 一覧の pinspec 欄に出る差分は生成物に含めない。`hw/pinspec/` にある型番だけを使うカードと `sim/` のテストは動く。

## 公開範囲（このリポジトリは public）

- 載せるもの: 構成に採用した実型番（設計事実）、pinspec と電気特性（出典の DocID・頁・照合日）、自分で描いた回路、自分の言葉で書いた解説。
- ローカルにとどめるもの: 購入先・入手メモ・購入予定・採用していない手持ちの一覧。`collection/getstarting/` は Git 管理外で、参照も転記もしない。
- 手持ちとの照合は `scripts/role_coverage.py` をローカルで実行し、結果は標準出力で見るだけにする。パスは Git 管理外の `.private/config.json` に置く。
- 74 シリーズ以外の部品は、要件と候補の実型番を `hw/parts_non74.json` に、購入先と購入予定を Git 管理外の `.private/purchase_plan_non74.json` に分けて書く。7400 シリーズ IC の台帳は `collection/` 側のもので、ここの部品は載せない。
- データシートの本文・図表は転載せず、数値と出典だけを引く。

## 公開用の資料（handout）

DR や紹介に配る PDF は、リポジトリの Markdown・閲覧用の図面・回路図から `scripts/build_handout.py` で組む。書式は `docs/handouts/README.md`。

- 資料ごとに、構成ファイル `docs/handouts/<名前>.json` と、その資料のための書き下ろしの章 `docs/handouts/<名前>/*.md` を置く。ほかの文書の表や節は `<!-- include: ... -->` で組むたびに取り込み、写さない。
- `python3 scripts/build_handout.py <名前>` で `.temp/handouts/<名前>_<日付>.pdf` を作る。pandoc と Chrome（または Edge）が要る。Python 側は標準ライブラリだけで、pandoc と Chrome は外部コマンドとして呼ぶ（設計ルール 10 の対象は `sim/`、Code Review Rules の依存の項は `scripts/gen_*.py`）。
- PDF はコミットしない。DR が済んだ版（カードの `status` が `reviewed`）だけを、ユーザーの指示で GitHub Releases に添付する。
- 載せる図は、閲覧用の図面（設計ルール 12）と生成物の回路図だけ。公開範囲（上の節）を守る。スクリプトは `.private/`・`collection/getstarting/`・`.temp/` のパスを拒む。
- 正本の見出し・表・行を変えたら、それを取り込む handout が組めるかを `build_handout.py` で確かめる（合わない `include` があると止まる）。pandoc の無い環境では、作業ログの「未了」に書いて、組める環境（Claude の Cowork など）に回す。

## 設計資料の定期 PDF（Git 管理外）

7400sCCP8 の設計と仕様を PDF（設計資料 PDF）に組み、設計が進むたびに組み直して `.private/docs-PDF/` に残す。ユーザーが通して読むための、その時点の写しで、DR 前の内容も含む。配らない（配るのは DR 済みの handout）。

- 冊の分け方: 要件定義とシステム設計で 1 冊（構成ファイル `docs/handouts/7400sCCP8_design.json`）、カードごとに 1 冊（`docs/handouts/<カード名>.json`。そのカードの handout の構成ファイルを兼ねる）。まとめて 1 冊にはしない。構成ファイルが無ければ最初に組むときに作り、`docs/handouts/README.md` の一覧に足す。
- 組み方は handout と同じで、`--archive` を付ける。`python3 scripts/build_handout.py <名前> --out .private/docs-PDF --archive` で `.private/docs-PDF/<名前>.pdf` を上書きし、前の版は `.private/docs-PDF/.archive/<名前>_<その版の日付>.pdf` へ移す（同じ日の版は最後のものだけ残る）。旧版は消さない。
- 中身: 要件定義の冊は、本文に `README.md`・`docs/REQUIREMENTS.md`・`docs/ARCHITECTURE.md`・`docs/design/SYSTEM.md`・`docs/DESIGN_DOCS.md`、付録にシステム階層の生成物（IC 一覧・信号辞書など）と閲覧用の図面の一覧。表紙の「状態」には段階計画の段を書く。カードの冊は `DESIGN.md`・回路図・`WIRING.md`（あれば `verify.wl`）で、表紙の「状態」にはカードの `status` を書く。
- 次のどれかを含む作業を終えたら、その作業の最後に該当する冊を組む。ユーザーが求めたときも組む。
  1. `docs/REQUIREMENTS.md` の決定事項（D 番号）を足した・改めた、段階計画の段が進んだ、または `docs/ARCHITECTURE.md`・`docs/design/SYSTEM.md`・`hw/system.json` を変えた → 要件定義の冊。
  2. カードを足した、またはカードの `card.json`・`DESIGN.md`・`status` を変えた → そのカードの冊（カードを足したら構成ファイルも作る）。
- 取りこぼしを拾うため、作業の初めに `.private/docs-PDF/<名前>.pdf` の更新日（表紙の作成日）を冊ごとに見る。`git log --since=<その日付> -- <その冊の正本>`（要件定義の冊は上の 1 の文書、カードの冊は `hw/cards/<カード名>`）に履歴があれば、その作業の最後に組む。
- 図は閲覧用の図面（設計ルール 12。Claude Design で作図した `docs/design/images/` の PNG）を優先する。表紙と章の頭の図（`cover_image`・`figure_before`）もここから選ぶ。章の中の Mermaid の図は、構成ファイルの `mermaid` で閲覧用の図面に差し替える（書き方は `docs/handouts/README.md`）。`docs/design/generated/` の図は、同じ内容の閲覧用の図面がまだ無い範囲にだけ使う。カードの回路図（`scripts/gen_card.py` の生成物）はそのまま載せる。
- 閲覧用の図面が正本より古いとき（作業ログの「未了」に図面の更新が残っているなど）は、先に図面を直して書き出し直してから組む。図面を直せないエージェント（Claude 以外）は組まずに、作業ログの「未了」に「設計資料 PDF の組み直し（図面の更新待ち）」と書いて Claude に回す。pandoc か Chrome の無い環境でも、組まずに「未了」に書く。
- PDF はコミットせず、Releases にも添付しない。載せるのは handout と同じく、リポジトリの文書と図だけ（公開範囲の節）。

## 作業ルール

- 多数ファイルの生成・構成変更の前に計画を提示して合意を取る。変更量が 500 行を超えそうなら事前確認する。
- 大きな変更は `work-in-progress/YYYY-MM-DD_*.md` に作業ログを残す。
- パスはリポジトリルートからの相対パス。一時ファイルは `.temp/`（Git 管理外）。
- JSON は UTF-8 / `ensure_ascii=False` / `indent=2`。
- Windows では `python3` ではなく `python`。`kicad-cli` は `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`。
- サブモジュールは、Collection / Structures それぞれの作業コピーで編集して push し、ここでは `git submodule update --remote <名前>` でポインタを進める。`collection/structures`（入れ子）は初期化しない。
- commit / push はユーザーが指示したときだけ行う。
- 発注・支払い・JLCPCB へのログインはユーザーが行う。基板化の段階では `collection/pcb-demo/ORDER_CHECKLIST.md` に準じた発注ゲートを設ける。

## Code Review Rules

このリポジトリの変更をレビューするときに確かめること。書式や表記の細部は指摘しない。

### 正本と生成物

- `hw/cards/*/WIRING.md`・`*.kicad_sch`・`svg/` と `docs/design/generated/` は生成物。正本（`card.json`・`hw/system.json`・`hw/builds/`）の変更を伴わずに生成物だけが変わっていたら、手で編集したものとして指摘する。正本だけが変わって生成物が古いままのときも指摘する。正しい直し方は、正本を直して `scripts/gen_card.py`・`scripts/gen_system.py` で再生成し、同じ変更に含めること。
- 命令セットや制御信号を変えたのに、`sim/isa.py`・`docs/design/SYSTEM.md`・`sim/tests/` のどれかが追従していなければ指摘する（設計ルール 11）。
- `sim/` と `scripts/gen_*.py` に標準ライブラリ以外の依存を足していたら指摘する（kicad-cli の呼び出しは除く）。
- 閲覧用の図面（設計ルール 12）を Claude Design 以外で足していたら（Mermaid の清書、手書きの SVG、画像編集した PNG）、または `docs/design/images/` の PNG を変えたのに `README.md` の一覧・書き出し日が追従していなければ指摘する。正本の変更で図面が古くなるのに、作業ログの「未了」に書いていないときも指摘する。

### 一次資料と数値

- `hw/pinspec/`・`hw/elec/` の値や `DESIGN.md` の数値（電流・電圧・遅延・抵抗値）に、出典（DocID と頁）か計算式が無ければ指摘する。読み取り信頼度が 85% 未満の値は、ユーザーが確認したと書かれていなければ指摘する。
- 電気特性を汎用型番や別ファミリの値で計算していたら指摘する（74S181 と 74LS181 で入力電流が 5 倍違う）。採用した実型番は `hw/builds/default.json` とカードの `device`。

### 回路

- TTL の入力の未接続、トーテムポール出力どうしの接続、3 ステートやオープンコレクタの共有ネットで同時に駆動しないことの説明の欠け、オープンコレクタのネットのプルアップの計算の欠けは、誤配線として指摘する。
- 74x181 をアクティブ High データで使うとき、桁上げ（Cn・Cn+4・74x182 の Cn+x）は L で桁上げあり。極性を取り違えた配線や論理式を指摘する。
- テストや検査を弱めて通している変更（比べる組み合わせを減らす、数えない警告の種類を足す、期待値をモデルの出力に合わせて書き換える）は、理由が書かれていなければ指摘する。

### 公開範囲

- このリポジトリは public。購入先・入手メモ・購入予定・採用していない手持ちの一覧、`collection/getstarting/` や `.private/` の内容、データシートの本文・図表の転載が入っていたら指摘する。
- handout や設計資料 PDF をコミットしていたら指摘する（handout は Releases に添付し、設計資料 PDF は `.private/docs-PDF/` に置く）。`docs/handouts/` の書き下ろしの章に、ほかの文書の表や節を写していたら指摘する（`include` で取り込む）。
