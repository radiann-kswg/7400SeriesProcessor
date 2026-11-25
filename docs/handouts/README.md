# 公開用の資料（handout）

DR や紹介のために、リポジトリの Markdown・清書図・回路図を 1 冊の PDF に組んだものを **handout** と呼ぶ。
ここに置くのは組み方（構成ファイル）と、その資料のための書き下ろしの章だけ。本文の正本は各 Markdown のままで、ここには写さない。
同じ構成ファイルで、設計の途中の写し（設計資料 PDF。`AGENTS.md`「設計資料の定期 PDF」）も組む。

| 資料 | 構成ファイル | 内容 |
|---|---|---|
| 7400sCCP8 設計資料 | [`7400sCCP8_design.json`](7400sCCP8_design.json) | 要件・アーキテクチャ・システム設計。`README.md`・`REQUIREMENTS.md`・`ARCHITECTURE.md`・`SYSTEM.md`・`DESIGN_DOCS.md`、付録にシステム階層の生成物と閲覧用の図面の一覧 |
| alu8 カード設計資料 | [`alu8.json`](alu8.json) | alu8 カードの DR 用。アーキテクチャの中の位置づけ、`DESIGN.md`、回路図、配線表、形式検証、出典 |
| mul カード設計資料 | [`mul.json`](mul.json) | mul カードの `DESIGN.md`、回路図、配線表 |
| reg8_574 カード設計資料 | [`reg8_574.json`](reg8_574.json) | reg8_574 カードの回路図、配線表（`DESIGN.md` は未作成） |

## 組み方

```
python scripts/build_handout.py alu8              # .temp/handouts/alu8_<日付>.pdf を作る
python scripts/build_handout.py alu8 --keep-html  # 組版前の HTML も残す（見た目の確認用）
python scripts/build_handout.py alu8 --out .private/docs-PDF --archive  # 設計資料 PDF: alu8.pdf を上書きし、前の版を .archive/ へ移す
```

- 要るもの: [pandoc](https://pandoc.org/)、Chrome か Edge（ヘッドレスで PDF を書き出す）。Python は標準ライブラリだけ。
- 出力は `.temp/handouts/`（Git 管理外）。PDF はコミットしない。
- DR が済んだ版（カードの `status` が `reviewed` になったとき）だけ、ユーザーの指示で GitHub Releases に添付する。

## 構成ファイル `<名前>.json`

| キー | 中身 |
|---|---|
| `title` / `subtitle` | 表紙の題と副題。頁の上の見出しは `title`（日付） |
| `cover_image` | 表紙の図（リポジトリからの相対パス） |
| `status` | 表紙の「状態」の欄 |
| `contents` | 表紙の「収録」の欄 |
| `note` | 表紙の下の注記 |
| `chapters` | 章の並び（下の表） |

章（`chapters` の要素）は、次のどれか 1 つで中身を指す。パスはリポジトリのルートからの相対パス。

| キー | 中身 |
|---|---|
| `md` | Markdown を 1 本。先頭が `# 見出し` ならそれを章の題にする（`title` を書けばそちらが優先）。下の `include` を展開する |
| `schematic` | 回路図の SVG（`scripts/gen_card.py` の生成物）。描いてある範囲に詰めて、A3 横の頁に置く |
| `code` | ソースコードを 1 本、そのまま載せる |

共通のキー: `num`（章番号。「付録 A」なども可）、`title`、`source_label`（章の題の下に出す出典。既定はパス）、`figure_before`（`{"src", "caption"}`。章の頭に置く図）、`note`（`schematic` の説明文）、`mermaid`（`md` の章の Mermaid の図を差し替える図。下の節）。

## 書き下ろしの章から正本を取り込む `include`

書き下ろしの章（`docs/handouts/<名前>/*.md`）で他の文書の表や節を使うときは、写さずに次の 1 行で取り込む。
HTML コメントなので GitHub 上では見えない。組むたびに正本から取り込むので、正本を直せば資料も追従する。

```
<!-- include: docs/design/SYSTEM.md section="## 4. 制御表" table=1 rows="0 / 1;2 / 3" cols=9 -->
```

| 引数 | 意味 |
|---|---|
| 先頭のパス | 取り込む Markdown |
| `section` | 見出しの行（前方一致）。その見出しから、同じか上の階層の次の見出しの手前まで。省略すると文書全体 |
| `table` | 範囲の中の何番目の表か（1 から）。`rows`（先頭の列の値を `;` で区切る。見出し行は常に入る）と `cols`（左から何列）で絞れる |
| `lines` | 範囲の中で、これで始まる行だけを取り込む（`;` で区切って複数） |

`table` も `lines` も無ければ、見出しの行を除いた範囲全体を取り込む。指定に合うものが無いときは組版を止める（正本の見出しや表が変わったことに気づけるように）。

## Mermaid の図を差し替える `mermaid`

`md` の章（`include` で取り込んだ分を含む）に Mermaid のコードがあると、そのままではコードの文字で載る。図は閲覧用の図面を優先するので（`AGENTS.md` 設計ルール 12）、その章に `mermaid` を書き、上から順に差し替える図を並べる。

```
"mermaid": [{"src": "docs/design/images/arch_datapath.png", "caption": "図 3-1　データの流れ"}]
```

- 図は `docs/design/images/` の閲覧用の図面から選ぶ。同じ内容の図面がまだ無いときだけ `docs/design/generated/` の SVG を使う。
- 章の中の Mermaid の数と `mermaid` の数が合わないと止まる（正本に Mermaid の図が増えたことに気づけるように）。

## 載せてよいもの

- リポジトリにある Markdown・清書図（`docs/design/images/`。Claude Design で作図したもの）・生成物の回路図だけ。
- データシートの本文・図表、購入先・入手メモ、`.private/` と `collection/getstarting/` の内容は載せない。スクリプトもそれらのパスを拒む。
