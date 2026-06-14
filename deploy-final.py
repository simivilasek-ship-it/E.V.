#!/usr/bin/env python3
"""Deploy přes wpvibe CLI (ajax nonce) + draft theme pro functions.php."""
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

# Načti patch funkce z deploy-content-updates.py
_spec = importlib.util.spec_from_file_location(
    "deploy_patches",
    os.path.join(os.path.dirname(__file__), "deploy-content-updates.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


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


def rest(opener, route, data=None, method="POST"):
    nonce = opener.open(f"{SITE}/wp-admin/admin-ajax.php?action=rest-nonce").read().decode().strip('"')
    req = urllib.request.Request(
        f"{SITE}/index.php?rest_route={route}",
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={"Content-Type": "application/json", "X-WP-Nonce": nonce},
    )
    try:
        return json.loads(opener.open(req).read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:800]}


def cli(opener, cmd, confirm=False):
    nonce = opener.open(f"{SITE}/wp-admin/admin-ajax.php?action=rest-nonce").read().decode().strip('"')
    body = {"command": cmd}
    if confirm:
        body["confirm_write"] = True
    req = urllib.request.Request(
        f"{SITE}/index.php?rest_route=/wpvibe/v1/cli/run",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-WP-Nonce": nonce},
    )
    try:
        return json.loads(opener.open(req).read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:800]}


def load_elementor(opener, pid):
    r = cli(opener, f"post meta get {pid} _elementor_data --format=json")
    return json.loads(r.get("stdout") or "[]")


def save_elementor(opener, pid, elements):
    """Uloží meta přes dočasný soubor na serveru (post meta import)."""
    payload = json.dumps(elements, ensure_ascii=False)
    tmp = f"/tmp/klz-el-{pid}.json"
    # Zapisuj po řádcích přes option (malé chunky)
    opt = f"klz_el_{pid}_b64"
    import base64

    b64 = base64.b64encode(payload.encode()).decode()
    cli(opener, f"option delete {opt}", confirm=True)
    chunk_size = 8000
    chunks = [b64[i : i + chunk_size] for i in range(0, len(b64), chunk_size)]
    for i, ch in enumerate(chunks):
        key = f"{opt}_{i}"
        ch_esc = ch.replace("\\", "\\\\").replace('"', '\\"')
        r = cli(opener, f'option update {key} "{ch_esc}"', confirm=True)
        if r.get("error"):
            return r
    # Import přes povolený wp eval-file? zkus post meta update s base64 decode via snippet
    # Fallback: přímý post meta update pokud vejde do limitu
    if len(payload) < 90000:
        esc = payload.replace("\\", "\\\\").replace("'", "'\\''")
        return cli(
            opener,
            f"post meta update {pid} _elementor_data '{esc}'",
            confirm=True,
        )
    # Velké stránky: uložit do uploads přes post create attachment není možné bez eval
    # Použij wp post meta update s JSON souborem — WP-CLI podporuje stdin v některých verzích
    parts = "+".join([f"get_option('{opt}_{i}')" for i in range(len(chunks))])
    return {
        "error": "payload_too_large",
        "hint": f"Page {pid} needs manual deploy; size=" + str(len(payload)),
    }


def patch_functions_via_draft(opener):
    rest(opener, "/wpvibe/v1/draft-theme/create", {})
    r = rest(opener, "/wpvibe/v1/draft-theme/status", None, "GET")
    if r.get("error"):
        print("draft status:", r)

    read = rest(
        opener,
        "/wpvibe/v1/file/read",
        {"path": "functions.php", "theme": "hello-elementor"},
    )
    content = read.get("content") or ""
    if not content:
        print("Nelze načíst functions.php:", read)
        return

    new_content = content.replace("info@letani-zabreh.cz", "klub@letani-zabreh.cz")
    new_content = new_content.replace("it2529@sspu-opava.cz", "klub@letani-zabreh.cz")
    if new_content == content:
        print("functions.php e-maily už jsou OK")
    else:
        r = rest(
            opener,
            "/wpvibe/v1/file/edit",
            {
                "path": "functions.php",
                "theme": "hello-elementor",
                "old_content": content,
                "new_content": new_content,
            },
        )
        print("file edit:", r.get("success", r))

    pub = rest(opener, "/wpvibe/v1/draft-theme/publish", {})
    print("publish:", pub.get("success", pub))


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.MozillaCookieJar()))
    login(opener)

    post_ids = _mod.parse_post_ids(
        cli(opener, "post list --post_type=post --format=ids --posts_per_page=10").get("stdout")
    ) if hasattr(_mod, "parse_post_ids") else [720, 719, 718]
    if len(post_ids) < 3:
        post_ids = [720, 719, 718]
    print("Příspěvky:", post_ids)

    for pid, fn in [(440, _mod.patch_kontakt), (509, _mod.patch_onas), (436, _mod.patch_sluzby)]:
        print(f"Stránka {pid}...")
        el = load_elementor(opener, pid)
        fn(el)
        r = save_elementor(opener, pid, el)
        print(" ", r.get("stdout") or r)

    print("Úvod 517...")
    el517 = load_elementor(opener, 517)
    _mod.patch_uvod(el517, post_ids)
    r = save_elementor(opener, 517, el517)
    print(" ", r.get("stdout") or r)

    print("functions.php...")
    patch_functions_via_draft(opener)

    cli(opener, "cache flush", confirm=True)
    cli(opener, "elementor flush-css", confirm=True)
    print("Hotovo.")


if __name__ == "__main__":
    main()
