#!/usr/bin/env python3
"""Nahraje PHP deploy skript a spustí ho na serveru."""
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
COOKIE = "/tmp/wp-it2529-cookies6.txt"
DEPLOY_PHP = os.path.join(os.path.dirname(__file__), "klz-deploy-content.php")


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
    return re.search(
        r'wpApiSettings\s*=\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"', admin
    ).group(1)


def cli(opener, nonce, cmd, confirm=False):
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
        return {"error": e.code, "body": e.read().decode()[:600]}


def upload_and_run(opener, nonce):
    php = open(DEPLOY_PHP, encoding="utf-8").read()
    b64 = base64.b64encode(php.encode()).decode()
    path = "klz-deploy-content.php"
    chunks = [b64[i : i + 10000] for i in range(0, len(b64), 10000)]

    # První chunk přepíše soubor, další appendují (každý příkaz = jeden výraz bez ;)
    for i, chunk in enumerate(chunks):
        esc = chunk.replace("\\", "\\\\").replace("'", "\\'")
        if i == 0:
            expr = f"file_put_contents(ABSPATH.'{path}',base64_decode('{esc}'))"
        else:
            expr = f"file_put_contents(ABSPATH.'{path}',base64_decode('{esc}'),FILE_APPEND)"
        r = cli(opener, nonce, f"eval {expr}", confirm=True)
        if r.get("error"):
            return r
        print(f"  chunk {i+1}/{len(chunks)} ok")

    r = cli(opener, nonce, f"eval include(ABSPATH.'{path}')", confirm=True)
    cli(opener, nonce, f"eval unlink(ABSPATH.'{path}')", confirm=True)
    return r


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")
    cj = http.cookiejar.MozillaCookieJar(COOKIE)
    try:
        cj.load(ignore_discard=True, ignore_expires=True)
    except FileNotFoundError:
        pass
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    nonce = login(opener)
    print("Nahrávám a spouštím deploy skript...")
    r = upload_and_run(opener, nonce)
    print(r.get("stdout") or r)
    cli(opener, nonce, "cache flush", confirm=True)
    cli(opener, nonce, "elementor flush-css", confirm=True)
    print("Hotovo.")


if __name__ == "__main__":
    main()
