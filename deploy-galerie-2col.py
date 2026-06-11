#!/usr/bin/env python3
"""Nasadí 2-sloupcový layout galerie na úvod (page 517)."""
import http.cookiejar
import json
import re
import urllib.parse
import urllib.request

import os

SITE = "https://it2529.sspu-opava.eu"
USER = os.environ.get("WP_USER", "it2529")
PWD = os.environ.get("WP_PASS", "")

GAL_CSS = """
@media (min-width: 768px) {
  body.page-id-517 .e-con[data-id="gal00001"] > .e-con-inner {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 24px !important;
  }
  body.page-id-517 .e-con[data-id="gal00001"] .elementor-element-gal00002,
  body.page-id-517 .e-con[data-id="gal00001"] .elementor-element-gal00003,
  body.page-id-517 .e-con[data-id="gal00001"] .elementor-element-gal00005 {
    grid-column: 1 / -1 !important;
  }
  body.page-id-517 .e-con[data-id="gal00001"] [data-id="f151ad9"],
  body.page-id-517 .e-con[data-id="gal00001"] [data-id="e9f1b47"],
  body.page-id-517 .e-con[data-id="gal00001"] [data-id="e8c51ae"],
  body.page-id-517 .e-con[data-id="gal00001"] [data-id="e6aaa59"] {
    width: 100% !important;
    max-width: 100% !important;
  }
  body.page-id-517 .e-con[data-id="gal00001"] .elementor-widget-image img {
    width: 100% !important;
    height: 260px !important;
    object-fit: cover !important;
    border-radius: 12px !important;
  }
}
@media (max-width: 767px) {
  body.page-id-517 .e-con[data-id="gal00001"] > .e-con-inner {
    display: flex !important;
    flex-direction: column !important;
    gap: 16px !important;
  }
}
"""


def find_widget(elements, wid):
    for el in elements:
        if el.get("id") == wid:
            return el
        if el.get("elements"):
            found = find_widget(el["elements"], wid)
            if found:
                return found
    return None


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS (heslo) a spusť znovu.")
    cj = http.cookiejar.MozillaCookieJar("/tmp/wp-it2529-cookies5.txt")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
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

    nonce = re.search(
        r'wpApiSettings\s*=\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"', admin
    ).group(1)

    def cli(cmd, confirm=False):
        body = {"command": cmd}
        if confirm:
            body["confirm_write"] = True
        req = urllib.request.Request(
            f"{SITE}/index.php?rest_route=/wpvibe/v1/cli/run",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-WP-Nonce": nonce},
        )
        return json.loads(opener.open(req).read().decode())

    raw = cli("post meta get 517 _elementor_data --format=json")
    stdout = raw.get("stdout") or raw.get("result") or ""
    if isinstance(stdout, str):
        elements = json.loads(stdout)
    else:
        elements = stdout

    widget = find_widget(elements, "seofix517")
    if not widget:
        raise SystemExit("Widget seofix517 nenalezen")

    html = widget["settings"]["html"]
    marker = "gal00001-two-col"
    if marker in html:
        print("CSS už je nasazené — hotovo.")
        return

    if "</style>" not in html:
        raise SystemExit("Chybí </style> v seofix517")

    inject = f'<style id="{marker}">{GAL_CSS}</style>'
    widget["settings"]["html"] = html.replace("</style>", GAL_CSS + "\n</style>", 1)

    payload = json.dumps(elements, ensure_ascii=False)
    payload_b64 = __import__("base64").b64encode(payload.encode()).decode()
    cli(f"eval \"update_post_meta(517, '_elementor_data', base64_decode('{payload_b64}')); echo 'ok';\"", confirm=True)
    cli("cache flush", confirm=True)
    print("Hotovo — galerie 2 sloupce na desktopu nasazena.")


if __name__ == "__main__":
    main()
