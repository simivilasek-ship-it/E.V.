#!/usr/bin/env python3
"""Dokončení: alt texty úvodních fotek + oprava snippet filtru pro prázdné alt=""."""
import base64
import importlib.util
import json
import os
import re

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

MEDIA_ALTS = {
    486: "Členové klubu létání Zábřeh na letišti LKZA",
    474: "Vyhlídkový let nad Moravou — služba klubu Zábřeh",
    481: "Výcvik pilota ULL na letišti LKZA Zábřeh",
    469: "Hangár a provoz klubu létání Zábřeh",
    454: "Letadlo připravené k odletu z LKZA Zábřeh",
    84: "Vyhlídkový let — pohled na krajinu z výšky",
    479: "Start letounu z dráhy letiště Zábřeh",
}

WIDGET_ALTS = {
    "about002": MEDIA_ALTS[486],
    "svcimg01": MEDIA_ALTS[474],
    "svcimg02": MEDIA_ALTS[481],
    "gi00002": MEDIA_ALTS[469],
    "gi00001": MEDIA_ALTS[454],
    "gi00004": MEDIA_ALTS[84],
    "gi00003": MEDIA_ALTS[479],
}

SNIPPET5_ALT_FILTER = r"""add_filter( 'elementor/widget/render_content', function ( $content, $widget ) {
	if ( empty( $content ) || false === stripos( $content, '<img' ) ) {
		return $content;
	}
	return preg_replace_callback( '/<img\b([^>]*?)>/i', function ( $m ) {
		$tag   = $m[0];
		$alt_v = '';
		if ( preg_match( '/\balt\s*=\s*(["\'])(.*?)\1/i', $tag, $alt ) ) {
			$alt_v = trim( $alt[2] );
			if ( $alt_v !== '' ) {
				return $tag;
			}
		}
		$new_alt = '';
		if ( preg_match( '/wp-image-(\d+)/i', $tag, $id ) ) {
			$new_alt = (string) get_post_meta( (int) $id[1], '_wp_attachment_image_alt', true );
		}
		if ( $new_alt === '' && preg_match( '/\/([^\/]+)\.(jpe?g|png|webp)/i', $tag, $fn ) ) {
			$new_alt = klz_alt_from_filename( preg_replace( '/-\d+x\d+(\.[a-z]+)$/i', '$1', $fn[1] ) );
		}
		if ( $new_alt === '' ) {
			$new_alt = 'Letiště LKZA Zábřeh';
		}
		if ( preg_match( '/\balt\s*=\s*(["\']).*?\1/i', $tag ) ) {
			return preg_replace( '/\balt\s*=\s*(["\']).*?\1/i', 'alt="' . esc_attr( $new_alt ) . '"', $tag, 1 );
		}
		return preg_replace( '/<img/i', '<img alt="' . esc_attr( $new_alt ) . '"', $tag, 1 );
	}, $content );
}, 20, 2 );
"""

FUNCTIONS_ALT_FILTER = r"""
add_filter( 'wp_get_attachment_image_attributes', function ( $attr, $attachment ) {
	if ( empty( $attr['alt'] ) && $attachment instanceof WP_Post ) {
		$meta = get_post_meta( $attachment->ID, '_wp_attachment_image_alt', true );
		if ( $meta ) {
			$attr['alt'] = $meta;
		}
	}
	return $attr;
}, 20, 2 );
"""


def walk_images(elements, fn):
    for el in elements:
        if el.get("widgetType") == "image":
            fn(el)
        if el.get("elements"):
            walk_images(el["elements"], fn)


def deploy_page517(wp, elements):
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = "klz_el517b"
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
    update_post_meta(517, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta(517, '_elementor_element_cache');
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/").read(32768)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )


def patch_snippet5(wp):
    s5 = wp.rest("GET", "/code-snippets/v1/snippets/5")
    code = s5["code"]
    start = code.find("add_filter( 'elementor/widget/render_content'")
    if start != -1:
        end = code.find("}, 20, 2 );", start)
        if end != -1:
            end += len("}, 20, 2 );")
            code = code[:start] + SNIPPET5_ALT_FILTER.strip() + code[end:]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/5",
        {
            "id": 5,
            "code": code,
            "active": True,
            "name": s5.get("name") or "KLZ SEO + sitemap + title",
            "scope": "global",
            "priority": s5.get("priority", 10),
            "desc": s5.get("desc") or "",
            "tags": s5.get("tags") or [],
        },
    )


def patch_functions_alt_filter(wp):
    marker = "klz_attachment_alt_fix"
    inject = (
        "add_filter( 'wp_get_attachment_image_attributes', function ( $attr, $attachment ) {\n"
        "\tif ( empty( $attr['alt'] ) && $attachment instanceof WP_Post ) {\n"
        "\t\t$meta = get_post_meta( $attachment->ID, '_wp_attachment_image_alt', true );\n"
        "\t\tif ( $meta ) {\n"
        "\t\t\t$attr['alt'] = $meta;\n"
        "\t\t}\n"
        "\t}\n"
        "\treturn $attr;\n"
        "}, 20, 2 );"
    )
    runner = f"""add_action('init', function () {{
    if (get_option('{marker}')) return;
    $path = get_stylesheet_directory() . '/functions.php';
    $php = file_get_contents($path);
    if (strpos($php, '{marker}') !== false) {{
        update_option('{marker}', 1);
        return;
    }}
    $inject = <<<'KLZPHP'
{inject}
KLZPHP;
    $php .= "\\n\\n// {marker}\\n" . $inject;
    file_put_contents($path, $php);
    update_option('{marker}', 1);
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/").read(8192)
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

    print("1. Media library alt texty (7 fotek)...")
    for aid, alt in MEDIA_ALTS.items():
        safe = alt.replace('"', '\\"')
        wp.cli(f'post meta update {aid} _wp_attachment_image_alt "{safe}"', confirm=True)

    print("2. Elementor úvod — image_alt widgety...")
    el = wp.load_el(517)
    def set_alt(e):
        wid = e.get("id", "")
        if wid in WIDGET_ALTS:
            e.setdefault("settings", {})["image_alt"] = WIDGET_ALTS[wid]
    walk_images(el, set_alt)
    deploy_page517(wp, el)

    print("3. Snippet #5 — oprava prázdného alt=\"\"...")
    patch_snippet5(wp)

    print("4. functions.php — doplnění alt z meta...")
    patch_functions_alt_filter(wp)

    print("5. Cache...")
    wp.cli("post meta delete 517 _elementor_element_cache", confirm=True)
    wp.cli("cache flush", confirm=True)
    wp.purge_cache()
    wp.op.open(f"{SITE}/?nocache=1").read(32768)

    print("Hotovo.")


if __name__ == "__main__":
    main()
