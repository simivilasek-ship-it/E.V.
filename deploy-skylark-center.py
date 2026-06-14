#!/usr/bin/env python3
"""Vycentrování letadla Skylark v rámečku karty (object-position)."""
import base64
import importlib.util
import os
import re
import urllib.request

_spec = importlib.util.spec_from_file_location(
    "d", os.path.join(os.path.dirname(__file__), "deploy-pages-api.py")
)
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

SITE = D.SITE
CSS_PATH = "wp-content/themes/hello-elementor/assets/klz-site.css"
MARKER = "/* KLZ Skylark center v1 */"
RULE = """
/* KLZ Skylark center v1 */
.elementor-721 .e-con[data-id="clc1"] .elementor-widget-image img,
.elementor-721 .elementor-element-clc1i img {
  object-position: 68% 58% !important;
}
@media (max-width: 767px) {
  .elementor-721 .e-con[data-id="clc1"] .elementor-widget-image img,
  .elementor-721 .elementor-element-clc1i img {
    object-position: 66% 56% !important;
  }
}
"""


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()

    css = urllib.request.urlopen(f"{SITE}/wp-content/themes/hello-elementor/assets/klz-site.css").read().decode(
        "utf-8", "replace"
    )
    if MARKER in css:
        start = css.index(MARKER)
        end = css.find("\n/* ", start + len(MARKER))
        css = css[:start] + (css[end + 1 :] if end != -1 else "")
    css = css.rstrip() + "\n" + RULE.strip() + "\n"

    b64 = base64.b64encode(css.encode()).decode()
    wp.cli("option delete klz_css_skylark_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update klz_css_skylark_{i} "{esc}"', confirm=True)
    wp.cli(f"option update klz_css_skylark_parts {len(chunks)}", confirm=True)

    runner = f"""add_action('init', function () {{
    $parts = (int) get_option('klz_css_skylark_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('klz_css_skylark_' . $i, '');
    if (!$b64) return;
    file_put_contents(ABSPATH . '{CSS_PATH}', base64_decode($b64));
    update_option('klz_skylark_center_done', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/?pagename=cim-letame").read(8192)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )

    ver_runner = """add_action('init', function () {
    $f = get_stylesheet_directory() . '/functions.php';
    if (!is_file($f)) return;
    $c = file_get_contents($f);
    $c = preg_replace("/'klz-site\\.css',\\s*array\\(\\),\\s*'\\d+'/", "'klz-site.css', array(), '20260618'", $c);
    $c = preg_replace("/\\?ver=\\d+'/", "?ver=20260618'", $c, 1);
    file_put_contents($f, $c);
}, 1);
"""
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": ver_runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/").read(8192)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )

    wp.cli("post meta delete 721 _elementor_element_cache", confirm=True)
    wp.cli("cache flush", confirm=True)
    wp.purge_cache()
    print("Skylark object-position nasazeno (68% 58%).")


if __name__ == "__main__":
    main()
