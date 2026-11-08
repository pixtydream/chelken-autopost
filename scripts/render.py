"""投稿データ(posts/<日付>/post.json)からカルーセル画像(1080x1350 JPEG)を書き出す。

使い方:
    python scripts/render.py            # 画像がない投稿・中身が変わった投稿だけ書き出す
    python scripts/render.py --all      # すべて書き出し直す
    python scripts/render.py posts/2026-11-09   # 指定の投稿だけ
"""
import hashlib
import html
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
ACCOUNT = "@chelken3"

W, H = 1080, 1350
DARK, CREAM, SAND, LINE = "#2B1E16", "#FBF6EE", "#F2E8DA", "#E4D6C3"
SUB, ACCENT, ACCENT_LIGHT, RUST = "#5C4A3D", "#C24A20", "#E9875F", "#8E3415"

FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Zen+Kaku+Gothic+New:wght@400;700;900&family=Noto+Sans+JP:wght@400;700&display=swap">'
)

BASE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ width: {W}px; height: {H}px; }}
body {{ font-family: 'Noto Sans JP', sans-serif; }}
.page {{ width: {W}px; height: {H}px; padding: 96px 88px 80px;
        display: flex; flex-direction: column; justify-content: space-between; }}
.disp {{ font-family: 'Zen Kaku Gothic New', sans-serif; font-weight: 900; }}
.foot {{ display: flex; justify-content: space-between; align-items: flex-end;
        padding-top: 28px; font-size: 26px; }}
.pill {{ display: inline-block; padding: 10px 28px; border-radius: 999px;
        font-size: 30px; font-weight: 700; }}
"""


def e(text):
    """HTMLエスケープし、改行を<br>にする。"""
    return html.escape(str(text or "")).replace("\n", "<br>")


def cover(s):
    return f"""
<div class="page" style="background:{DARK};color:{CREAM}">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span class="pill" style="background:{ACCENT_LIGHT};color:{DARK}">{e(s.get('eyebrow'))}</span>
    <span style="font-size:28px;color:{LINE};letter-spacing:2px">{e(s.get('date_label'))}</span>
  </div>
  <div style="display:flex;flex-direction:column;gap:40px">
    <p style="font-size:44px;font-weight:700;color:{ACCENT_LIGHT}">{e(s.get('kicker'))}</p>
    <h1 class="disp" style="font-size:{s.get('title_size', 120)}px;line-height:1.15;letter-spacing:-2px">{e(s.get('title'))}</h1>
    <p style="font-size:38px;line-height:1.6;color:{LINE}">{e(s.get('lead'))}</p>
  </div>
  <div class="foot" style="border-top:2px solid {SUB};font-size:30px">
    <b>{ACCOUNT}</b><span style="color:{LINE}">{e(s.get('cta', '保存して行きたいお店リストに →'))}</span>
  </div>
</div>"""


def shop(s):
    rows = "".join(
        f"""<div style="display:flex;gap:32px">
          <p style="width:170px;flex-shrink:0;font-size:30px;font-weight:700;color:{RUST}">{e(k)}</p>
          <p style="font-size:30px;line-height:1.6">{e(v)}</p></div>"""
        for k, v in s.get("rows", [])
    )
    rows_box = (
        f'<div style="display:flex;flex-direction:column;gap:24px;background:{SAND};'
        f'border-radius:24px;padding:40px 48px">{rows}</div>'
        if rows
        else ""
    )
    badge = (
        f'<span class="pill" style="background:{DARK};color:{CREAM}">{e(s["badge"])}</span>'
        if s.get("badge")
        else ""
    )
    return f"""
<div class="page" style="background:{CREAM};color:{DARK}">
  <div style="display:flex;flex-direction:column;gap:44px">
    <div style="display:flex;align-items:center;gap:24px">
      <p class="disp" style="font-size:96px;line-height:1;color:{ACCENT}">{e(s.get('num'))}</p>{badge}
    </div>
    <div style="display:flex;flex-direction:column;gap:20px">
      <h2 class="disp" style="font-size:{s.get('name_size', 96)}px;line-height:1.15">{e(s.get('name'))}</h2>
      <p style="font-size:38px;font-weight:700;color:{SUB}">{e(s.get('area'))}</p>
    </div>
    <p style="font-size:40px;line-height:1.7">{e(s.get('body'))}</p>
  </div>
  {rows_box}
  <div class="foot" style="border-top:2px solid {LINE}">
    <span style="color:{SUB}">{e(s.get('source', '最新情報は各店の公式でご確認ください'))}</span><b>{ACCOUNT}</b>
  </div>
</div>"""


def price(s):
    def card(col, dark):
        bg, fg, rule, sub = (DARK, CREAM, SUB, LINE) if dark else (CREAM, DARK, LINE, SUB)
        lines = "".join(
            f"""<div style="display:flex;justify-content:space-between;align-items:baseline;
                 border-top:2px solid {rule};padding-top:20px">
              <p style="font-size:30px;color:{sub}">{e(label)}</p>
              <p class="disp" style="font-size:56px">{e(val)}<span style="font-size:28px">{e(col.get('unit', '円'))}</span></p></div>"""
            for label, val in col.get("lines", [])
        )
        return f"""<div style="background:{bg};color:{fg};border-radius:24px;padding:40px;
                    display:flex;flex-direction:column;gap:24px">
          <p style="font-size:36px;font-weight:700">{e(col.get('label'))}</p>{lines}</div>"""

    cols = s.get("columns", [])
    grid = "".join(card(c, i % 2 == 1) for i, c in enumerate(cols))
    notes = "".join(f'<p style="font-size:30px;line-height:1.6">{e(n)}</p>' for n in s.get("notes", []))
    return f"""
<div class="page" style="background:{SAND};color:{DARK}">
  <div style="display:flex;flex-direction:column;gap:20px">
    <p style="font-size:32px;font-weight:700;color:{RUST}">{e(s.get('kicker'))}</p>
    <h2 class="disp" style="font-size:92px;line-height:1.2">{e(s.get('title'))}</h2>
  </div>
  <div style="display:grid;grid-template-columns:repeat({max(len(cols), 1)},minmax(0,1fr));gap:24px">{grid}</div>
  <div style="display:flex;flex-direction:column;gap:14px">{notes}</div>
  <div class="foot" style="border-top:2px solid {LINE}">
    <span style="color:{SUB}">{e(s.get('source', '最新の料金は公式でご確認ください'))}</span><b>{ACCOUNT}</b>
  </div>
</div>"""


def listing(s):
    items = "".join(
        f"""<div style="display:flex;gap:28px;align-items:baseline;border-top:2px solid {LINE};padding-top:22px">
          <p class="disp" style="font-size:44px;color:{ACCENT};width:72px;flex-shrink:0">{i:02d}</p>
          <div><p style="font-size:38px;font-weight:700;line-height:1.4">{e(it.get('name'))}</p>
          <p style="font-size:28px;color:{SUB};line-height:1.5">{e(it.get('note'))}</p></div></div>"""
        for i, it in enumerate(s.get("items", []), start=s.get("start", 1))
    )
    return f"""
<div class="page" style="background:{CREAM};color:{DARK}">
  <div style="display:flex;flex-direction:column;gap:20px">
    <p style="font-size:32px;font-weight:700;color:{RUST}">{e(s.get('kicker'))}</p>
    <h2 class="disp" style="font-size:80px;line-height:1.2">{e(s.get('title'))}</h2>
  </div>
  <div style="display:flex;flex-direction:column;gap:22px">{items}</div>
  <div class="foot" style="border-top:2px solid {LINE}">
    <span style="color:{SUB}">{e(s.get('source', '最新情報は各店の公式でご確認ください'))}</span><b>{ACCOUNT}</b>
  </div>
</div>"""


LAYOUTS = {"cover": cover, "shop": shop, "price": price, "list": listing}


def page_html(slide):
    body = LAYOUTS[slide["layout"]](slide)
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{FONTS}<style>{BASE_CSS}</style></head><body>{body}</body></html>'


def slides_hash(post_dir: Path):
    data = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    blob = json.dumps(data["slides"], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def needs_render(post_dir: Path):
    stamp = post_dir / "images" / ".slides-hash"
    return not stamp.exists() or stamp.read_text().strip() != slides_hash(post_dir)


def render_post(page, post_dir: Path):
    data = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    out = post_dir / "images"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    for i, slide in enumerate(data["slides"], start=1):
        page.set_content(page_html(slide), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(out / f"{i:02d}.jpg"), type="jpeg", quality=92,
                        clip={"x": 0, "y": 0, "width": W, "height": H})
    (out / ".slides-hash").write_text(slides_hash(post_dir))
    print(f"rendered {post_dir.name}: {len(data['slides'])} slides")


def main(args):
    if args and args[0] != "--all":
        targets = [Path(a).resolve() for a in args]
    else:
        targets = sorted(p for p in POSTS.iterdir() if (p / "post.json").exists())
        if "--all" not in args:
            targets = [p for p in targets if needs_render(p)]
    if not targets:
        print("nothing to render")
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
        page = browser.new_page(viewport={"width": W, "height": H})
        for t in targets:
            render_post(page, t)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
