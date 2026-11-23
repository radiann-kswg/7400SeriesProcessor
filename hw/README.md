# hw — スロット・カード・構成と回路図生成

## データモデル

| ファイル | 内容 |
|---|---|
| `system.json` | システム階層の正本。ブロック（IC のまとまり）とブロック間の信号。`python scripts/gen_system.py [--svg]` で `docs/design/generated/` に全体図・IC 一覧・信号辞書を生成する（`--svg` は mermaid-cli の `mmdc` が要る） |
| `parts_non74.json` | 74 シリーズ以外の部品（プログラム記憶・発振子・電源・高圧）の要件と候補の実型番。購入先は書かない |
| `slots.json` | 役割（スロット）の定義。層（core / peripheral / panel）、必要数、機能上の候補型番 |
| `cards/<card>/card.json` | カード（実装）の定義。使う IC、実型番、全ピンの接続ネット、カードコネクタの信号 |
| `cards/<card>/DESIGN.md` | カードの解説（なぜそうつなぐか、電気計算、検証、目視チェックリスト）。章立ては `docs/DESIGN_DOCS.md` |
| `builds/<build>.json` | 構成。どのスロットにどのカードを挿すか |
| `pinspec/<型番>.json` | 一次資料を目視照合したピン情報（Collection の pinspec と同じ書式）。Collection に無い型番の分だけ置く |

新しい型番が手に入ったときの流れ:

1. `slots.json` の候補に無ければ、担える役割の `candidates` に追加する。
2. データシートを収集して目視照合し、pinspec を作る（`collection/CLAUDE.md` の手順）。
3. `cards/<新カード>/card.json` を書く。同じ役割の既存カードとコネクタ信号を揃える。
4. `python scripts/gen_card.py <新カード> --svg --erc` で配線表と回路図を生成し、目視確認する。
5. `sim/` にその IC の動作モデルを追加し、テストを通す。
6. `builds/` の構成でスロットの採用カードを差し替える。

## 回路図生成（`scripts/gen_card.py`）

`card.json` を唯一の正本として、次を生成する。生成物は手で編集しない。

- `WIRING.md` — IC ごとのピン配線表（ピン番号・名称・方向・接続ネット）、コネクタ表、ネット一覧、検査結果。
- `<card>.kicad_sch` — KiCad 回路図。IC は**実物の DIP と同じピン並び**の箱シンボル（左列が 1 番から下へ、右列が下から上へ）で描き、各ピンにネットラベルを付ける。同じラベル同士がつながる。
- `svg/<card>.svg` — `--svg` 指定時。GitHub 上でそのまま見られる。

検査（生成時に必ず実行される）:

- pinspec の全ピンに接続先（または `NC`）が書かれているか。
- 電源ピンが `VCC`、GND ピンが `GND` になっているか。出力ピンを電源に直結していないか。
- 接続先が 1 か所しかないネット、IC につながっていないコネクタ信号（警告）。
- `--erc` 指定時は `kicad-cli sch erc` も実行する。シンボルを回路図に埋め込んでいるため出る `lib_symbol_issues` は数えない。

`card.json` の書式は `cards/reg8_574/card.json` を見本にする。ネット名は ASCII、L アクティブ信号は `_n` を付ける。

## 状態

- `reg8_574` は生成工程の実証用カード。コネクタの信号並びは暫定。
- 74x181 / 74x182 / 74x89 / 74x284 / 74x285 は pinspec 作成済み（`hw/pinspec/`）。カードは `docs/design/SYSTEM.md`（システム設計の案）が承認されてから作る。
- 生成器はまだ IC とコネクタだけを扱う。受動部品（プルアップ抵抗など）、ネットごとの用途、`hw/system.json` の信号とカードのコネクタ信号の突き合わせ、電気特性（`hw/elec/`）による電流・レベルの計算は未対応で、core のカードを書く前に拡張する。
- 74x141（K155ID1）は一次資料が未入手のため pinspec 未作成（`docs/REQUIREMENTS.md` の R9）。
