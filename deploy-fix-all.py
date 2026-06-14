#!/usr/bin/env python3
"""Trvalá oprava patičky + flush cache + re-deploy stránek."""
import base64
import importlib.util
import json
import os
import re
import urllib.parse
import urllib.request

_spec = importlib.util.spec_from_file_location(
    "p", os.path.join(os.path.dirname(__file__), "deploy-content-updates.py")
)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

_spec2 = importlib.util.spec_from_file_location(
    "d", os.path.join(os.path.dirname(__file__), "deploy-pages-api.py")
)
D = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(D)

SITE = D.SITE

# Import contact patches from deploy-footer-kontakt
_spec3 = importlib.util.spec_from_file_location(
    "f", os.path.join(os.path.dirname(__file__), "deploy-footer-kontakt.py")
)
F = importlib.util.module_from_spec(_spec3)
_spec3.loader.exec_module(F)

FOOTER_SNIPPET = r"""add_action('wp_loaded', function () {
    for ($p = 1; $p <= 100; $p++) {
        remove_action('wp_body_open', 'klz_nav', $p);
        remove_action('wp_footer', 'klz_footer_v3', $p);
    }
}, 9999);

add_action('wp_body_open', 'klz_nav_v3', 5);
function klz_nav_v3() {
    static $done = false;
    if ($done) return;
    $done = true;
    $logo = 'https://it2529.sspu-opava.eu/wp-content/uploads/2026/06/logo-klz-1.png';
    $current_id = (int) get_queried_object_id();
    $pages = array(517, 509, 721, 436, 639, 440);
    $labels = array(
        517 => 'Úvod', 509 => 'O nás', 721 => 'Čím létáme',
        436 => 'Služby', 639 => 'Galerie', 440 => 'Kontakt',
    );
    echo '<nav id="klz-nav" class="klz-nav" role="navigation" aria-label="Hlavni navigace">';
    echo '<div class="klz-inner">';
    echo '<a href="' . esc_url(home_url('/')) . '" class="klz-logo" aria-label="Klub létání Zábřeh - Domů">';
    echo '<img src="' . esc_url($logo) . '" alt="Klub létání Zábřeh" width="160" height="44"></a>';
    echo '<button id="klz-burger" type="button" aria-label="Otevřít menu" aria-expanded="false" ';
    echo 'onclick="var m=document.querySelector(\'#klz-nav .klz-links\');var b=this;';
    echo 'm.classList.toggle(\'open\');b.classList.toggle(\'open\');';
    echo 'b.setAttribute(\'aria-expanded\',m.classList.contains(\'open\'))">';
    echo '<span></span><span></span><span></span></button><ul class="klz-links">';
    foreach ($pages as $pid) {
        $slug = get_post_field('post_name', $pid);
        $url = ($pid === 517) ? home_url('/') : home_url('/?pagename=' . $slug);
        $active = ($current_id === (int) $pid) ? ' class="active"' : '';
        echo '<li' . $active . '><a href="' . esc_url($url) . '">';
        echo esc_html($labels[$pid]) . '</a></li>';
    }
    echo '</ul></div></nav>';
}
"""

REMOVE = {517: {"aktual01"}, 509: {"onfleet1", "ontrain1"}}


def strip_sections(elements, remove_ids):
    return [el for el in elements if el.get("id") not in remove_ids]


def deploy_elementor_page(wp, pid, elements, done_key):
    wp.cli(f"option delete {done_key}", confirm=True)
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = f"klz_el{pid}"
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
    update_post_meta({pid}, '_elementor_edit_mode', 'builder');
    update_option('{done_key}', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig6 = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    urls = {517: f"{SITE}/", 509: f"{SITE}/?pagename=o-nas", 440: f"{SITE}/?pagename=kontakt"}
    wp.op.open(urls[pid]).read(32768)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )


def purge_all_cache(wp):
    for opt in ["wp_cache_enabled", "super_cache_enabled", "cache_compression", "wp_super_cache_late_init"]:
        wp.cli(f"option update {opt} 0", confirm=True)
    wp.cli("cache flush", confirm=True)
    wp.cli("elementor flush-css --regenerate", confirm=True)
    for pid in [517, 509, 440, 436, 639, 721]:
        wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
        wp.cli(f"post update {pid} --post_modified=now", confirm=True)
    wp.purge_cache()
    html = wp.op.open(
        f"{SITE}/wp-admin/options-general.php?page=wpsupercache&tab=contents"
    ).read().decode("utf-8", "replace")
    m = re.search(r'name="_wpnonce" value="([^"]+)"', html)
    if m:
        post = urllib.parse.urlencode(
            {
                "wp_delete_cache": "1",
                "_wpnonce": m.group(1),
                "_wp_http_referer": "/wp-admin/options-general.php?page=wpsupercache&tab=contents",
                "action": "delete",
            }
        ).encode()
        wp.op.open(
            urllib.request.Request(
                f"{SITE}/wp-admin/options-general.php?page=wpsupercache&tab=contents",
                data=post,
                method="POST",
            )
        )


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()

    print("1. Snippet 8 — navigace (bez náhrady patičky)...")
    s8 = wp.rest("GET", "/code-snippets/v1/snippets/8")
    payload = {
        "id": 8,
        "code": FOOTER_SNIPPET,
        "active": True,
        "name": "KLZ navigace + patička fix",
        "scope": "global",
        "priority": 0,
        "desc": s8.get("desc") or "",
        "tags": s8.get("tags") or [],
    }
    r = wp.rest("PUT", "/code-snippets/v1/snippets/8", payload)
    if not r.get("active"):
        r = wp.rest("PUT", "/code-snippets/v1/snippets/8", {**payload, "active": True})
    print("   active:", r.get("active"))

    print("2. Úvod 517 — bez aktualit...")
    el517 = strip_sections(wp.load_el(517), REMOVE[517])
    deploy_elementor_page(wp, 517, el517, "klz_fix517")

    print("3. O nás 509 — bez floty a výcviku...")
    el509 = strip_sections(wp.load_el(509), REMOVE[509])
    deploy_elementor_page(wp, 509, el509, "klz_fix509")

    print("4. Kontakt 440 — formulář + mapa...")
    el440 = wp.load_el(440)
    F.patch_kontakt_full(el440)
    deploy_elementor_page(wp, 440, el440, "klz_fix440")

    print("5. Cache flush...")
    purge_all_cache(wp)

    for url in [f"{SITE}/", f"{SITE}/?pagename=kontakt", f"{SITE}/?pagename=o-nas"]:
        wp.op.open(f"{url}&klzfix=1").read(8192)
    print("Hotovo.")


if __name__ == "__main__":
    main()
