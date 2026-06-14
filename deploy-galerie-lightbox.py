#!/usr/bin/env python3
"""Galerie (639): lightbox s přepínáním fotek."""
import base64
import importlib.util
import json
import os
import re
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
CSS_MARKER = "/* KLZ galerie lightbox v1 */"

GAL_CSS = """
/* KLZ galerie lightbox v1 */
.klz-galerie {
  display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)) !important;
  gap: 16px !important;
  width: 100% !important;
  max-width: 1100px !important;
  margin: 0 auto !important;
}
.klz-galerie-item {
  display: block !important;
  width: 100% !important;
  padding: 0 !important;
  border: none !important;
  background: none !important;
  cursor: zoom-in !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 4px 18px rgba(15, 15, 15, 0.08) !important;
  transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.klz-galerie-item:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 10px 28px rgba(15, 15, 15, 0.14) !important;
}
.klz-galerie-item img {
  width: 100% !important;
  height: 200px !important;
  object-fit: cover !important;
  display: block !important;
}
.klz-lightbox {
  position: fixed !important;
  inset: 0 !important;
  z-index: 999999 !important;
  background: rgba(8, 10, 16, 0.94) !important;
  display: none !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 56px 72px !important;
}
.klz-lightbox.is-open { display: flex !important; }
.klz-lightbox img {
  max-width: min(1100px, 100%) !important;
  max-height: calc(100vh - 120px) !important;
  width: auto !important;
  height: auto !important;
  object-fit: contain !important;
  border-radius: 8px !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45) !important;
}
.klz-lightbox-close,
.klz-lightbox-prev,
.klz-lightbox-next {
  position: absolute !important;
  border: none !important;
  background: rgba(255, 255, 255, 0.12) !important;
  color: #fff !important;
  width: 48px !important;
  height: 48px !important;
  border-radius: 999px !important;
  font-size: 28px !important;
  line-height: 1 !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.klz-lightbox-close { top: 16px; right: 16px; font-size: 32px !important; }
.klz-lightbox-prev { left: 16px; top: 50%; transform: translateY(-50%); }
.klz-lightbox-next { right: 16px; top: 50%; transform: translateY(-50%); }
.klz-lightbox-close:hover,
.klz-lightbox-prev:hover,
.klz-lightbox-next:hover { background: rgba(255, 255, 255, 0.22) !important; }
.klz-lightbox-counter {
  position: absolute !important;
  bottom: 18px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  color: rgba(255, 255, 255, 0.85) !important;
  font: 600 14px/1.4 Inter, sans-serif !important;
  letter-spacing: 0.04em !important;
}
@media (max-width: 767px) {
  .klz-galerie { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 10px !important; }
  .klz-galerie-item img { height: 140px !important; }
  .klz-lightbox { padding: 48px 12px !important; }
  .klz-lightbox-prev, .klz-lightbox-next { width: 40px !important; height: 40px !important; }
}
"""

GAL_JS = """
<script>
(function () {
  function init() {
    var grid = document.querySelector('.klz-galerie');
    var box = document.getElementById('klz-lightbox');
    if (!grid || !box) return;
    var items = Array.prototype.slice.call(grid.querySelectorAll('.klz-galerie-item'));
    if (!items.length) return;
    var img = box.querySelector('img');
    var counter = box.querySelector('.klz-lightbox-counter');
    var idx = 0;
    function show(i) {
      idx = (i + items.length) % items.length;
      img.src = items[idx].getAttribute('data-full') || items[idx].querySelector('img').src;
      img.alt = (items[idx].querySelector('img') || {}).alt || '';
      counter.textContent = (idx + 1) + ' / ' + items.length;
    }
    function open(i) { show(i); box.classList.add('is-open'); document.body.style.overflow = 'hidden'; }
    function close() { box.classList.remove('is-open'); document.body.style.overflow = ''; img.removeAttribute('src'); }
    items.forEach(function (el, i) {
      el.addEventListener('click', function () { open(i); });
    });
    box.querySelector('.klz-lightbox-close').addEventListener('click', close);
    box.querySelector('.klz-lightbox-prev').addEventListener('click', function (e) { e.stopPropagation(); show(idx - 1); });
    box.querySelector('.klz-lightbox-next').addEventListener('click', function (e) { e.stopPropagation(); show(idx + 1); });
    box.addEventListener('click', function (e) { if (e.target === box) close(); });
    document.addEventListener('keydown', function (e) {
      if (!box.classList.contains('is-open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') show(idx - 1);
      if (e.key === 'ArrowRight') show(idx + 1);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
</script>
"""

LIGHTBOX_HTML = """
<div id="klz-lightbox" class="klz-lightbox" role="dialog" aria-modal="true" aria-label="Galerie fotek">
  <button type="button" class="klz-lightbox-close" aria-label="Zavřít">&times;</button>
  <button type="button" class="klz-lightbox-prev" aria-label="Předchozí fotka">&#8249;</button>
  <img src="" alt="">
  <button type="button" class="klz-lightbox-next" aria-label="Další fotka">&#8250;</button>
  <div class="klz-lightbox-counter"></div>
</div>
"""


def full_url(src: str) -> str:
    return re.sub(r"-\d+x\d+(\.(?:jpe?g|png|webp))", r"\1", src, flags=re.I)


def strip_old_assets(html: str) -> str:
    html = re.sub(r"<style[^>]*>[\s\S]*?klz-galerie[\s\S]*?</style>", "", html, flags=re.I)
    html = re.sub(r"<script>[\s\S]*?klz-galerie[\s\S]*?</script>", "", html, flags=re.I)
    html = re.sub(r'<div id="klz-lightbox"[\s\S]*?</div>\s*(?=<script|$)', "", html, flags=re.I)
    return html.strip()


def wrap_gallery(html: str) -> str:
    html = strip_old_assets(html)

    def repl(m):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]+)"', tag)
        if not src_m:
            return tag
        src = src_m.group(1)
        alt_m = re.search(r'alt="([^"]*)"', tag)
        alt = alt_m.group(1) if alt_m else "Fotografie z letiště LKZA Zábřeh"
        full = full_url(src)
        esc_alt = alt.replace('"', "&quot;")
        return (
            f'<button type="button" class="klz-galerie-item" data-full="{full}" '
            f'aria-label="Otevřít fotku: {esc_alt}">'
            f'<img src="{src}" alt="{esc_alt}" loading="lazy"></button>'
        )

    html = re.sub(r"<img\b[^>]*>", repl, html)

    if "klz-galerie" not in html:
        m = re.search(r"<div(\s[^>]*)?>", html)
        if m:
            tag = m.group(0)
            if 'class="' in tag:
                new_tag = re.sub(r'class="([^"]*)"', r'class="\1 klz-galerie"', tag, count=1)
            else:
                new_tag = tag.replace("<div", '<div class="klz-galerie"', 1)
            html = html.replace(tag, new_tag, 1)
        else:
            html = f'<div class="klz-galerie">{html}</div>'

    return html + LIGHTBOX_HTML + GAL_JS


def deploy_page639(wp, elements):
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = "klz_el639_lb"
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
    update_post_meta(639, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta(639, '_elementor_element_cache');
    update_option('klz_galerie_lightbox_done', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/?pagename=galerie").read(32768)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
    )


def deploy_css(wp):
    css = urllib.request.urlopen(f"{SITE}/wp-content/themes/hello-elementor/assets/klz-site.css").read().decode(
        "utf-8", "replace"
    )
    if CSS_MARKER in css:
        start = css.index(CSS_MARKER)
        end = css.find("\n/* ", start + len(CSS_MARKER))
        css = css[:start] + (css[end + 1 :] if end != -1 else "")
    css = css.rstrip() + "\n" + GAL_CSS.strip() + "\n"
    b64 = base64.b64encode(css.encode()).decode()
    wp.cli("option delete klz_css_gal_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update klz_css_gal_{i} "{esc}"', confirm=True)
    wp.cli(f"option update klz_css_gal_parts {len(chunks)}", confirm=True)
    runner = f"""add_action('init', function () {{
    $parts = (int) get_option('klz_css_gal_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('klz_css_gal_' . $i, '');
    if (!$b64) return;
    file_put_contents(ABSPATH . '{CSS_PATH}', base64_decode($b64));
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

    el = wp.load_el(639)
    gal = P.find_widget(el, "gal00010")
    gal["settings"]["editor"] = wrap_gallery(gal["settings"]["editor"])
    n = len(re.findall(r"klz-galerie-item", gal["settings"]["editor"]))
    print(f"Galerie: {n} fotek s lightboxem")

    deploy_page639(wp, el)
    deploy_css(wp)

    wp.cli("post meta delete 639 _elementor_element_cache", confirm=True)
    wp.cli("cache flush", confirm=True)
    wp.purge_cache()
    print("Hotovo.")


if __name__ == "__main__":
    main()
