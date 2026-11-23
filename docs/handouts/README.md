# 公開用の資料（handout）

DR や紹介のために、リポジトリの Markdown・清書図・回路図を 1 冊の PDF に組んだものを **handout** と呼ぶ。
ここに置くのは組み方（構成ファイル）と、その資料のための書き下ろしの章だけ。本文の正本は各 Markdown のままで、ここには写さない。

| 資料 | 構成ファイル | 内容 |
|---|---|---|
| alu8 カード設計資料 | [`alu8.json`](alu8.json) | alu8 カードの DR 用。アーキテクチャの中の位置づけ、`DESIGN.md`、回路図、配線表、形式検証、出典 |

## 組み方

```
python scripts/build_handout.py alu8              # .temp/handouts/alu8_<日付>.pdf を作る
python scripts/build_handout.py alu8 --keep-html  # 組版前の HTML も残す（見た目の確認用）
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

共通のキー: `num`（章番号。「付録 A」なども可）、`title`、`source_label`（章の題の下に出す出典。既定はパス）、`figure_before`（`{"src", "caption"}`。章の頭に置く図）、`note`（`schematic` の説明文）。

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

## 載せてよいもの

- リポジトリにある Markdown・清書図（`docs/design/images/`。Claude Design で作図したもの）・生成物の回路図だけ。
- データシートの本文・図表、購入先・入手メモ、`.private/` と `collection/getstarting/` の内容は載せない。スクリプトもそれらのパスを拒む。
