#!/usr/bin/env python3
"""Opravy z hodnocení: překlepy, alt texty fotek, patička (telefon místo domény)."""
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

# Střídání popisů podle názvu souboru (deterministicky).
ALT_POOL = [
    "Letadlo na dráze letiště LKZA Zábřeh",
    "Vyhlídkový let nad Moravskoslezským krajem",
    "Hangár a letadla klubu létání Zábřeh",
    "Příprava letounu před startem na LKZA",
    "Pohled na letištní plochu v Dolním Benešově",
    "Pilot a spolucestující před odletem z LKZA",
    "Letoun ve vzduchu nad okolní krajinou",
    "Klub létání Zábřeh — aktivita na letišti",
    "Start letadla z dráhy letiště Zábřeh",
    "Ultralehké letadlo na parkovací ploše LKZA",
    "Letištní provoz v letním období",
    "Panorama letiště Zábřeh u Hlučína",
    "Přistání letounu na dráze LKZA Zábřeh",
    "Členové klubu u letadla na letišti Zábřeh",
    "Výhled z kokpitu během vyhlídkového letu",
]

HOME_IMAGE_ALT = {
    "about002": "Členové klubu létání Zábřeh na letišti LKZA",
    "svcimg01": "Vyhlídkový let nad Moravou — služba klubu Zábřeh",
    "svcimg02": "Výcvik pilota ULL na letišti LKZA Zábřeh",
    "gi00001": "Letadlo připravené k odletu z LKZA Zábřeh",
    "gi00002": "Hangár a provoz klubu létání Zábřeh",
    "gi00003": "Start letounu z dráhy letiště Zábřeh",
    "gi00004": "Vyhlídkový let — pohled na krajinu z výšky",
}

TEXT_REPLACEMENTS = {
    "pomocíme": "pomůžeme",
    "nájdeme": "najdeme",
    "kolíček": "koníček",
}

SNIPPET5_ALT_FILTER = r"""add_filter( 'elementor/widget/render_content', function ( $content, $widget ) {
	if ( empty( $content ) || false === stripos( $content, '<img' ) ) {
		return $content;
	}
	return preg_replace_callback( '/<img\b([^>]*?)>/i', function ( $m ) {
		$tag = $m[0];
		if ( preg_match( '/\balt\s*=\s*(["\'])(.*?)\1/i', $tag, $alt ) && trim( $alt[2] ) !== '' ) {
			return $tag;
		}
		if ( preg_match( '/wp-image-(\d+)/i', $tag, $id ) ) {
			$meta = get_post_meta( (int) $id[1], '_wp_attachment_image_alt', true );
			if ( $meta ) {
				return preg_replace( '/<img/i', '<img alt="' . esc_attr( $meta ) . '"', $tag, 1 );
			}
		}
		if ( preg_match( '/\/([^\/]+)\.(jpe?g|png|webp)/i', $tag, $fn ) ) {
			$alt = klz_alt_from_filename( $fn[1] );
			return preg_replace( '/<img/i', '<img alt="' . esc_attr( $alt ) . '"', $tag, 1 );
		}
		return preg_replace( '/<img/i', '<img alt="Letiště LKZA Zábřeh"', $tag, 1 );
	}, $content );
}, 20, 2 );
"""

SNIPPET5_HELPER = r"""
if ( ! function_exists( 'klz_alt_from_filename' ) ) {
	function klz_alt_from_filename( $basename ) {
		$map = json_decode( base64_decode( 'ALT_MAP_B64' ), true );
		if ( is_array( $map ) && isset( $map[ $basename ] ) ) {
			return $map[ $basename ];
		}
		$pool = array(
			'Letadlo na dráze letiště LKZA Zábřeh',
			'Vyhlídkový let nad Moravskoslezským krajem',
			'Hangár a letadla klubu létání Zábřeh',
			'Příprava letounu před startem na LKZA',
			'Pohled na letištní plochu v Dolním Benešově',
		);
		$idx = abs( crc32( (string) $basename ) ) % count( $pool );
		return $pool[ $idx ];
	}
}
"""


def alt_for_filename(name: str) -> str:
    stem = re.sub(r"\.[^.]+$", "", name.split("/")[-1])
    idx = abs(hash(stem)) % len(ALT_POOL)
    return ALT_POOL[idx]


def patch_strings(obj):
    """Rekurzivně opraví překlepy ve všech řetězcích v Elementor JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = patch_strings(v)
        return obj
    if isinstance(obj, list):
        return [patch_strings(x) for x in obj]
    if isinstance(obj, str):
        s = obj
        for old, new in TEXT_REPLACEMENTS.items():
            if old and old in s:
                s = s.replace(old, new)
        return s
    return obj


def add_alt_to_img_tags(html: str, filename_map: dict) -> str:
    def repl(m):
        tag = m.group(0)
        if re.search(r'\balt\s*=\s*["\'][^"\']+["\']', tag):
            return tag
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            return tag
        fname = src.group(1).split("/")[-1]
        alt = filename_map.get(fname) or alt_for_filename(fname)
        return tag.replace("<img", f'<img alt="{alt}"', 1)

    return re.sub(r"<img\b[^>]*>", repl, html)


def walk_images(elements, fn):
    for el in elements:
        if el.get("widgetType") == "image":
            fn(el)
        if el.get("elements"):
            walk_images(el["elements"], fn)


def collect_filenames(elements):
    names = set()
    for el in elements:
        s = el.get("settings", {})
        for key in ("editor", "html"):
            v = s.get(key, "")
            if isinstance(v, str):
                for src in re.findall(r'src="([^"]+)"', v):
                    names.add(src.split("/")[-1])
        url = s.get("image", {}).get("url", "")
        if url:
            names.add(url.split("/")[-1])
        if el.get("elements"):
            names |= collect_filenames(el["elements"])
    return names


def build_filename_map(elements_list):
    m = {}
    for elements in elements_list:
        for fname in collect_filenames(elements):
            if fname not in m:
                m[fname] = alt_for_filename(fname)
    for wid, alt in HOME_IMAGE_ALT.items():
        pass  # widget-specific alts applied separately
    return m


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
    urls = {
        517: f"{SITE}/",
        509: f"{SITE}/?pagename=o-nas",
        436: f"{SITE}/?pagename=sluzby",
        639: f"{SITE}/?pagename=galerie",
    }
    wp.op.open(urls.get(pid, SITE)).read(32768)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )


def patch_functions_footer(wp):
    runner = r"""add_action('init', function () {
    $path = get_stylesheet_directory() . '/functions.php';
    $php = file_get_contents($path);
    $old = "echo '<li><a href=\"https://it2529.sspu-opava.eu/\" target=\"_blank\" rel=\"noopener noreferrer\">it2529.sspu-opava.eu</a></li>';";
    $new = "echo '<li><a href=\"tel:+420737871590\">+420 737 871 590</a></li>';\n    echo '<li><a href=\"https://letani-zabreh.cz\" target=\"_blank\" rel=\"noopener noreferrer\">letani-zabreh.cz</a></li>';";
    if (strpos($php, $old) !== false) {
        $php = str_replace($old, $new, $php);
        file_put_contents($path, $php);
        update_option('klz_footer_patched', 1);
    }
}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig6 = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/").read(8192)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )
    return wp.cli("option get klz_footer_patched").get("stdout", "").strip()


def update_snippet5_alt_filter(wp, filename_map):
    s5 = wp.rest("GET", "/code-snippets/v1/snippets/5")
    code = s5["code"]
    start = code.find("add_filter( 'elementor/widget/render_content'")
    if start == -1:
        start = code.find('add_filter( "elementor/widget/render_content"')
    if start != -1:
        end = code.find("}, 20, 2 );", start)
        if end != -1:
            end += len("}, 20, 2 );")
            code = code[:start] + SNIPPET5_ALT_FILTER.strip() + code[end:]
    helper = SNIPPET5_HELPER.replace(
        "ALT_MAP_B64",
        base64.b64encode(json.dumps(filename_map, ensure_ascii=False).encode()).decode(),
    )
    if "function klz_alt_from_filename" not in code:
        code = helper + "\n" + code
    else:
        hstart = code.find("if ( ! function_exists( 'klz_alt_from_filename' )")
        if hstart != -1:
            hend = code.find("\n}", hstart) + 2
            code = code[:hstart] + helper.strip() + code[hend:]
    payload = {
        "id": 5,
        "code": code,
        "active": True,
        "name": s5.get("name") or "KLZ SEO + sitemap + title",
        "scope": "global",
        "priority": s5.get("priority", 10),
        "desc": s5.get("desc") or "",
        "tags": s5.get("tags") or [],
    }
    wp.rest("PUT", "/code-snippets/v1/snippets/5", payload)


def attachment_ids(wp):
    r = wp.cli("post list --post_type=attachment --posts_per_page=200 --format=ids")
    raw = (r.get("stdout") or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    return [str(x.get("ID", "")) for x in data if x.get("ID")]
                return [str(x) for x in data]
        except json.JSONDecodeError:
            pass
    return [x for x in raw.split() if x.isdigit()]


def attachment_filename(wp, aid):
    r = wp.cli(f"post get {aid} --field=guid")
    raw = (r.get("stdout") or "").strip()
    if raw.startswith("http"):
        return raw.split("/")[-1]
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            guid = data.get("guid") or ""
            if guid:
                return guid.split("/")[-1]
    except json.JSONDecodeError:
        pass
    r2 = wp.cli(f"post get {aid} --field=url")
    raw2 = (r2.get("stdout") or "").strip()
    if raw2.startswith("http"):
        return raw2.split("/")[-1]
    return ""


def update_media_alts(wp, filename_map):
    ids = attachment_ids(wp)
    updated = 0
    for aid in ids:
        fname = attachment_filename(wp, aid)
        if not fname:
            continue
        alt = filename_map.get(fname)
        if not alt:
            continue
        wp.cli(
            f'post meta update {aid} _wp_attachment_image_alt "{alt.replace(chr(34), "")}"',
            confirm=True,
        )
        updated += 1
    return updated


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()
    skip_el = os.environ.get("SKIP_EL") == "1"

    pages = {}
    for pid in [517, 509, 436, 639]:
        pages[pid] = patch_strings(wp.load_el(pid))

    filename_map = build_filename_map(list(pages.values()))

    gal = P.find_widget(pages[639], "gal00010")
    gal["settings"]["editor"] = add_alt_to_img_tags(
        gal["settings"]["editor"], filename_map
    )

    def set_home_alt(el):
        wid = el.get("id", "")
        alt = HOME_IMAGE_ALT.get(wid)
        if alt:
            el.setdefault("settings", {})["image_alt"] = alt
            fname = el.get("settings", {}).get("image", {}).get("url", "").split("/")[-1]
            if fname:
                filename_map[fname] = alt

    walk_images(pages[517], set_home_alt)

    cta = P.find_widget(pages[517], "cta00005")
    cta["settings"]["editor"] = cta["settings"]["editor"].replace("pomocíme", "pomůžeme")

    if not skip_el:
        print("1. Elementor stránky 517, 509, 436, 639...")
        for pid, elements in pages.items():
            deploy_elementor_page(wp, pid, elements, f"klz_review_{pid}")
    else:
        print("1. Elementor — přeskočeno (SKIP_EL=1)")

    print("2. Media library alt texty...")
    n = update_media_alts(wp, filename_map)
    print(f"   aktualizováno {n} příloh")

    print("3. Snippet #5 — chytřejší alt fallback...")
    update_snippet5_alt_filter(wp, filename_map)

    print("4. Patička — telefon místo studentské domény...")
    patched = patch_functions_footer(wp)
    print(f"   footer patched: {patched}")

    print("5. Cache...")
    wp.cli("option update wp_cache_enabled 0", confirm=True)
    for pid in [517, 509, 436, 639, 440]:
        wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
    wp.purge_cache()
    wp.cli("cache flush", confirm=True)

    for url in [f"{SITE}/", f"{SITE}/?pagename=galerie", f"{SITE}/?pagename=sluzby"]:
        wp.op.open(url).read(8192)
    print("Hotovo.")


if __name__ == "__main__":
    main()
