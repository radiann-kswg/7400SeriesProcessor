@AGENTS.md

Claude 向け補足（共通の指示は `AGENTS.md` にだけ書く。ここには Claude の道具でしか通じないことだけを書く）:

- Cowork では Halvan の Desktop Commander・KiCad MCP（`mcp__remote-devices__kicad__*`。2026-11-23 から）・kicad-happy プラグインが使える。使えない場合は作業を止めず、`kicad-cli` とファイル直接編集で代替する。
- Cowork には ponytail のプラグインが無い。作業の初めに Desktop Commander で `%USERPROFILE%\.claude\plugins\cache\ponytail\ponytail\<版>\skills\ponytail\SKILL.md`（レビューのときは `ponytail-review` も）を読んで従う。
- データシートの目視照合は `collection/AGENTS.md` の「対話型ファクトチェック手順」に従う（信頼度 85% 未満はユーザーに目視確認を依頼）。Cowork では PDF を作業コピーからステージし、Read のページ指定で直接目視してよい（PNG 化を省ける）。文字層から抜いた数値も、該当ページを目視してから採用する。
- handout（`AGENTS.md`「公開用の資料」）は Halvan で組む（pandoc は 2026-11-23 に winget で `%LOCALAPPDATA%\Pandoc` へ導入）。Desktop Commander の PowerShell は PATH が古いことがあるので、`$env:Path = "$env:LOCALAPPDATA\Pandoc;" + $env:Path` を付けてから `python scripts\build_handout.py <名前>` を実行する。仕上がりは PDF をステージして Read で頁を見る。
- 会話のロールプレイ設定がある場合も、リポジトリ内のファイル・コミットメッセージは中立な文体で書く。
- 閲覧用の図面（`AGENTS.md` 設計ルール 12）は Claude Design のキャンバス「7400sCCP8 アーキテクチャ図」に作る（データの流れ・制御の流れ・クロック位相・基板の構成・LED 表示、カードの中の構造図）。配布用の PDF などに載せる図も、このキャンバスのアートボードから書き出したものを使う。`hw/system.json`・`docs/design/SYSTEM.md`・カードの `card.json` か `DESIGN.md` を変えたとき、または作業ログの「未了」に清書図の更新があるときは、キャンバスの該当する図を直し、`docs/design/images/` の PNG を書き出し直す（アートボードは静的なマークアップなので、`<x-dc>` の中身をそのまま HTML にしてヘッドレス Chrome で撮れる）。
