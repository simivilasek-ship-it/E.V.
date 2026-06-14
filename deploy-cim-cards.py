#!/usr/bin/env python3
"""Čím létáme (721): fotky Skylark + Skyleader a hezčí karty."""
import base64
import importlib.util
import json
import os
import urllib.parse
import urllib.request

_spec = importlib.util.spec_from_file_location(
    "d", os.path.join(os.path.dirname(__file__), "deploy-pages-api.py")
)
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

_spec2 = importlib.util.spec_from_file_location(
    "p", os.path.join(os.path.dirname(__file__), "deploy-content-updates.py")
)
P = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(P)

SITE = D.SITE
SKYLARK = {
    "url": f"{SITE}/wp-content/uploads/2026/06/Skylark-2019.jpg",
    "id": 499,
    "source": "library",
}
SKYLEADER_PATH = (
    "/home/simi/.cursor/projects/home-simi-Sta-en-nepojmenovan-slo-ka/assets/"
    "Skyleader_GP_7-1f327aea-4602-485f-97ac-d0af66d92eb7.png"
)
CSS_PATH = "wp-content/themes/hello-elementor/assets/klz-site.css"
CSS_MARKER = "/* KLZ Čím létáme karty v2 */"
OLD_CSS_MARKERS = ["/* KLZ Čím létáme karty v1 */", "/* KLZ Čím létáme karty v2 */"]

LABEL = (
    '<p style="color:#b80000;font-size:11px;font-weight:700;'
    'letter-spacing:2px;text-transform:uppercase;margin:0 0 8px;">{text}</p>'
)

CARD_CSS = """
/* KLZ Čím létáme karty v2 */
.elementor-721 .e-con[data-id="clmain04"]{
  display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;
  gap:28px!important;align-items:stretch!important;width:100%!important;
  max-width:960px!important;margin:0 auto!important;justify-content:center!important;
  flex-wrap:unset!important}
.elementor-721 .e-con[data-id="clc1"],
.elementor-721 .e-con[data-id="clc2"]{
  width:100%!important;max-width:100%!important;min-width:0!important;
  --width:100%!important;flex:1 1 auto!important;
  overflow:hidden!important;display:flex!important;flex-direction:column!important;
  background:#fff!important;border:1px solid #e8eef5!important;
  border-radius:16px!important;box-shadow:0 10px 32px rgba(15,15,15,0.07)!important;
  padding:0!important;height:100%!important}
.elementor-721 .e-con[data-id="clc1"] .elementor-widget-image,
.elementor-721 .e-con[data-id="clc2"] .elementor-widget-image{
  width:100%!important;margin:0!important}
.elementor-721 .e-con[data-id="clc1"] .elementor-widget-image img,
.elementor-721 .e-con[data-id="clc2"] .elementor-widget-image img{
  width:100%!important;height:240px!important;object-fit:cover!important;
  display:block!important;border-radius:0!important}
.elementor-721 .e-con[data-id="clc1"] .elementor-widget-text-editor,
.elementor-721 .e-con[data-id="clc2"] .elementor-widget-text-editor,
.elementor-721 .e-con[data-id="clc1"] .elementor-widget-heading,
.elementor-721 .e-con[data-id="clc2"] .elementor-widget-heading{
  padding-left:24px!important;padding-right:24px!important}
.elementor-721 .elementor-element-clc1h,
.elementor-721 .elementor-element-clc2h{margin-top:8px!important}
.elementor-721 .elementor-element-clc1g,
.elementor-721 .elementor-element-clc2g{padding:20px 24px 0!important}
.elementor-721 .elementor-element-clc1t,
.elementor-721 .elementor-element-clc2t{
  padding-bottom:28px!important;flex:1!important}
.elementor-721 .elementor-element-clc1t p,
.elementor-721 .elementor-element-clc2t p{margin:0!important}
@media (max-width:767px){
  .elementor-721 .e-con[data-id="clmain04"]{grid-template-columns:1fr!important;gap:20px!important}
  .elementor-721 .e-con[data-id="clc1"] .elementor-widget-image img,
  .elementor-721 .e-con[data-id="clc2"] .elementor-widget-image img{height:210px!important}}
"""


def upload_media(wp, filepath, filename, alt):
    with open(filepath, "rb") as f:
        body = f.read()
    req = urllib.request.Request(
        f"{SITE}/index.php?rest_route=/wp/v2/media",
        data=body,
        method="POST",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg",
            "X-WP-Nonce": wp.nonce(),
        },
    )
    resp = json.loads(wp.op.open(req).read().decode())
    aid = resp["id"]
    wp.rest(
        "POST",
        f"/wp/v2/media/{aid}",
        {"alt_text": alt, "title": "GP-7 Skyleader OK-PUA 67"},
    )
    return {"url": resp["source_url"], "id": aid, "source": "library"}


def image_widget(wid, image, alt):
    return {
        "id": wid,
        "elType": "widget",
        "widgetType": "image",
        "settings": {
            "image": image,
            "image_size": "large",
            "align": "center",
            "image_alt": alt,
            "width": {"unit": "%", "size": 100},
            "width_mobile": {"unit": "%", "size": 100},
        },
        "elements": [],
    }


def patch_cards(elements, skyleader_img):
    card_style = {
        "flex_direction": "column",
        "width": {"unit": "%", "size": 100},
        "width_tablet": {"unit": "%", "size": 100},
        "width_mobile": {"unit": "%", "size": 100},
        "background_background": "classic",
        "background_color": "#ffffff",
        "border_border": "none",
        "padding": {"unit": "px", "top": 0, "right": 0, "bottom": 0, "left": 0, "isLinked": True},
        "content_width": "full",
    }
    row = P.find_widget(elements, "clmain04")
    row["settings"]["flex_direction"] = "row"
    row["settings"]["flex_wrap"] = "wrap"
    row["settings"]["gap"] = {"unit": "px", "size": 28, "column": "28", "row": "28", "isLinked": True}

    for cid, tag, img_id, img, alt in [
        ("clc1", "Dolnoplošník", "clc1i", SKYLARK, "Letoun DV-1 Skylark OK-MUA 73 na letišti"),
        ("clc2", "Hornoplošník", "clc2i", skyleader_img, "Letoun GP-7 Skyleader OK-PUA 67 na letišti"),
    ]:
        card = P.find_widget(elements, cid)
        card["settings"].update(card_style)
        kids = card.setdefault("elements", [])
        # tag widget
        tag_w = P.find_widget(elements, cid + "g")
        if not tag_w:
            tag_w = {
                "id": cid + "g",
                "elType": "widget",
                "widgetType": "text-editor",
                "settings": {"editor": LABEL.format(text=tag)},
                "elements": [],
            }
            h_idx = next(i for i, e in enumerate(kids) if e.get("id") == cid + "h")
            kids.insert(h_idx, tag_w)
        else:
            tag_w["settings"]["editor"] = LABEL.format(text=tag)
        tag_w["settings"]["_padding"] = {
            "unit": "px", "top": 0, "right": 24, "bottom": 0, "left": 24, "isLinked": False
        }
        # image widget
        existing = P.find_widget(elements, img_id)
        if existing:
            existing["settings"]["image"] = img
            existing["settings"]["image_alt"] = alt
        else:
            kids.insert(0, image_widget(img_id, img, alt))


def deploy_page(wp, pid, elements, done_key):
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = f"klz_el{pid}"
    wp.cli(f"option delete {done_key}", confirm=True)
    wp.cli(f"option delete {prefix}_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update {prefix}_{i} "{esc}"', confirm=True)
    wp.cli(f"option update {prefix}_parts {len(chunks)}", confirm=True)
    runner = f"""add_action('init', function () {{
    $parts = (int) get_option('{prefix}_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('{prefix}_' . $i, '');
    if (!$b64) return;
    $data = json_decode(base64_decode($b64), true);
    if (!is_array($data)) return;
    update_post_meta({pid}, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta({pid}, '_elementor_element_cache');
    delete_post_meta({pid}, '_elementor_css');
    update_option('{done_key}', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/?pagename=cim-letame").read(32768)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )


def deploy_css(wp):
    css = urllib.request.urlopen(
        f"{SITE}/wp-content/themes/hello-elementor/assets/klz-site.css?ver=20260615"
    ).read().decode("utf-8", "replace")
    for marker in OLD_CSS_MARKERS:
        if marker in css:
            start = css.index(marker)
            end = css.find("\n/* ", start + len(marker))
            css = css[:start] + (css[end:] if end != -1 else "")
    css = css.rstrip() + "\n\n" + CARD_CSS.strip() + "\n"
    b64 = base64.b64encode(css.encode()).decode()
    wp.cli("option delete klz_css_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update klz_css_{i} "{esc}"', confirm=True)
    wp.cli(f"option update klz_css_parts {len(chunks)}", confirm=True)
    runner = f"""add_action('init', function () {{
    $parts = (int) get_option('klz_css_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('klz_css_' . $i, '');
    if (!$b64) return;
    file_put_contents(ABSPATH . '{CSS_PATH}', base64_decode($b64));
    update_option('klz_cim_css_done', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(SITE + "/").read(8192)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )
    # bump css version
    runner2 = """add_action('init', function () {
    $f = get_stylesheet_directory() . '/functions.php';
    if (!is_file($f)) return;
    $c = file_get_contents($f);
    $n = str_replace("'20260615'", "'20260616'", $c);
    if ($n !== $c) file_put_contents($f, $n);
}, 1);
"""
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner2, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(SITE + "/").read(8192)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )


def fix_layout():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()
    el = wp.load_el(721)
    skyleader = P.find_widget(el, "clc2i")["settings"]["image"]
    patch_cards(el, skyleader)
    deploy_page(wp, 721, el, "klz_cim_layout_fix")
    deploy_css(wp)
    wp.cli("post meta delete 721 _elementor_element_cache", confirm=True)
    wp.cli("post meta delete 721 _elementor_css", confirm=True)
    wp.cli("elementor flush-css --regenerate", confirm=True)
    wp.cli("cache flush", confirm=True)
    print("Layout opraven.")


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    if not os.path.isfile(SKYLEADER_PATH):
        raise SystemExit(f"Chybí soubor: {SKYLEADER_PATH}")
    wp = D.WP()
    wp.login()
    print("1. Nahrávám Skyleader...")
    skyleader = upload_media(
        wp, SKYLEADER_PATH, "Skyleader-GP7-OK-PUA67.jpg",
        "Letoun GP-7 Skyleader OK-PUA 67 na letišti",
    )
    print("   ID", skyleader["id"], skyleader["url"])
    wp.cli(
        'post meta update 499 _wp_attachment_image_alt "Letoun DV-1 Skylark OK-MUA 73 na letišti"',
        confirm=True,
    )
    print("2. Upravuji karty...")
    el = wp.load_el(721)
    patch_cards(el, skyleader)
    deploy_page(wp, 721, el, "klz_cim_cards")
    print("3. CSS karet...")
    deploy_css(wp)
    wp.cli("post meta delete 721 _elementor_element_cache", confirm=True)
    wp.cli("elementor flush-css --regenerate", confirm=True)
    wp.cli("cache flush", confirm=True)
    print("Hotovo.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        fix_layout()
    else:
        main()
