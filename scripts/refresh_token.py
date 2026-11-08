"""Instagramのアクセストークン（60日有効）を延長し、新しい値を標準出力に出す。

GitHub Actions の refresh ワークフローから呼ばれ、出力は gh secret set に直接渡される
（ログには出さない）。発行から24時間以上たったトークンでないと延長できない。
"""
import os
import sys

import requests

token = os.environ.get("IG_ACCESS_TOKEN", "")
if not token:
    sys.exit("IG_ACCESS_TOKEN がありません")

r = requests.get(
    "https://graph.instagram.com/refresh_access_token",
    params={"grant_type": "ig_refresh_token", "access_token": token},
    timeout=60,
)
if r.status_code >= 400:
    sys.exit(f"延長に失敗しました: {r.status_code} {r.text}")

data = r.json()
sys.stderr.write(f"延長しました（有効期間 約{int(data.get('expires_in', 0)) // 86400}日）\n")
sys.stdout.write(data["access_token"])
