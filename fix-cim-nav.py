#!/usr/bin/env python3
"""Oprava navigace (721) v functions.php + úklid stránky Čím létáme."""
import base64
import copy
import importlib.util
import json
import os
import urllib.request

SITE = "https://it2529.sspu-opava.eu"
PWD = os.environ.get("WP_PASS", "")

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


def cim_page_clean():
    """Jedna sekce — bez duplicitního nadpisu FLOTA / Čím létáme."""
    card = lambda cid, title, desc, image=None: {
        "id": cid,
        "elType": "container",
        "settings": {
            "flex_direction": "column",
            "width": {"unit": "%", "size": 48},
            "width_mobile": {"unit": "%", "size": 100},
            "background_background": "classic",
            "background_color": "#ffffff",
            "border_border": "solid",
            "border_width": {"unit": "px", "top": 1, "right": 1, "bottom": 1, "left": 1, "isLinked": True},
            "border_color": "#e8eef5",
            "border_radius": {"unit": "px", "top": 12, "right": 12, "bottom": 12, "left": 12, "isLinked": True},
            "padding": {"unit": "px", "top": 28, "right": 24, "bottom": 28, "left": 24, "isLinked": True},
        },
        "elements": ([
            {
                "id": cid + "i",
                "elType": "widget",
                "widgetType": "image",
                "settings": {
                    "image": image,
                    "image_size": "full",
                    "align": "center",
                    "image_alt": f"Letoun {title}",
                    "image_border_radius": {
                        "unit": "px",
                        "top": 12,
                        "right": 12,
                        "bottom": 12,
                        "left": 12,
                        "isLinked": True,
                    },
                    "width": {"unit": "%", "size": 100},
                    "width_mobile": {"unit": "%", "size": 100},
                },
                "elements": [],
            }
        ] if image else [])
        + [
            {
                "id": cid + "h",
                "elType": "widget",
                "settings": {
                    "title": title,
                    "header_size": "h3",
                    "title_color": "#111827",
                    "typography_font_weight": "700",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": cid + "t",
                "elType": "widget",
                "settings": {"editor": desc},
                "elements": [],
                "widgetType": "text-editor",
            },
        ],
        "isInner": True,
    }
    return [
        {
            "id": "clmain01",
            "elType": "container",
            "settings": {
                "flex_direction": "column",
                "content_width": "boxed",
                "boxed_width": {"unit": "px", "size": 1100},
                "padding": {"unit": "px", "top": 64, "right": 48, "bottom": 48, "left": 48, "isLinked": False},
                "padding_mobile": {"unit": "px", "top": 40, "right": 24, "bottom": 32, "left": 24, "isLinked": False},
                "flex_align_items": "center",
            },
            "elements": [
                {
                    "id": "clmain02",
                    "elType": "widget",
                    "settings": {
                        "title": "Čím létáme",
                        "header_size": "h1",
                        "align": "center",
                        "title_color": "#0f0f0f",
                        "typography_font_size": {"unit": "px", "size": 40},
                        "typography_font_weight": "800",
                    },
                    "elements": [],
                    "widgetType": "heading",
                },
                {
                    "id": "clmain03",
                    "elType": "widget",
                    "settings": {
                        "editor": (
                            '<p style="text-align:center;color:#555;font-size:18px;line-height:1.75;'
                            'max-width:720px;margin:16px auto 40px;">'
                            "Na letišti LKZA Zábřeh provozujeme dvě ultralehká letadla pro výcvik ULL "
                            "i vyhlídkové lety.</p>"
                        )
                    },
                    "elements": [],
                    "widgetType": "text-editor",
                },
                {
                    "id": "clmain04",
                    "elType": "container",
                    "settings": {
                        "flex_direction": "row",
                        "flex_wrap": "wrap",
                        "gap": {"unit": "px", "size": 24},
                        "flex_justify_content": "center",
                        "content_width": "full",
                    },
                    "elements": [
                        card(
                            "clc1",
                            "DV-1 SKYLARK",
                            '<p style="color:#555;font-size:16px;line-height:1.75;margin:0;">'
                            "Ultralehký dvoumístný <strong>dolnoplošník</strong>. Stabilní let, "
                            "vhodný pro výcvik ULL i vyhlídkové prolety.</p>",
                            image={
                                "url": f"{SITE}/wp-content/uploads/2026/06/Skylark-2019.jpg",
                                "id": 499,
                                "source": "library",
                            },
                        ),
                        card(
                            "clc2",
                            "GP-7 SKYLEADER",
                            '<p style="color:#555;font-size:16px;line-height:1.75;margin:0;">'
                            "Ultralehký dvoumístný <strong>hornoplošník</strong>. Moderní kokpit "
                            "a pohodlná sedadla pro instruktora a žáka.</p>",
                        ),
                    ],
                    "isInner": True,
                },
                {
                    "id": "clmain05",
                    "elType": "widget",
                    "settings": {
                        "editor": (
                            '<p style="text-align:center;color:#555;font-size:16px;margin:40px 0 16px;">'
                            "Máte zájem o výcvik nebo prolet?</p>"
                        )
                    },
                    "elements": [],
                    "widgetType": "text-editor",
                },
                {
                    "id": "clmain06",
                    "elType": "widget",
                    "settings": {
                        "text": "Kontaktujte nás",
                        "link": {"url": f"{SITE}/?pagename=kontakt"},
                        "size": "md",
                        "background_color": "#b80000",
                        "button_text_color": "#ffffff",
                        "border_radius": {
                            "unit": "px",
                            "top": 100,
                            "right": 100,
                            "bottom": 100,
                            "left": 100,
                            "isLinked": True,
                        },
                        "align": "center",
                    },
                    "elements": [],
                    "widgetType": "button",
                },
            ],
            "isInner": False,
        }
    ]


NAV_SNIPPET = r"""add_action('wp_loaded', function () {
    remove_action('wp_body_open', 'klz_nav');
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

FUNC_PATCH = r"""add_action('init', function () {
    if (get_option('klz_func_nav721_done')) {
        return;
    }
    $path = get_stylesheet_directory() . '/functions.php';
    if (!is_readable($path) || !is_writable($path)) {
        return;
    }
    $c = file_get_contents($path);
    if (strpos($c, '721') !== false && strpos($c, 'Čím létáme') !== false) {
        update_option('klz_func_nav721_done', 1);
        return;
    }
    $replacements = array(
        '$pages = array( 517, 509, 436, 639, 440 );' => '$pages = array( 517, 509, 721, 436, 639, 440 );',
        '$pages = array(517, 509, 436, 639, 440);' => '$pages = array(517, 509, 721, 436, 639, 440);',
        "509 => 'O nás', 436 => 'Služby'" => "509 => 'O nás', 721 => 'Čím létáme', 436 => 'Služby'",
        '509 => \'O nás\', 436 => \'Služby\'' => '509 => \'O nás\', 721 => \'Čím létáme\', 436 => \'Služby\'',
    );
    foreach ($replacements as $from => $to) {
        if (strpos($c, $from) !== false) {
            $c = str_replace($from, $to, $c);
        }
    }
    file_put_contents($path, $c);
    update_option('klz_func_nav721_done', 1);
}, 1);
"""


def deploy_elementor_page(wp, pid, elements):
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = f"klz_el{pid}"
    wp.cli(f"option delete {prefix}_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update {prefix}_{i} "{esc}"', confirm=True)
    wp.cli(f"option update {prefix}_parts {len(chunks)}", confirm=True)
    wp.cli("option delete klz_cim_el_done", confirm=True)
    runner = f"""add_action('init', function () {{
    if (get_option('klz_cim_el_done')) return;
    $parts = (int) get_option('{prefix}_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('{prefix}_' . $i, '');
    if (!$b64) return;
    $data = json_decode(base64_decode($b64), true);
    if (!is_array($data)) return;
    update_post_meta({pid}, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta({pid}, '_elementor_element_cache');
    update_post_meta({pid}, '_elementor_edit_mode', 'builder');
    update_post_meta({pid}, '_wp_page_template', 'default');
    update_option('klz_cim_el_done', 1);
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig6 = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/?pagename=cim-letame").read(16384)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()

    pid = 721
    print("1. Úklid stránky Čím létáme (ID 721)...")
    deploy_elementor_page(wp, pid, cim_page_clean())

    print("2. Navigace — snippet v3 (nahradí klz_nav)...")
    s8 = wp.rest("GET", "/code-snippets/v1/snippets/8")
    r = wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/8",
        {
            "id": 8,
            "code": NAV_SNIPPET,
            "active": True,
            "name": "KLZ navigace + Čím létáme",
            "scope": "global",
            "priority": 0,
            "desc": s8.get("desc") or "",
            "tags": s8.get("tags") or [],
        },
    )
    print("   snippet 8 active:", r.get("active"), r.get("code_error"))

    print("3. Patch functions.php ( záloha)...")
    wp.cli("option delete klz_func_nav721_done", confirm=True)
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig6 = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": FUNC_PATCH, "active": True, "name": s6["name"], "scope": "global", "priority": 2},
    )
    wp.op.open(f"{SITE}/").read(4096)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )
    print("   func patch done:", wp.cli("option get klz_func_nav721_done").get("stdout"))

    wp.cli("option update wp_cache_enabled 0", confirm=True)
    for p in [517, 509, 721, 436, 639, 440]:
        wp.cli(f"post update {p} --post_modified=now", confirm=True)
        wp.cli(f"post meta delete {p} _elementor_element_cache", confirm=True)
    wp.purge_cache()
    wp.cli("cache flush", confirm=True)
    print("Hotovo.")


if __name__ == "__main__":
    main()
