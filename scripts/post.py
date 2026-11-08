"""承認済みで投稿時刻を過ぎた投稿を、Instagram公式API（Instagramログイン版）でカルーセル公開する。

1回の実行で公開するのは最大1件（連投を防ぐため）。
必要な環境変数:
    IG_ACCESS_TOKEN   Instagramのアクセストークン（GitHub Secretsに保管）
    GITHUB_REPOSITORY GitHub Actionsが自動で設定（例: yourname/chelken-autopost）
    IMAGE_BRANCH      画像を置いているブランチ（省略時 main）
    DRY_RUN           "1" ならAPIを呼ばずに、何を投稿するかだけ表示
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
API = "https://graph.instagram.com/v23.0"
JST = timezone(timedelta(hours=9))
MAX_LATE = timedelta(hours=12)  # 予定から12時間以上遅れた投稿は自動では出さない


def log(msg):
    print(msg, flush=True)


def due_posts(now):
    for d in sorted(p for p in POSTS.iterdir() if (p / "post.json").exists()):
        data = json.loads((d / "post.json").read_text(encoding="utf-8"))
        if (d / "published.json").exists():
            continue
        if data.get("approved") is not True:
            continue
        when = datetime.fromisoformat(f"{data['date']}T{data['time']}").replace(tzinfo=JST)
        if when > now:
            continue
        if now - when > MAX_LATE:
            log(f"skip {d.name}: 予定時刻を12時間以上過ぎているため自動投稿しません")
            continue
        images = sorted((d / "images").glob("*.jpg"))
        if not images:
            log(f"skip {d.name}: 画像がまだありません")
            continue
        yield d, data, images


def caption_of(data):
    tags = " ".join(data.get("hashtags", []))
    return f"{data['caption'].strip()}\n\n{tags}".strip()


def api(method, path, token, **params):
    params["access_token"] = token
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text}")
    return r.json()


def wait_ready(container_id, token, tries=30):
    for _ in range(tries):
        status = api("GET", container_id, token, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} status {status}")
        time.sleep(5)
    raise RuntimeError(f"container {container_id} not ready")


def publish(d, data, images, token, repo, branch):
    base = f"https://raw.githubusercontent.com/{repo}/{branch}/posts/{d.name}/images"
    urls = [f"{base}/{p.name}" for p in images]
    caption = caption_of(data)

    if len(urls) == 1:
        c = api("POST", "me/media", token, image_url=urls[0], caption=caption)["id"]
    else:
        children = []
        for u in urls[:10]:
            cid = api("POST", "me/media", token, image_url=u, is_carousel_item="true")["id"]
            wait_ready(cid, token)
            children.append(cid)
        c = api("POST", "me/media", token, media_type="CAROUSEL",
                children=",".join(children), caption=caption)["id"]
    wait_ready(c, token)
    media_id = api("POST", "me/media_publish", token, creation_id=c)["id"]
    return media_id


def main():
    now = datetime.now(JST)
    dry = os.environ.get("DRY_RUN") == "1"
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("IMAGE_BRANCH", "main")

    for d, data, images in due_posts(now):
        log(f"due: {d.name} {data['date']} {data['time']} ({len(images)} slides)")
        if dry:
            log(caption_of(data))
            return
        if not token or not repo:
            log("IG_ACCESS_TOKEN がまだ登録されていないため、投稿をスキップしました")
            return
        media_id = publish(d, data, images, token, repo, branch)
        (d / "published.json").write_text(json.dumps(
            {"media_id": media_id, "published_at": datetime.now(JST).isoformat()},
            ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"published {d.name}: media_id={media_id}")
        return  # 1回の実行で1件だけ
    log("投稿する予定のものはありません")


if __name__ == "__main__":
    main()
