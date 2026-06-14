#!/usr/bin/env python3
"""Přidá fotku Skylark na stránku Čím létáme (721)."""
import base64
import importlib.util
import json
import os

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


def skylark_image_widget():
    return {
        "id": "clc1i",
        "elType": "widget",
        "widgetType": "image",
        "settings": {
            "image": SKYLARK,
            "image_size": "full",
            "align": "center",
            "image_alt": "Letoun DV-1 Skylark OK-MUA 73 na letišti",
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


def patch_cim_skylark(elements):
    card = P.find_widget(elements, "clc1")
    if not card:
        raise SystemExit("Karta clc1 nenalezena")
    kids = card.setdefault("elements", [])
    if P.find_widget(elements, "clc1i"):
        img = P.find_widget(elements, "clc1i")
        img["settings"]["image"] = SKYLARK
        img["settings"]["image_alt"] = "Letoun DV-1 Skylark OK-MUA 73 na letišti"
        return
    kids.insert(0, skylark_image_widget())


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


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()
    wp.cli(
        'post meta update 499 _wp_attachment_image_alt "Letoun DV-1 Skylark OK-MUA 73 na letišti"',
        confirm=True,
    )
    el = wp.load_el(721)
    patch_cim_skylark(el)
    deploy_page(wp, 721, el, "klz_cim_skylark_img")
    wp.cli("post meta delete 721 _elementor_element_cache", confirm=True)
    wp.cli("elementor flush-css --regenerate", confirm=True)
    wp.cli("cache flush", confirm=True)
    print("Skylark fotka nasazena.")


if __name__ == "__main__":
    main()
