#!/usr/bin/env python3
"""Odstranění sekcí: úvod aktuality, O nás flota + výcvik."""
import base64
import importlib.util
import json
import os

_spec = importlib.util.spec_from_file_location(
    "d", os.path.join(os.path.dirname(__file__), "deploy-pages-api.py")
)
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

SITE = D.SITE

REMOVE = {
    517: {"aktual01"},
    509: {"onfleet1", "ontrain1"},
}


def strip_sections(elements, remove_ids):
    return [el for el in elements if el.get("id") not in remove_ids]


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
    slugs = {517: "", 509: "o-nas"}
    url = f"{SITE}/" if pid == 517 else f"{SITE}/?pagename={slugs[pid]}"
    wp.op.open(url).read(16384)
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

    for pid, remove_ids in REMOVE.items():
        label = "úvod" if pid == 517 else "O nás"
        print(f"{label} ({pid}) — odstraňuji: {', '.join(sorted(remove_ids))}")
        el = wp.load_el(pid)
        new_el = strip_sections(el, remove_ids)
        if len(new_el) == len(el):
            print("   varování: žádná sekce neodstraněna")
        deploy_elementor_page(wp, pid, new_el, f"klz_rm{pid}_done")
        print("   hotovo:", wp.cli(f"option get klz_rm{pid}_done").get("stdout"))

    wp.cli("option update wp_cache_enabled 0", confirm=True)
    for pid in REMOVE:
        wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
    wp.purge_cache()
    wp.cli("cache flush", confirm=True)
    print("Deploy dokončen.")


if __name__ == "__main__":
    main()
