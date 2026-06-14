#!/usr/bin/env python3
"""Oprava zarovnání tlačítka Mám zájem na Službách (436)."""
import base64
import importlib.util
import json
import os
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
CSS_PATH = "wp-content/themes/hello-elementor/assets/klz-site.css"
MARKER = "/* KLZ Služby tlačítka fix */"

BTN_FIX = """
/* KLZ Služby tlačítka fix */
.elementor-436 .e-con[data-id="scvyc01"]{
  align-items:center!important;text-align:center!important;
  display:flex!important;flex-direction:column!important}
.elementor-436 .e-con[data-id="scvyc01"] .elementor-widget-heading .elementor-heading-title,
.elementor-436 .e-con[data-id="scvyc01"] .elementor-widget-text-editor{text-align:center!important;width:100%!important}
.elementor-436 .e-con[data-id="scvyc01"] .elementor-widget-text-editor p{text-align:center!important;color:#555!important}
.elementor-436 .e-con[data-id="scvyc01"] ul{display:inline-block!important;text-align:left!important;margin:16px auto 0!important;padding-left:1.1em!important}
.elementor-436 .e-con[data-id="scvyc01"] .elementor-widget-button{
  width:100%!important;margin-top:auto!important;padding-top:20px!important;
  display:flex!important;justify-content:center!important}
.elementor-436 .e-con[data-id="scvyc01"] .elementor-button-wrapper{
  margin:0!important;display:flex!important;justify-content:center!important;width:100%!important}
.page-id-436 .e-con[data-id="scvyc01"] .elementor-widget-button{
  margin-top:auto!important;width:100%!important;display:flex!important;justify-content:center!important}
.page-id-436 .e-con[data-id="scvyc01"] .elementor-button-wrapper{
  display:flex!important;justify-content:center!important;width:100%!important}
"""


def patch_elementor(elements):
    for wid in ["sa999999", "sb555555", "sc444444", "scvyc05"]:
        btn = P.find_widget(elements, wid)
        btn["settings"]["align"] = "center"


def deploy_css(wp):
    css = urllib.request.urlopen(
        f"{SITE}/wp-content/themes/hello-elementor/assets/klz-site.css?ver=20260616"
    ).read().decode("utf-8", "replace")
    if MARKER in css:
        start = css.index(MARKER)
        end = css.find("\n/* ", start + len(MARKER))
        css = css[:start] + (css[end:] if end != -1 else "")
    # also extend existing rule if scvyc01 missing from SLUZBY block
    css = css.replace(
        '.elementor-436 .e-con[data-id="sc111111"]{align-items:center!important;text-align:center!important}',
        '.elementor-436 .e-con[data-id="sc111111"],.elementor-436 .e-con[data-id="scvyc01"]{align-items:center!important;text-align:center!important}',
    )
    css = css.replace(
        '.elementor-436 .e-con[data-id="sc111111"] .elementor-widget-button{width:100%!important;margin-top:auto!important;padding-top:20px!important;display:flex!important;justify-content:center!important}',
        '.elementor-436 .e-con[data-id="sc111111"] .elementor-widget-button,.elementor-436 .e-con[data-id="scvyc01"] .elementor-widget-button{width:100%!important;margin-top:auto!important;padding-top:20px!important;display:flex!important;justify-content:center!important}',
    )
    css = css.replace(
        '.elementor-436 .e-con[data-id="sc111111"] .elementor-button-wrapper{margin:0!important;display:flex!important;justify-content:center!important;width:100%!important}',
        '.elementor-436 .e-con[data-id="sc111111"] .elementor-button-wrapper,.elementor-436 .e-con[data-id="scvyc01"] .elementor-button-wrapper{margin:0!important;display:flex!important;justify-content:center!important;width:100%!important}',
    )
    css = css.rstrip() + "\n\n" + BTN_FIX.strip() + "\n"
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
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest("PUT", "/code-snippets/v1/snippets/6", {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1})
    wp.op.open(SITE + "/").read(8192)
    wp.rest("PUT", "/code-snippets/v1/snippets/6", {"code": orig, "active": False, "name": s6["name"], "scope": "global"})
    runner2 = """add_action('init', function () {
    $f = get_stylesheet_directory() . '/functions.php';
    if (!is_file($f)) return;
    $c = file_get_contents($f);
    $n = str_replace("'20260616'", "'20260617'", $c);
    if ($n !== $c) file_put_contents($f, $n);
}, 1);
"""
    wp.rest("PUT", "/code-snippets/v1/snippets/6", {"code": runner2, "active": True, "name": s6["name"], "scope": "global", "priority": 1})
    wp.op.open(SITE + "/").read(8192)
    wp.rest("PUT", "/code-snippets/v1/snippets/6", {"code": orig, "active": False, "name": s6["name"], "scope": "global"})


def deploy_page(wp, elements):
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = "klz_el436"
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
    update_post_meta(436, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta(436, '_elementor_element_cache');
    delete_post_meta(436, '_elementor_css');
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest("PUT", "/code-snippets/v1/snippets/6", {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1})
    wp.op.open(f"{SITE}/?pagename=sluzby").read(32768)
    wp.rest("PUT", "/code-snippets/v1/snippets/6", {"code": orig, "active": False, "name": s6["name"], "scope": "global"})


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()
    el = wp.load_el(436)
    patch_elementor(el)
    deploy_page(wp, el)
    deploy_css(wp)
    wp.cli("cache flush", confirm=True)
    print("Tlačítko opraveno.")


if __name__ == "__main__":
    main()
