#!/usr/bin/env python3
"""Deploy přes wpvibe draft-theme + spuštění klz-deploy-content.php v functions.php."""
import base64
import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://it2529.sspu-opava.eu"
USER = os.environ.get("WP_USER", "it2529")
PWD = os.environ.get("WP_PASS", "")
DEPLOY_PHP = os.path.join(os.path.dirname(__file__), "klz-deploy-content.php")
RESTORE_HOOK = """
/* KLZ one-shot restore page 440 if corrupted */
add_action('init', function () {
    if (get_option('klz_restore_440_done')) {
        return;
    }
    $b = (string) get_option('klz_r440_0', '') . (string) get_option('klz_r440_1', '');
    if (!$b) {
        return;
    }
    $data = json_decode(base64_decode($b), true);
    if (!is_array($data)) {
        return;
    }
    update_post_meta(440, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta(440, '_elementor_element_cache');
    update_option('klz_restore_440_done', 1);
    if (class_exists('\\Elementor\\Plugin')) {
        \\Elementor\\Plugin::$instance->files_manager->clear_cache();
    }
}, 1);
"""

DEPLOY_HOOK = """
/* KLZ one-shot content deploy */
add_action('init', function () {
    if (get_option('klz_content_deploy_done')) {
        return;
    }
    $path = get_stylesheet_directory() . '/klz-deploy-content.php';
    if (!is_readable($path)) {
        return;
    }
    require $path;
    update_option('klz_content_deploy_done', 1);
}, 2);
"""


def login(opener):
    opener.open(f"{SITE}/wp-login.php")
    data = urllib.parse.urlencode(
        {
            "log": USER,
            "pwd": PWD,
            "wp-submit": "Přihlásit se",
            "redirect_to": f"{SITE}/wp-admin/",
            "testcookie": "1",
        }
    ).encode()
    opener.open(urllib.request.Request(f"{SITE}/wp-login.php", data=data, method="POST"))
    admin = opener.open(f"{SITE}/wp-admin/").read().decode("utf-8", "replace")
    if "wp-admin-bar" not in admin and "Nástěnka" not in admin:
        raise SystemExit("Přihlášení selhalo")


def nonce(opener):
    return opener.open(f"{SITE}/wp-admin/admin-ajax.php?action=rest-nonce").read().decode().strip('"')


def cli(opener, cmd, confirm=False):
    body = {"command": cmd}
    if confirm:
        body["confirm_write"] = True
    req = urllib.request.Request(
        f"{SITE}/index.php?rest_route=/wpvibe/v1/cli/run",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-WP-Nonce": nonce(opener)},
    )
    try:
        return json.loads(opener.open(req).read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:600]}


def rest(opener, route, data=None, method="POST"):
    req = urllib.request.Request(
        f"{SITE}/index.php?rest_route={route}",
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={"Content-Type": "application/json", "X-WP-Nonce": nonce(opener)},
    )
    try:
        return json.loads(opener.open(req).read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:600]}


def read_functions(opener):
    rest(opener, "/wpvibe/v1/draft-theme/create", {})
    r = rest(
        opener,
        "/wpvibe/v1/file/read",
        {"path": "functions.php", "theme": "hello-elementor"},
    )
    return r.get("content") or ""


def edit_functions(opener, old, new):
    return rest(
        opener,
        "/wpvibe/v1/file/edit",
        {
            "path": "functions.php",
            "theme": "hello-elementor",
            "old_content": old,
            "new_content": new,
        },
    )


def write_theme_file(opener, path, content):
    """Vytvoří/ přepíše soubor v draft tématu přes edit s prázdným old."""
    return rest(
        opener,
        "/wpvibe/v1/file/edit",
        {
            "path": path,
            "theme": "hello-elementor",
            "old_content": "",
            "new_content": content,
        },
    )


def publish_and_trigger(opener):
    pub = rest(opener, "/wpvibe/v1/draft-theme/publish", {})
    print("publish:", pub.get("success", pub))
    cli(opener, "cache flush", confirm=True)
    cli(opener, "elementor flush-css", confirm=True)
    # Spustí init hooky
    for url in [f"{SITE}/", f"{SITE}/?page_id=440", f"{SITE}/?page_id=509"]:
        try:
            opener.open(url).read(4096)
        except Exception:
            pass


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.MozillaCookieJar()))
    login(opener)

    # Reset deploy flags
    cli(opener, "option delete klz_content_deploy_done", confirm=True)
    cli(opener, "option delete klz_restore_440_done", confirm=True)

    deploy_php = open(DEPLOY_PHP, encoding="utf-8").read()
    # Odstraň closing ?> pokud je
    deploy_php = deploy_php.replace("?>", "").strip()

    fn = read_functions(opener)
    if not fn:
        raise SystemExit("Nelze načíst functions.php")

    # Odstraň staré KLX hooky
    fn_clean = re.sub(r"/\* KLZ one-shot.*?\*/\s*add_action\('init'.*?\n\}, \d+\);\n", "", fn, flags=re.S)

    # 1) Restore hook + deploy soubor + deploy hook
    w = write_theme_file(opener, "klz-deploy-content.php", "<?php\n" + deploy_php + "\n")
    print("write deploy php:", w.get("success", w))

    new_fn = fn_clean.rstrip() + "\n" + RESTORE_HOOK + DEPLOY_HOOK
    e = edit_functions(opener, fn_clean, new_fn)
    print("edit functions:", e.get("success", e))

    publish_and_trigger(opener)

    # Ověření
    html = opener.open(f"{SITE}/?page_id=440").read().decode("utf-8", "replace")
    checks = {
        "telefon": "737 871 590" in html,
        "email": "klub@letani-zabreh.cz" in html,
        "ic": "03522245" in html,
    }
    print("Kontakt ověření:", checks)

    # Uklidit hooky z functions.php (nechat deploy soubor)
    fn2 = read_functions(opener)
    fn3 = re.sub(r"/\* KLZ one-shot.*?\*/\s*add_action\('init'.*?\n\}, \d+\);\n", "", fn2, flags=re.S)
    if fn3 != fn2:
        edit_functions(opener, fn2, fn3)
        publish_and_trigger(opener)
        print("Hooky odstraněny z functions.php")

    print("Hotovo.")


if __name__ == "__main__":
    main()
