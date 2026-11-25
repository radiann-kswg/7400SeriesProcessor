# 2026-11-25 設計資料の定期 PDF（要件定義の冊とカードごとの冊）

## 依頼

- 7400sCCP8 の設計と仕様の PDF を、Git 管理外の `.private/docs-PDF/` に定期的に組むよう `AGENTS.md` に書く。図は Claude Design のものを優先する。
- 続けて、要件定義（システム設計まで）を 1 冊、カードの回路設計をカードごとに 1 冊で組む（まとめて 1 冊にはしない）。
- ARCHITECTURE.md と生成物の Mermaid の図は、閲覧用の図面に差し替え、ニキシー表示は新しく描く（ユーザーの選択）。

## 変更

- `AGENTS.md`: 「設計資料の定期 PDF（Git 管理外）」の節（冊の分け方、組むきっかけ、取りこぼしの拾い方、図の優先順位）。構成の一覧と Code Review Rules の公開範囲の項も合わせた。`CLAUDE.md` に Halvan での組み方を 1 文。
- `scripts/build_handout.py`: 章の `mermaid` で、Mermaid のコード（取り込んだ分を含む）を上から順に図へ差し替える。数が合わないと止まる。書式は `docs/handouts/README.md`。
- 構成ファイル: `docs/handouts/7400sCCP8_design.json`（付録 A は書き下ろし `7400sCCP8_design/generated.md` で生成物の一覧を取り込む）、`mul.json`、`reg8_574.json`。alu8 は既存の `alu8.json` をそのまま使う。
- 閲覧用の図面: キャンバス「7400sCCP8 アーキテクチャ図」に Nixie（ニキシー表示の概念図。`docs/ARCHITECTURE.md` 5 章の Mermaid と D17〜D19・D26・D35 から）を足し、`docs/design/images/arch_nixie.png` に書き出した（`images/README.md` を更新）。
- 続けて（ユーザーの依頼）、付録 A に残っていた生成物の図（`fig_loader.svg`・`fig_io.svg`）も清書した。キャンバスに Loader・Io を足し、`hw/system.json` の信号どおりに描いて `arch_loader.png`・`arch_io.png` に書き出し、`7400sCCP8_design/generated.md` の図を差し替えた。交差はローダ基板で 2 か所（KSCLK × KHIT_n、WI_n × LD0..7）、io 基板で 1 か所（IEN0_n × OUT0..7）。
- PDF の置き方を変えた（ユーザーの依頼）: 冊ごとに決まった名前 `.private/docs-PDF/<名前>.pdf` で上書きし、前の版は `.private/docs-PDF/.archive/<名前>_<その版の日付>.pdf` へ移す。`build_handout.py` に `--archive` を足し、`AGENTS.md`・`CLAUDE.md`・`docs/handouts/README.md` を合わせた。`.archive/` はユーザーが作り、11/23 版の 2 冊を入れてあった。

## 検証

| 内容 | 結果 |
|---|---|
| Halvan で `python scripts\build_handout.py <名前> --out .private\docs-PDF`（4 冊） | すべて成功。`7400sCCP8_design` 40 頁、`alu8` 24 頁、`mul` 13 頁、`reg8_574` 6 頁 |
| 図の差し替え後、`7400sCCP8_design` を `--archive` で組み直し | 成功（42 頁）。前の版が `.archive/7400sCCP8_design_2026-11-25.pdf` に移った。付録 A の図 A-1・A-2 が清書図になったことを目視 |
| PDF の文字層に Mermaid のコードが残っていないか | 4 冊とも 0 件 |
| 表紙・図・回路図の頁の目視 | 図 3-1・3-2（清書図）、付録 A の生成物の図 2 枚、mul・reg8_574 の回路図が読める |

## 未了

- reg8_574 には `DESIGN.md` と閲覧用の図面が無い（カード設計の段で作る）。冊は回路図と配線表だけ。
- commit はユーザーの指示待ち。作業ツリーにある mul カードの未コミット分（`2026-11-25_mul_card.md`）とは別のコミットにする。
