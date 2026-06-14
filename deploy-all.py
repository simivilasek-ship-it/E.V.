#!/usr/bin/env python3
"""Nasadí všechny požadované úpravy přes wpvibe CLI (správné ukládání Elementor meta)."""
import http.cookiejar
import importlib.util
import json
import os
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://it2529.sspu-opava.eu"
USER = os.environ.get("WP_USER", "it2529")
PWD = os.environ.get("WP_PASS", "")

_spec = importlib.util.spec_from_file_location(
    "patches",
    os.path.join(os.path.dirname(__file__), "deploy-content-updates.py"),
)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


class WPSession:
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
        self.op.open(
            urllib.request.Request(f"{SITE}/wp-login.php", data=data, method="POST")
        )
        admin = self.op.open(f"{SITE}/wp-admin/").read().decode("utf-8", "replace")
        if "wp-admin-bar" not in admin and "Nástěnka" not in admin:
            raise SystemExit("Přihlášení selhalo")

    def _nonce(self):
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
            headers={
                "Content-Type": "application/json",
                "X-WP-Nonce": self._nonce(),
            },
        )
        try:
            return json.loads(self.op.open(req).read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "body": e.read().decode()[:600]}

    def load_el(self, pid):
        r = self.cli(f"post meta get {pid} _elementor_data --format=json")
        return json.loads(r.get("stdout") or "[]")

    def save_el(self, pid, elements):
        payload = json.dumps(elements, ensure_ascii=False)
        cmd = "post meta update %d _elementor_data '%s'" % (
            pid,
            payload.replace("'", "'\\''"),
        )
        return self.cli(cmd, confirm=True)

    def parse_post_ids(self, raw):
        raw = (raw or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            data = json.loads(raw)
            ids = []
            for item in data:
                if isinstance(item, dict):
                    ids.append(int(item.get("ID") or item.get("id")))
                else:
                    ids.append(int(item))
            return ids
        return [int(x) for x in raw.split()]


def patch_functions_emails_via_snippet(wp: WPSession):
    """Dočasný snippet pro sjednocení e-mailů ve functions.php (Code Snippets)."""
    code = r"""
add_action('init', function () {
    if (get_option('klz_email_patch_done')) return;
    $path = get_stylesheet_directory() . '/functions.php';
    if (!is_readable($path)) return;
    $c = file_get_contents($path);
    $n = str_replace(
        ['info@letani-zabreh.cz', 'it2529@sspu-opava.cz'],
        'klub@letani-zabreh.cz',
        $c
    );
    if ($n !== $c) file_put_contents($path, $n);
    update_option('klz_email_patch_done', 1);
}, 1);
""".strip()
    wp.cli("option delete klz_email_patch_done", confirm=True)
    # Code Snippets ukládá do wp_snippets — vytvoříme přes insert pokud existuje tabulka
    esc = code.replace("\\", "\\\\").replace('"', '\\"')
    sql = (
        'db query "INSERT INTO wp_snippets (name, description, code, tags, scope, priority, '
        'active, modified, revision, cloud_id) SELECT \'KLZ email patch\', \'\', '
        f'\'{esc}\', \'\', \'global\', 10, 1, NOW(), 1, NULL FROM DUAL '
        "WHERE NOT EXISTS (SELECT 1 FROM wp_snippets WHERE name='KLZ email patch')\""
    )
    r = wp.cli(sql, confirm=True)
    if r.get("error") or (r.get("stderr") and "Error" in str(r.get("stderr"))):
        print("  Snippet DB skip:", r.get("stderr") or r.get("body") or r)
    else:
        print("  E-mail snippet aktivován")


def verify():
    html = (
        urllib.request.urlopen(f"{SITE}/?pagename=kontakt")
        .read()
        .decode("utf-8", "replace")
    )
    checks = {
        "telefon": "737 871 590" in html,
        "email_klub": "klub@letani-zabreh.cz" in html,
        "ic": "03522245" in html,
        "cím_létáme": "SKYLARK" in urllib.request.urlopen(f"{SITE}/?pagename=o-nas").read().decode("utf-8", "replace"),
        "vycvik": "Výcvik ULL" in urllib.request.urlopen(f"{SITE}/?pagename=sluzby").read().decode("utf-8", "replace"),
        "aktuality": "Aktuality a akce" in urllib.request.urlopen(SITE).read().decode("utf-8", "replace"),
    }
    return checks


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")
    wp = WPSession()
    wp.login()

    post_ids = wp.parse_post_ids(
        wp.cli("post list --post_type=post --format=ids --posts_per_page=10").get("stdout")
    )
    if len(post_ids) < 3:
        post_ids = [720, 719, 718]
    print("Příspěvky:", post_ids)

    for pid, fn in [
        (440, P.patch_kontakt),
        (509, P.patch_onas),
        (436, P.patch_sluzby),
    ]:
        print(f"Ukládám {pid}...")
        el = wp.load_el(pid)
        fn(el)
        r = wp.save_el(pid, el)
        print(" ", r.get("stdout") or r.get("error") or r)

    print("Ukládám 517...")
    el517 = wp.load_el(517)
    P.patch_uvod(el517, post_ids)
    r = wp.save_el(517, el517)
    print(" ", r.get("stdout") or r.get("error") or r)

    patch_functions_emails_via_snippet(wp)

    wp.cli("cache flush", confirm=True)
    wp.cli("elementor flush-css", confirm=True)

    print("Ověření:", verify())
    print("Hotovo.")


if __name__ == "__main__":
    main()
