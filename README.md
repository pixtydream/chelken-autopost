# @chelken3 自動投稿

関西グルメアカウント @chelken3 の投稿を、Instagram 公式API と GitHub Actions で自動化する仕組みです。外部の有料サービスは使いません。

## 毎週の流れ

1. 毎週日曜の朝、Claude が翌週7本分の企画と投稿データ（`posts/<日付>/post.json`）を作ります。
2. `post.json` が追加・変更されると、「画像を作る」が動き、`posts/<日付>/images/` にカルーセル画像（1080×1350）ができます。
3. 中身を確認して、OKの投稿は `post.json` の `"approved": false` を `true` に変えます（Claude に「11/10をOK」と頼んでも変えられます）。
4. 「インスタに投稿する」が30分ごとに動き、承認済みで投稿時刻を過ぎたものを1件ずつ公開します。公開すると `published.json` が残ります。

承認していない投稿は、時刻が来ても公開されません。予定から12時間以上過ぎた投稿も、自動では公開しません。

## 最初の設定（1回だけ）

GitHub の Secrets（Settings → Secrets and variables → Actions）に、次の2つを登録します。値は本人が貼り付けます。

| 名前 | 中身 |
| --- | --- |
| `IG_ACCESS_TOKEN` | Meta の開発者画面で発行した Instagram のアクセストークン |
| `GH_SECRETS_TOKEN` | GitHub の Fine-grained トークン（このリポジトリだけ、Secrets の Read and write 権限） |

`IG_ACCESS_TOKEN` は60日で切れるため、「インスタの鍵を延長する」が毎週月曜に延長して保存し直します。失敗すると GitHub からメールが届きます。

## 手動で動かす

Actions タブから各ワークフローを選び「Run workflow」で実行できます。「インスタに投稿する」は `dry_run` を `1` にすると、投稿せずに何が出るかだけ確認できます。

## ファイル

- `scripts/render.py` 画像の書き出し（レイアウト：cover / shop / price / list）
- `scripts/post.py` Instagram への投稿
- `scripts/refresh_token.py` アクセストークンの延長
- `.github/workflows/` 自動実行の設定
