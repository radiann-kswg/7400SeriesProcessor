@AGENTS.md

Claude 向け補足:

- Cowork では kicad-happy プラグイン（`kicad-happy:kicad` / `kicad-happy:jlcpcb` など）と、Windows 機 halvan の KiCad MCP・Desktop Commander が使える。使えない場合は作業を止めず、`kicad-cli` とファイル直接編集で代替する。
- データシートの目視照合は `collection/CLAUDE.md` の「対話型ファクトチェック手順」に従う（信頼度 85% 未満はユーザーに目視確認を依頼）。Cowork では PDF を作業コピーからステージし、Read のページ指定で直接目視してよい（PNG 化を省ける）。文字層から抜いた数値も、該当ページを目視してから採用する。
- 会話のロールプレイ設定がある場合も、リポジトリ内のファイル・コミットメッセージは中立な文体で書く。
- DR 用の清書図は、Cowork では Claude Design のキャンバス「7400sCCP8 アーキテクチャ図」に作る（データの流れ・制御の流れ・クロック位相・基板の構成・LED 表示）。`hw/system.json` か `docs/design/SYSTEM.md` を変えたら、キャンバスの該当する図を直し、`docs/design/images/` の PNG を書き出し直す（アートボードは静的なマークアップなので、`<x-dc>` の中身をそのまま HTML にしてヘッドレス Chrome で撮れる）。
