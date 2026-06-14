#!/usr/bin/env python3
"""Oprava mobilní verze stránky O nás (509) — CSS v klz-site.css."""
import base64
import importlib.util
import os
import urllib.request

_spec = importlib.util.spec_from_file_location(
    "d", os.path.join(os.path.dirname(__file__), "deploy-pages-api.py")
)
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

SITE = D.SITE
CSS_PATH = "wp-content/themes/hello-elementor/assets/klz-site.css"
MARKER = "/* KLZ O nás mobil v2 */"
OLD_MARKER = "/* KLZ O nás mobil */"

MOBILE_CSS = """
/* KLZ O nás mobil v2 */
@media (max-width:767px){
  .elementor-509 .e-con[data-id="onhdr001"],
  .elementor-509 .e-con[data-id="onmain01"],
  .elementor-509 .e-con[data-id="onstory1"]{
    width:100%!important;max-width:100%!important;
    padding-left:16px!important;padding-right:16px!important;box-sizing:border-box!important}
  .elementor-509 .e-con[data-id="onmain01"] .e-con-inner,
  .elementor-509 .e-con[data-id="onstory1"] .e-con-inner{
    width:100%!important;max-width:100%!important;padding-left:0!important;padding-right:0!important}
  .elementor-509 .e-con[data-id="onmain01"]{
    flex-direction:column!important;gap:28px!important;align-items:stretch!important}
  .elementor-509 .e-con[data-id="ontxt001"]{
    width:100%!important;max-width:100%!important;flex:1 1 auto!important}
  .elementor-509 .elementor-element-onimg001,
  .elementor-509 [data-id="onimg001"]{
    width:100%!important;max-width:100%!important;align-self:stretch!important}
  .elementor-509 .elementor-element-onimg001 img,
  .elementor-509 [data-id="onimg001"] img{
    width:100%!important;max-width:100%!important;height:auto!important;border-radius:12px!important}
  .elementor-509 .e-con[data-id="onstats1"]{
    display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;
    gap:8px!important;width:100%!important;flex-direction:unset!important}
  .elementor-509 .e-con[data-id="onstats1"]>.e-con{
    width:100%!important;max-width:100%!important;min-width:0!important;flex:none!important;
    padding:12px 8px!important;box-sizing:border-box!important}
  .elementor-509 .e-con[data-id="onstats1"] .elementor-heading-title{
    white-space:normal!important;word-break:break-word!important;hyphens:auto!important}
  .elementor-509 .elementor-element-ons1l .elementor-heading-title,
  .elementor-509 .elementor-element-ons2l .elementor-heading-title,
  .elementor-509 .elementor-element-ons3l .elementor-heading-title{
    font-size:10px!important;line-height:1.25!important}
  .elementor-509 .elementor-element-ons1n .elementor-heading-title,
  .elementor-509 .elementor-element-ons2n .elementor-heading-title,
  .elementor-509 .elementor-element-ons3n .elementor-heading-title{
    font-size:20px!important;line-height:1.1!important}
  .elementor-509 .elementor-element-onp001,
  .elementor-509 .elementor-element-onp002{
    font-size:15px!important;line-height:1.75!important}
  .elementor-509 .elementor-element-onhd002 .elementor-heading-title{
    font-size:clamp(28px,8vw,36px)!important}
  .elementor-509 .elementor-element-onst004 img{width:100%!important;max-width:100%!important}
  .elementor-509 .elementor-element-onst005{width:100%!important;text-align:center!important}
  .elementor-509 .elementor-element-onst005 .elementor-button{
    width:100%!important;max-width:320px!important}
}
@media (max-width:360px){
  .elementor-509 .e-con[data-id="onstats1"]{grid-template-columns:1fr!important;gap:10px!important}
  .elementor-509 .e-con[data-id="onstats1"]>.e-con{padding:14px 16px!important}
}
"""


def patch_css(css: str) -> str:
    import re

    css = re.sub(
        r"\.elementor-509 \.e-con\[data-id=\"onmain01\"\]\{flex-direction:column!important;gap:24px!important;padding-left:16px!important;padding-right:16px!important\}\s*"
        r"\.elementor-509 \.e-con\[data-id=\"ontxt001\"\],\.elementor-509 \[data-id=\"onimg001\"\]\{width:100%!important;max-width:100%!important;flex:none!important\}\s*"
        r"\.elementor-509 \.e-con\[data-id=\"onstats1\"\]\{flex-direction:row!important;flex-wrap:wrap!important;gap:8px!important\}\s*"
        r"\.elementor-509 \.e-con\[data-id=\"onstats1\"\]>\.e-con\{flex:1 1 30%!important;min-width:95px!important\}",
        "",
        css,
    )
    for m in (MARKER, OLD_MARKER):
        if m in css:
            start = css.index(m)
            end = css.find("\n@media", start + 1)
            if end == -1:
                end = css.find("\n/* ", start + len(m))
            if end == -1:
                css = css[:start]
            else:
                css = css[:start] + css[end:]
    return css.rstrip() + "\n\n" + MOBILE_CSS.strip() + "\n"


def deploy_file(wp, path: str, content: str):
    b64 = base64.b64encode(content.encode()).decode()
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
    file_put_contents(ABSPATH . '{path}', base64_decode($b64));
    update_option('klz_onas_mobile_done', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(SITE + "/?pagename=o-nas").read(8192)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )


def bump_css_version(wp):
    runner = """add_action('init', function () {
    $f = get_stylesheet_directory() . '/functions.php';
    if (!is_file($f)) return;
    $c = file_get_contents($f);
    $n = str_replace("'20260613'", "'20260614'", $c);
    if ($n !== $c) file_put_contents($f, $n);
}, 1);
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


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()
    css = urllib.request.urlopen(
        f"{SITE}/wp-content/themes/hello-elementor/assets/klz-site.css?ver=20260613"
    ).read().decode("utf-8", "replace")
    css = patch_css(css)
    deploy_file(wp, CSS_PATH, css)
    bump_css_version(wp)
    wp.cli("post meta delete 509 _elementor_element_cache", confirm=True)
    wp.cli("cache flush", confirm=True)
    print("O nás mobil hotovo.")


if __name__ == "__main__":
    main()
