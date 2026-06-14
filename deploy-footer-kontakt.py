#!/usr/bin/env python3
"""Obnovení patičky, kontaktního formuláře a mapy."""
import base64
import importlib.util
import json
import os

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

CONTACT_FORM_HTML = """<form id="klz-contact-form" class="klz-contact-form" method="post" novalidate>
  <div class="klz-field">
    <label for="klz-name">Jméno</label>
    <input type="text" id="klz-name" name="name" required autocomplete="name">
  </div>
  <div class="klz-field">
    <label for="klz-email">E-mail</label>
    <input type="email" id="klz-email" name="email" required autocomplete="email">
  </div>
  <div class="klz-field">
    <label for="klz-message">Zpráva</label>
    <textarea id="klz-message" name="message" rows="5" required></textarea>
  </div>
  <button type="submit">Odeslat zprávu</button>
  <p class="klz-form-msg" aria-live="polite"></p>
</form>"""

MAP_HTML = """<div class="klz-map-wrap" style="margin-top:24px;width:100%;border-radius:8px;overflow:hidden;border:1px solid #e8eef5;line-height:0;">
<iframe title="Mapa letiště LKZA Zábřeh" width="100%" height="300" style="border:0;display:block;"
src="https://www.openstreetmap.org/export/embed.html?bbox=17.862%2C49.898%2C17.892%2C49.920&amp;layer=mapnik&amp;marker=49.909%2C17.877"
loading="lazy"></iframe>
</div>
<p style="margin:10px 0 0;font-size:13px;color:#666;text-align:center;">
<a href="https://www.google.com/maps/search/?api=1&amp;query=Leti%C5%A1t%C4%9B+Z%C3%A1b%C5%99eh+LKZA" target="_blank" rel="noopener noreferrer" style="color:#1a73e8;">Otevřít v Google Maps</a>
</p>"""

SUBTITLE_HTML = (
    '<p style="text-align:center;color:#b80000;font-size:12px;font-weight:700;'
    'letter-spacing:2px;text-transform:uppercase;margin:12px 0 0;">Jsme tu pro vás</p>'
)

NAV_SNIPPET = r"""add_action('wp_loaded', function () {
    for ($p = 1; $p <= 100; $p++) {
        remove_action('wp_body_open', 'klz_nav', $p);
    }
}, 9999);

add_action('wp_body_open', 'klz_nav_v3', 5);
function klz_nav_v3() {
    static $done = false;
    if ($done) {
        return;
    }
    $done = true;
    $logo = 'https://it2529.sspu-opava.eu/wp-content/uploads/2026/06/logo-klz-1.png';
    $current_id = (int) get_queried_object_id();
    $pages = array(517, 509, 721, 436, 639, 440);
    $labels = array(
        517 => 'Úvod',
        509 => 'O nás',
        721 => 'Čím létáme',
        436 => 'Služby',
        639 => 'Galerie',
        440 => 'Kontakt',
    );
    echo '<nav id="klz-nav" class="klz-nav" role="navigation" aria-label="Hlavni navigace">';
    echo '<div class="klz-inner">';
    echo '<a href="' . esc_url(home_url('/')) . '" class="klz-logo" aria-label="Klub létání Zábřeh - Domů">';
    echo '<img src="' . esc_url($logo) . '" alt="Klub létání Zábřeh" width="160" height="44"></a>';
    echo '<button id="klz-burger" type="button" aria-label="Otevřít menu" aria-expanded="false" ';
    echo 'onclick="var m=document.querySelector(\'#klz-nav .klz-links\');var b=this;';
    echo 'm.classList.toggle(\'open\');b.classList.toggle(\'open\');';
    echo 'b.setAttribute(\'aria-expanded\',m.classList.contains(\'open\'))">';
    echo '<span></span><span></span><span></span></button>';
    echo '<ul class="klz-links">';
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


def patch_kontakt_full(elements):
    P.patch_kontakt(elements)
    P.find_widget(elements, "ea333333")["settings"]["editor"] = SUBTITLE_HTML
    P.find_widget(elements, "ec222222")["settings"]["html"] = CONTACT_FORM_HTML
    P.find_widget(elements, "eb999999")["settings"]["editor"] = P.CONTACT_EDITOR
    P.find_widget(elements, "ec111111")["settings"]["html"] = MAP_HTML
    icons = P.find_widget(elements, "eb333334")
    icons["settings"]["icon_list"] = [
        {
            "_id": "ic1",
            "text": "klub@letani-zabreh.cz",
            "selected_icon": {"value": "fas fa-envelope", "library": "fa-solid"},
            "link": {"url": "mailto:klub@letani-zabreh.cz"},
        },
        {
            "_id": "ic2",
            "text": "+420 737 871 590",
            "selected_icon": {"value": "fas fa-phone", "library": "fa-solid"},
            "link": {"url": "tel:+420737871590"},
        },
        {
            "_id": "ic3",
            "text": "LKZA Zábřeh, Dolní Benešov",
            "selected_icon": {"value": "fas fa-map-marker-alt", "library": "fa-solid"},
            "link": {"url": "https://www.google.com/maps/search/?api=1&query=Leti%C5%A1t%C4%9B+Z%C3%A1b%C5%99eh+LKZA", "is_external": "on"},
        },
        {
            "_id": "ic4",
            "text": "letani-zabreh.cz",
            "selected_icon": {"value": "fas fa-globe", "library": "fa-solid"},
            "link": {"url": "https://letani-zabreh.cz", "is_external": "on"},
        },
        {
            "_id": "ic5",
            "text": "@klub_letani_zabreh",
            "selected_icon": {"value": "fab fa-instagram", "library": "fa-brands"},
            "link": {
                "url": "https://www.instagram.com/klub_letani_zabreh/",
                "is_external": "on",
            },
        },
    ]


def deploy_elementor_page(wp, pid, elements, done_key):
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = f"klz_el{pid}"
    wp.cli(f"option delete {prefix}_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update {prefix}_{i} "{esc}"', confirm=True)
    wp.cli(f"option update {prefix}_parts {len(chunks)}", confirm=True)
    wp.cli(f"option delete {done_key}", confirm=True)
    runner = f"""add_action('init', function () {{
    if (get_option('{done_key}')) return;
    $parts = (int) get_option('{prefix}_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('{prefix}_' . $i, '');
    if (!$b64) return;
    $data = json_decode(base64_decode($b64), true);
    if (!is_array($data)) return;
    update_post_meta({pid}, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta({pid}, '_elementor_element_cache');
    update_post_meta({pid}, '_elementor_edit_mode', 'builder');
    update_option('{done_key}', 1);
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig6 = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/?pagename=kontakt").read(16384)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()

    print("1. Navigace — snippet bez náhrady patičky...")
    s8 = wp.rest("GET", "/code-snippets/v1/snippets/8")
    payload = {
        "id": 8,
        "code": NAV_SNIPPET,
        "active": True,
        "name": "KLZ navigace + Čím létáme",
        "scope": "global",
        "priority": 0,
        "desc": s8.get("desc") or "",
        "tags": s8.get("tags") or [],
    }
    r = wp.rest("PUT", "/code-snippets/v1/snippets/8", payload)
    if not r.get("active"):
        r = wp.rest("PUT", "/code-snippets/v1/snippets/8", {**payload, "active": True})
    print("   snippet 8:", r.get("active"), r.get("code_error"))

    print("2. Kontakt (440) — formulář, adresa, mapa...")
    el440 = wp.load_el(440)
    patch_kontakt_full(el440)
    deploy_elementor_page(wp, 440, el440, "klz_el440_done")
    print("   el440 done:", wp.cli("option get klz_el440_done").get("stdout"))

    wp.cli("option update wp_cache_enabled 0", confirm=True)
    for pid in [440, 517, 509, 721, 436, 639]:
        wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
    wp.purge_cache()
    wp.cli("cache flush", confirm=True)
    print("Hotovo.")


if __name__ == "__main__":
    main()
