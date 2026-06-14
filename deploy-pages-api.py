#!/usr/bin/env python3
"""Služby (výcvik), nová stránka Čím létáme, kontakt IČO+e-mail — přes wpvibe REST API."""
import base64
import copy
import http.cookiejar
import importlib.util
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://it2529.sspu-opava.eu"
USER = os.environ.get("WP_USER", "it2529")
PWD = os.environ.get("WP_PASS", "")

_spec = importlib.util.spec_from_file_location(
    "patches", os.path.join(os.path.dirname(__file__), "deploy-content-updates.py")
)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


class WP:
    def __init__(self):
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.MozillaCookieJar())
        )

    def login(self):
        self.op.open(f"{SITE}/wp-login.php")
        data = urllib.parse.urlencode(
            {
                "log": USER,
                "pwd": PWD,
                "wp-submit": "Přihlásit se",
                "redirect_to": f"{SITE}/wp-admin/",
                "testcookie": "1",
            }
        ).encode()
        self.op.open(urllib.request.Request(f"{SITE}/wp-login.php", data=data, method="POST"))
        admin = self.op.open(f"{SITE}/wp-admin/").read().decode("utf-8", "replace")
        if "wp-admin-bar" not in admin and "Nástěnka" not in admin:
            raise SystemExit("Přihlášení selhalo")

    def nonce(self):
        return (
            self.op.open(f"{SITE}/wp-admin/admin-ajax.php?action=rest-nonce")
            .read()
            .decode()
            .strip('"')
        )

    def cli(self, cmd, confirm=False):
        body = {"command": cmd}
        if confirm:
            body["confirm_write"] = True
        req = urllib.request.Request(
            f"{SITE}/index.php?rest_route=/wpvibe/v1/cli/run",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-WP-Nonce": self.nonce()},
        )
        try:
            return json.loads(self.op.open(req).read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "body": e.read().decode()[:800]}

    def rest(self, method, route, body=None):
        req = urllib.request.Request(
            f"{SITE}/index.php?rest_route={route}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Content-Type": "application/json", "X-WP-Nonce": self.nonce()},
        )
        return json.loads(self.op.open(req).read().decode())

    def load_el(self, pid):
        r = self.cli(f"post meta get {pid} _elementor_data --format=json")
        return json.loads(r.get("stdout") or "[]")

    def save_el(self, pid, elements):
        payload = json.dumps(elements, ensure_ascii=False)
        if ";" in payload:
            return P.update_meta_json(self.op, self.nonce(), pid, elements)
        cmd = "post meta update %d _elementor_data '%s'" % (
            pid,
            payload.replace("'", "'\\''"),
        )
        return self.cli(cmd, confirm=True)

    def purge_cache(self):
        html = self.op.open(
            f"{SITE}/wp-admin/options-general.php?page=wpsupercache&tab=easy"
        ).read().decode("utf-8", "replace")
        m = re.search(r'name="_wpnonce" value="([^"]+)"', html)
        if not m:
            return
        post = urllib.parse.urlencode(
            {
                "wp_delete_cache": "1",
                "wp_cache_clear": "",
                "_wpnonce": m.group(1),
                "_wp_http_referer": "/wp-admin/options-general.php?page=wpsupercache&tab=easy",
                "action": "easy",
            }
        ).encode()
        self.op.open(
            urllib.request.Request(
                f"{SITE}/wp-admin/options-general.php?page=wpsupercache&tab=easy",
                data=post,
                method="POST",
            )
        )


def patch_kontakt_minimal(elements):
    """Jen e-mail a IČO — formulář necháme beze změny."""
    icons = P.find_widget(elements, "eb333334")
    if icons:
        for item in icons["settings"].get("icon_list", []):
            icon = str(item.get("selected_icon", {}).get("value", ""))
            if "envelope" in icon or "@" in item.get("text", ""):
                item["text"] = "klub@letani-zabreh.cz"
                item["link"] = {"url": "mailto:klub@letani-zabreh.cz"}
    addr = P.find_widget(elements, "eb999999")
    if addr:
        html = addr["settings"].get("editor", "")
        if "03522245" not in html:
            addr["settings"]["editor"] = P.CONTACT_EDITOR
        else:
            html = re.sub(
                r"(<strong>IČ:</strong>\s*)[^<\n]+",
                r"\g<1>03522245",
                html,
            )
            html = re.sub(
                r"mailto:[^\"'>]+",
                "mailto:klub@letani-zabreh.cz",
                html,
            )
            addr["settings"]["editor"] = html
    seo = P.find_widget(elements, "seofix440")
    if seo:
        html = seo["settings"].get("html", "")
        html = re.sub(
            r'"email"\s*:\s*"[^"]*"',
            '"email": "klub@letani-zabreh.cz"',
            html,
        )
        seo["settings"]["html"] = html


def patch_sluzby_force(elements):
    if P.find_widget(elements, "scvyc01"):
        print("  Služby: výcvik už v meta")
        return
    P.patch_sluzby(elements)


def cim_letame_page_data():
    fleet = copy.deepcopy(P.fleet_container())
    fleet["id"] = "clpage01"
    for el in fleet.get("elements", []):
        if el.get("id") == "onfl004":
            el["id"] = "clpage04"
    hero = {
        "id": "clhero01",
        "elType": "container",
        "settings": {
            "flex_direction": "column",
            "content_width": "boxed",
            "boxed_width": {"unit": "px", "size": 1100},
            "background_background": "classic",
            "background_color": "#0f0f0f",
            "padding": {"unit": "px", "top": 80, "right": 48, "bottom": 64, "left": 48, "isLinked": False},
            "padding_mobile": {"unit": "px", "top": 56, "right": 24, "bottom": 48, "left": 24, "isLinked": False},
            "flex_align_items": "center",
        },
        "elements": [
            {
                "id": "clhero02",
                "elType": "widget",
                "settings": {
                    "title": "Čím létáme",
                    "header_size": "h1",
                    "align": "center",
                    "title_color": "#ffffff",
                    "typography_font_size": {"unit": "px", "size": 42},
                    "typography_font_weight": "800",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": "clhero03",
                "elType": "widget",
                "settings": {
                    "editor": (
                        '<p style="text-align:center;color:rgba(255,255,255,0.85);'
                        'font-size:18px;line-height:1.75;margin:16px 0 0;">'
                        "Ultralehká letadla klubu na letišti LKZA Zábřeh — pro výcvik i vyhlídkové lety.</p>"
                    )
                },
                "elements": [],
                "widgetType": "text-editor",
            },
        ],
        "isInner": False,
    }
    cta = {
        "id": "clcta01",
        "elType": "container",
        "settings": {
            "flex_direction": "column",
            "content_width": "boxed",
            "boxed_width": {"unit": "px", "size": 900},
            "background_background": "classic",
            "background_color": "#f8fafc",
            "padding": {"unit": "px", "top": 48, "right": 48, "bottom": 72, "left": 48, "isLinked": False},
            "flex_align_items": "center",
        },
        "elements": [
            {
                "id": "clcta02",
                "elType": "widget",
                "settings": {
                    "editor": (
                        '<p style="text-align:center;color:#555;font-size:17px;line-height:1.8;margin:0 0 20px;">'
                        "Máte zájem o výcvik nebo prolet? Napište nám přes kontaktní formulář.</p>"
                    )
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "clcta03",
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
    return [hero, fleet, cta]


def parse_created_id(r):
    raw = (r.get("stdout") or "").strip()
    if raw.isdigit():
        return int(raw)
    try:
        data = json.loads(raw)
        return int(data.get("ID") or data.get("id"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def find_page_id(wp: WP, slug: str):
    r = wp.cli(
        f"post list --post_type=page --name={slug} --field=ID --format=ids"
    )
    pid = (r.get("stdout") or "").strip().split()[0] if r.get("stdout") else ""
    return int(pid) if pid.isdigit() else None


def ensure_cim_page(wp: WP):
    pid = find_page_id(wp, "cim-letame")
    if not pid:
        r = wp.cli(
            "post create --post_type=page --post_status=publish "
            "--post_title='Čím létáme' --post_name=cim-letame --porcelain",
            confirm=True,
        )
        pid = parse_created_id(r)
        if not pid:
            raise SystemExit(f"Nepodařilo se vytvořit stránku: {r}")
        print(f"  Vytvořena stránka Čím létáme: ID {pid}")
    else:
        print(f"  Stránka Čím létáme existuje: ID {pid}")

    for key, val in [
        ("_elementor_edit_mode", "builder"),
        ("_elementor_template_type", "wp-page"),
        ("_wp_page_template", "elementor_header_footer"),
    ]:
        wp.cli(f"post meta update {pid} {key} '{val}'", confirm=True)

    elements = cim_letame_page_data()
    r = P.update_meta_json(wp.op, wp.nonce(), pid, elements)
    print(f"  Elementor uložen: {r.get('stdout', r)}")
    wp.cli(f"post update {pid} --post_modified=now", confirm=True)
    wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
    wp.cli(f"option update klz_cim_page_id {pid}", confirm=True)
    return pid


NAV_SNIPPET = """add_action('init', function () {
    if (get_option('klz_nav_cim_done')) {
        return;
    }
    $pid = (int) get_option('klz_cim_page_id', 0);
    if (!$pid) {
        return;
    }
    $path = get_stylesheet_directory() . '/functions.php';
    if (!is_readable($path)) {
        return;
    }
    $c = file_get_contents($path);
    if (strpos($c, (string) $pid) !== false) {
        update_option('klz_nav_cim_done', 1);
        return;
    }
    $c = preg_replace(
        '/(\\$pages\\s*=\\s*array\\s*\\(\\s*517,\\s*509,)/',
        '$1 ' . $pid . ',',
        $c,
        1
    );
    $c = preg_replace(
        '/(509\\s*=>\\s*\\\'O nás\\\',)/',
        "$1\\n        $pid => 'Čím létáme',",
        $c,
        1
    );
    if ($c && is_writable($path)) {
        file_put_contents($path, $c);
        update_option('klz_nav_cim_done', 1);
    }
}, 1);
"""


def update_nav(wp: WP, cim_pid: int):
    wp.cli(f"option update klz_cim_page_id {cim_pid}", confirm=True)
    wp.cli("option delete klz_nav_cim_done", confirm=True)
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig_code, orig_active = s6["code"], s6["active"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {
            "code": NAV_SNIPPET,
            "active": True,
            "name": s6["name"],
            "scope": "global",
            "priority": 1,
        },
    )
    wp.op.open(f"{SITE}/").read(8192)
    done = wp.cli("option get klz_nav_cim_done").get("stdout", "").strip()
    print(f"  Navigace aktualizována: {done}")
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig_code, "active": orig_active, "name": s6["name"], "scope": "global"},
    )


def deploy_sluzby_via_options(wp: WP):
    """436 může obsahovat ; v CSS — použij options + snippet runner."""
    el436 = wp.load_el(436)
    patch_sluzby_force(el436)
    if P.find_widget(el436, "scvyc01"):
        b64 = base64.b64encode(
            json.dumps(el436, ensure_ascii=False).encode()
        ).decode()
        chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
        wp.cli("option delete klz_el436_parts", confirm=True)
        for i, ch in enumerate(chunks):
            esc = ch.replace("\\", "\\\\").replace('"', '\\"')
            wp.cli(f'option update klz_el436_{i} "{esc}"', confirm=True)
        wp.cli(f"option update klz_el436_parts {len(chunks)}", confirm=True)
        wp.cli("option delete klz_pages_436_517_done", confirm=True)

        runner = """add_action('init', function () {
    if (get_option('klz_pages_436_517_done')) return;
    $parts = (int) get_option('klz_el436_parts', 0);
    $b64 = '';
    for ($i = 0; $i < $parts; $i++) $b64 .= (string) get_option('klz_el436_' . $i, '');
    if (!$b64) return;
    $data = json_decode(base64_decode($b64), true);
    if (!is_array($data)) return;
    update_post_meta(436, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta(436, '_elementor_element_cache');
    update_option('klz_pages_436_517_done', 1);
}, 1);
"""
        s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
        orig = s6["code"]
        wp.rest(
            "PUT",
            "/code-snippets/v1/snippets/6",
            {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
        )
        wp.op.open(f"{SITE}/?pagename=sluzby").read(8192)
        wp.rest(
            "PUT",
            "/code-snippets/v1/snippets/6",
            {"code": orig, "active": False, "name": s6["name"], "scope": "global"},
        )
        print("  Služby: výcvik nasazen přes snippet")


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")
    wp = WP()
    wp.login()

    print("1. Služby — výcvik…")
    deploy_sluzby_via_options(wp)

    print("2. Kontakt — e-mail a IČO (formulář beze změny)…")
    el440 = wp.load_el(440)
    patch_kontakt_minimal(el440)
    r = wp.save_el(440, el440)
    print(f"  => {r.get('stdout', r)}")

    print("3. Nová stránka Čím létáme…")
    cim_pid = ensure_cim_page(wp)

    print("4. Navigace…")
    update_nav(wp, cim_pid)

    for pid in [436, 440, cim_pid]:
        wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
        wp.cli(f"post update {pid} --post_modified=now", confirm=True)

    wp.cli("cache flush", confirm=True)
    wp.cli("elementor flush-css", confirm=True)
    wp.purge_cache()
    print("\nHotovo.")


if __name__ == "__main__":
    main()
