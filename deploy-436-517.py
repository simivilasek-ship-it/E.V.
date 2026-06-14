#!/usr/bin/env python3
"""Deploy stránek 436 a 517 přes options + dočasný Code Snippet #6."""
import base64
import http.cookiejar
import importlib.util
import json
import os
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://it2529.sspu-opava.eu"
PWD = os.environ.get("WP_PASS", "")

_spec = importlib.util.spec_from_file_location(
    "p", os.path.join(os.path.dirname(__file__), "deploy-content-updates.py")
)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

RUNNER = """add_action('init', function () {
    if (get_option('klz_pages_436_517_done')) {
        return;
    }
    foreach (array(436 => 'klz_el436', 517 => 'klz_el517') as $pid => $prefix) {
        $parts = (int) get_option($prefix . '_parts', 0);
        $b64 = '';
        for ($i = 0; $i < $parts; $i++) {
            $b64 .= (string) get_option($prefix . '_' . $i, '');
        }
        if (!$b64) {
            continue;
        }
        $data = json_decode(base64_decode($b64), true);
        if (!is_array($data)) {
            continue;
        }
        update_post_meta($pid, '_elementor_data', wp_slash(wp_json_encode($data)));
        delete_post_meta($pid, '_elementor_element_cache');
    }
    update_option('klz_pages_436_517_done', 1);
}, 1);
"""


class WP:
    def __init__(self):
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.MozillaCookieJar())
        )

    def login(self):
        self.op.open(f"{SITE}/wp-login.php")
        data = urllib.parse.urlencode(
            {
                "log": "it2529",
                "pwd": PWD,
                "wp-submit": "Přihlásit se",
                "redirect_to": f"{SITE}/wp-admin/",
                "testcookie": "1",
            }
        ).encode()
        self.op.open(urllib.request.Request(f"{SITE}/wp-login.php", data=data, method="POST"))

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

    def load_el(self, pid):
        return json.loads(
            self.cli(f"post meta get {pid} _elementor_data --format=json").get("stdout") or "[]"
        )

    def rest(self, method, route, body=None):
        req = urllib.request.Request(
            f"{SITE}/index.php?rest_route={route}",
            data=json.dumps(body).encode() if body else None,
            method=method,
            headers={"Content-Type": "application/json", "X-WP-Nonce": self.nonce()},
        )
        return json.loads(self.op.open(req).read().decode())


def store_chunks(wp: WP, prefix: str, b64: str):
    wp.cli(f"option delete {prefix}_parts", confirm=True)
    chunks = [b64[i : i + 8000] for i in range(0, len(b64), 8000)]
    for i, ch in enumerate(chunks):
        esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        wp.cli(f'option update {prefix}_{i} "{esc}"', confirm=True)
    wp.cli(f"option update {prefix}_parts {len(chunks)}", confirm=True)


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")
    wp = WP()
    wp.login()
    wp.cli("option delete klz_pages_436_517_done", confirm=True)

    el436 = wp.load_el(436)
    P.patch_sluzby(el436)
    store_chunks(wp, "klz_el436", base64.b64encode(json.dumps(el436, ensure_ascii=False).encode()).decode())

    el517 = wp.load_el(517)
    P.patch_uvod(el517, [720, 719, 718])
    store_chunks(wp, "klz_el517", base64.b64encode(json.dumps(el517, ensure_ascii=False).encode()).decode())

    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig_code, orig_active = s6["code"], s6["active"]
    r = wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {
            "code": RUNNER,
            "active": True,
            "name": s6["name"],
            "scope": "global",
            "priority": 1,
        },
    )
    print("activate snippet 6:", r.get("active"), r.get("code_error"))

    wp.op.open(f"{SITE}/").read(65536)
    wp.op.open(f"{SITE}/?pagename=sluzby").read(65536)

    done = wp.cli("option get klz_pages_436_517_done").get("stdout", "").strip()
    print("done flag:", done)
    print("436 scvyc01:", "scvyc01" in (wp.cli("post meta get 436 _elementor_data").get("stdout") or ""))
    print("517 aktual01:", "aktual01" in (wp.cli("post meta get 517 _elementor_data").get("stdout") or ""))

    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig_code, "active": orig_active, "name": s6["name"], "scope": "global"},
    )

    for pid in [436, 517, 440, 509]:
        wp.cli(f"post update {pid} --post_modified=now", confirm=True)
        wp.cli(f"post meta delete {pid} _elementor_element_cache", confirm=True)
    wp.cli("cache flush", confirm=True)
    print("Hotovo.")


if __name__ == "__main__":
    main()
