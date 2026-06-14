#!/usr/bin/env python3
"""Doplnění kontaktu, O nás, služeb, aktualit, galerie 2 sloupce, e-mailů."""
import base64
import copy
import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error

SITE = "https://it2529.sspu-opava.eu"
USER = os.environ.get("WP_USER", "it2529")
PWD = os.environ.get("WP_PASS", "")
COOKIE = "/tmp/wp-it2529-cookies6.txt"

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

CONTACT_EDITOR = (
    '<p style="color:#555;font-size:15px;line-height:1.8;margin:0 0 16px;">'
    "<strong>Sídlo klubu</strong><br>"
    "Klub létání Zábřeh – Dolní Benešov, z.s.<br>"
    "Dobrovského 874/29, Přívoz<br>"
    "702 00 Ostrava</p>"
    '<p style="color:#555;font-size:15px;line-height:1.8;margin:0 0 16px;">'
    "<strong>Letiště</strong><br>"
    "Letiště Zábřeh (LKZA)<br>"
    "Dolní Benešov<br>"
    "747 22</p>"
    '<p style="color:#555;font-size:15px;line-height:1.8;margin:0;">'
    "<strong>IČ:</strong> 03522245<br>"
    "<strong>Bankovní spojení:</strong> Fio banka, č. ú. 2100690327/2010</p>"
)

POSTS = [
    {
        "title": "Jubilejní 10. ročník Hangár párty Letiště Zábřeh",
        "content": (
            "<p>Klub létání Zábřeh zve na tradiční Hangár párty — setkání pilotů, "
            " přátel létání a všech, kdo rádi tráví čas u letadel. Oslavíme desátý ročník "
            " akce na letišti LKZA v Dolním Benešově.</p>"
            "<p>Program zahrnuje prohlídku hangáru, posezení u grilu a sdílení "
            " leteckých příběhů. Sledujte náš Instagram pro aktuální termín a detaily.</p>"
        ),
        "date": "2025-08-15 10:00:00",
    },
    {
        "title": "Dětský letecký den – Základní škola Bolatice",
        "content": (
            "<p>Ve spolupráci se Základní školou Bolatice pořádáme dětský letecký den. "
            " Žáci se seznámí s letadly klubu, bezpečností na letišti a principy létání.</p>"
            "<p>Akce probíhá přímo na letišti Zábřeh. Více informací a rezervace termínů "
            " získáte na e-mailu <a href=\"mailto:klub@letani-zabreh.cz\">klub@letani-zabreh.cz</a>.</p>"
        ),
        "date": "2025-05-20 10:00:00",
    },
    {
        "title": "Letecký den na letišti Náměšť nad Oslavou",
        "content": (
            "<p>Členové klubu se zúčastnili leteckého dne na letišti Náměšť nad Oslavou. "
            " Setkání pilotů z celé republiky, ukázky letadel a sdílení zkušeností z ULL i VFR výcviku.</p>"
            "<p>Podobné akce plánujeme i na našem domovském letišti — sledujte aktuality klubu.</p>"
        ),
        "date": "2025-06-01 10:00:00",
    },
]


def find_widget(elements, wid):
    for el in elements:
        if el.get("id") == wid:
            return el
        if el.get("elements"):
            found = find_widget(el["elements"], wid)
            if found:
                return found
    return None


def update_meta_json(opener, nonce, pid, elements):
    payload = json.dumps(elements, ensure_ascii=False)
    b64 = base64.b64encode(payload.encode()).decode()
    path = f"/tmp/wp-el-{pid}.b64"
    # Write base64 to server file in chunks (avoids request size limits)
    chunks = [b64[i : i + 12000] for i in range(0, len(b64), 12000)]

    def run_eval(php, confirm=True):
        body = {"command": f'eval "{php}"', "confirm_write": confirm}
        req = urllib.request.Request(
            f"{SITE}/index.php?rest_route=/wpvibe/v1/cli/run",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-WP-Nonce": nonce},
        )
        try:
            return json.loads(opener.open(req).read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "body": e.read().decode()[:500]}

    run_eval(f"file_put_contents('{path}', '');")
    for i, chunk in enumerate(chunks):
        esc = chunk.replace("\\", "\\\\").replace('"', '\\"')
        r = run_eval(f'file_put_contents("{path}", "{esc}", FILE_APPEND); echo {i};')
        if r.get("error"):
            return r

    php = (
        f"$j=base64_decode(file_get_contents('{path}')); "
        f"update_post_meta({pid}, '_elementor_data', $j); "
        f"unlink('{path}'); echo 'ok';"
    )
    return run_eval(php)


def patch_kontakt(elements):
    icons = find_widget(elements, "eb333334")
    icons["settings"]["icon_list"] = [
        {
            "_id": "ic1",
            "text": "klub@letani-zabreh.cz",
            "selected_icon": {"value": "fas fa-envelope", "library": "fa-solid"},
            "link": {"url": "mailto:klub@letani-zabreh.cz"},
        },
        {
            "_id": "ic2",
            "text": "+420 737 871 590",
            "selected_icon": {"value": "fas fa-phone", "library": "fa-solid"},
            "link": {"url": "tel:+420737871590"},
        },
        {
            "_id": "ic3",
            "text": "LKZA Zábřeh, Dolní Benešov",
            "selected_icon": {"value": "fas fa-map-marker-alt", "library": "fa-solid"},
            "link": {"url": ""},
        },
        {
            "_id": "ic4",
            "text": "letani-zabreh.cz",
            "selected_icon": {"value": "fas fa-globe", "library": "fa-solid"},
            "link": {"url": "https://letani-zabreh.cz", "is_external": "on"},
        },
        {
            "_id": "ic5",
            "text": "@klub_letani_zabreh",
            "selected_icon": {"value": "fab fa-instagram", "library": "fa-brands"},
            "link": {
                "url": "https://www.instagram.com/klub_letani_zabreh/",
                "is_external": "on",
            },
        },
    ]
    find_widget(elements, "eb999999")["settings"]["editor"] = CONTACT_EDITOR
    html_w = find_widget(elements, "seofix440")
    html = html_w["settings"]["html"]
    html = re.sub(
        r'"email"\s*:\s*"[^"]*"',
        '"email": "klub@letani-zabreh.cz"',
        html,
    )
    html = re.sub(
        r'"telephone"\s*:\s*"[^"]*"',
        '"telephone": "+420737871590"',
        html,
    )
    if '"telephone"' not in html and "ContactPage" in html:
        html = html.replace(
            '"name": "Kontakt',
            '"telephone": "+420737871590", "email": "klub@letani-zabreh.cz", "name": "Kontakt',
            1,
        )
    html_w["settings"]["html"] = html


def fleet_container():
    card = lambda cid, title, desc: {
        "id": cid,
        "elType": "container",
        "settings": {
            "flex_direction": "column",
            "content_width": "full",
            "_flex_size": "grow",
            "width": {"unit": "%", "size": 48},
            "width_mobile": {"unit": "%", "size": 100},
            "background_background": "classic",
            "background_color": "#f8fafc",
            "border_border": "solid",
            "border_width": {"unit": "px", "top": 1, "right": 1, "bottom": 1, "left": 1, "isLinked": True},
            "border_color": "#e8eef5",
            "border_radius": {"unit": "px", "top": 12, "right": 12, "bottom": 12, "left": 12, "isLinked": True},
            "padding": {"unit": "px", "top": 28, "right": 24, "bottom": 28, "left": 24, "isLinked": True},
        },
        "elements": [
            {
                "id": cid + "h",
                "elType": "widget",
                "settings": {
                    "title": title,
                    "header_size": "h3",
                    "title_color": "#111827",
                    "typography_font_weight": "700",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": cid + "t",
                "elType": "widget",
                "settings": {"editor": desc},
                "elements": [],
                "widgetType": "text-editor",
            },
        ],
        "isInner": True,
    }
    return {
        "id": "onfleet1",
        "elType": "container",
        "settings": {
            "container_type": "flex",
            "flex_direction": "column",
            "content_width": "boxed",
            "boxed_width": {"unit": "px", "size": 1100},
            "background_background": "classic",
            "background_color": "#ffffff",
            "padding": {"unit": "px", "top": 72, "right": 48, "bottom": 48, "left": 48, "isLinked": False},
            "padding_mobile": {"unit": "px", "top": 48, "right": 24, "bottom": 32, "left": 24, "isLinked": False},
            "flex_align_items": "center",
        },
        "elements": [
            {
                "id": "onfl001",
                "elType": "widget",
                "settings": {
                    "editor": '<p style="color:#b80000;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;text-align:center;">FLOTA</p>'
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "onfl002",
                "elType": "widget",
                "settings": {
                    "title": "Čím létáme",
                    "header_size": "h2",
                    "align": "center",
                    "title_color": "#0f0f0f",
                    "typography_font_size": {"unit": "px", "size": 32},
                    "typography_font_weight": "800",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": "onfl003",
                "elType": "widget",
                "settings": {
                    "editor": '<p style="text-align:center;color:#555;font-size:17px;line-height:1.75;margin:16px 0 36px;">V hangáru na LKZA provozujeme dvě ultralehká letadla pro výcvik i vyhlídkové lety.</p>'
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "onfl004",
                "elType": "container",
                "settings": {
                    "flex_direction": "row",
                    "content_width": "full",
                    "flex_wrap": "wrap",
                    "gap": {"unit": "px", "size": 24},
                    "flex_justify_content": "center",
                },
                "elements": [
                    card(
                        "onflc1",
                        "DV-1 SKYLARK",
                        '<p style="color:#555;font-size:16px;line-height:1.75;margin:0;">Ultralehký dvoumístný <strong>dolnoplošník</strong>. Stabilní let, vhodný pro výcvik ULL i vyhlídkové prolety nad okolím letiště.</p>',
                    ),
                    card(
                        "onflc2",
                        "GP-7 SKYLEADER",
                        '<p style="color:#555;font-size:16px;line-height:1.75;margin:0;">Ultralehký dvoumístný <strong>hornoplošník</strong>. Moderní kokpit a pohodlné sedadla pro instruktora a žáka.</p>',
                    ),
                ],
                "isInner": True,
            },
        ],
        "isInner": False,
    }


def vycvik_container():
    return {
        "id": "ontrain1",
        "elType": "container",
        "settings": {
            "container_type": "flex",
            "flex_direction": "column",
            "content_width": "boxed",
            "boxed_width": {"unit": "px", "size": 900},
            "background_background": "classic",
            "background_color": "#f8fafc",
            "padding": {"unit": "px", "top": 56, "right": 48, "bottom": 72, "left": 48, "isLinked": False},
            "padding_mobile": {"unit": "px", "top": 40, "right": 24, "bottom": 56, "left": 24, "isLinked": False},
            "flex_align_items": "center",
        },
        "elements": [
            {
                "id": "ontr001",
                "elType": "widget",
                "settings": {
                    "editor": '<p style="color:#b80000;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;text-align:center;">VÝCVIK</p>'
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "ontr002",
                "elType": "widget",
                "settings": {
                    "title": "Výcvik ULL a VFR",
                    "header_size": "h2",
                    "align": "center",
                    "title_color": "#0f0f0f",
                    "typography_font_size": {"unit": "px", "size": 28},
                    "typography_font_weight": "800",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": "ontr003",
                "elType": "widget",
                "settings": {
                    "editor": (
                        '<p style="text-align:center;color:#555;font-size:17px;line-height:1.85;margin:16px 0 0;">'
                        "Nabízíme výcvik pilota ultralehkých letadel (ULL) i navazující výcvik VFR. "
                        "Teorie i praktický výcvik probíhá na letišti LKZA Zábřeh s certifikovanými instruktory. "
                        'Více informací a přihlášky: <a href="mailto:klub@letani-zabreh.cz">klub@letani-zabreh.cz</a> '
                        'nebo telefon <a href="tel:+420737871590">+420 737 871 590</a>.</p>'
                    )
                },
                "elements": [],
                "widgetType": "text-editor",
            },
        ],
        "isInner": False,
    }


def patch_onas(elements):
    if find_widget(elements, "onfleet1"):
        print("  O nás: sekce Čím létáme už existuje")
    else:
        idx = next(i for i, el in enumerate(elements) if el.get("id") == "onstory1")
        elements.insert(idx, fleet_container())
        elements.insert(idx + 1, vycvik_container())


def vycvik_service_card():
    return {
        "id": "scvyc01",
        "elType": "container",
        "settings": {
            "flex_direction": "column",
            "content_width": "full",
            "_flex_size": "grow",
            "width": {"unit": "%", "size": 32},
            "background_background": "classic",
            "background_color": "#ffffff",
            "border_border": "solid",
            "border_width": {"unit": "px", "top": 1, "right": 1, "bottom": 1, "left": 1, "isLinked": True},
            "border_color": "#e8e8e8",
            "border_radius": {"unit": "px", "top": 16, "right": 16, "bottom": 16, "left": 16, "isLinked": True},
            "padding": {"unit": "px", "top": 36, "right": 28, "bottom": 36, "left": 28, "isLinked": False},
            "width_mobile": {"unit": "%", "size": 100},
            "box_shadow_box_shadow_type": "yes",
            "box_shadow_box_shadow": {"horizontal": 0, "vertical": 8, "blur": 30, "spread": 0, "color": "rgba(0,0,0,0.05)"},
        },
        "elements": [
            {
                "id": "scvyc02",
                "elType": "widget",
                "settings": {
                    "editor": '<p style="color:#b80000;font-size:11px;font-weight:700;letter-spacing:2px;margin:0 0 12px;">VÝCVIK</p>'
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "scvyc03",
                "elType": "widget",
                "settings": {
                    "title": "Výcvik ULL / VFR",
                    "title_color": "#111827",
                    "typography_font_size": {"unit": "px", "size": 22},
                    "typography_font_weight": "700",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": "scvyc04",
                "elType": "widget",
                "settings": {
                    "editor": (
                        '<p style="color:#444;font-size:15px;line-height:1.7;">Kompletní výcvik pilota ultralehkých letadel '
                        "a navazující VFR na letišti LKZA.</p>"
                        '<ul style="color:#444;font-size:15px;line-height:1.9;margin-top:16px;">'
                        "<li>Teorie a praktický výcvik</li><li>Instruktoři s dlouholetou praxí</li>"
                        "<li>Letadla DV-1 Skylark a GP-7 Skyleader</li></ul>"
                    )
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "scvyc05",
                "elType": "widget",
                "settings": {
                    "text": "Mám zájem",
                    "link": {"url": "https://it2529.sspu-opava.eu/?page_id=440"},
                    "size": "md",
                    "background_color": "#0f0f0f",
                    "button_text_color": "#ffffff",
                    "border_radius": {"unit": "px", "top": 100, "right": 100, "bottom": 100, "left": 100, "isLinked": True},
                    "typography_text_transform": "none",
                    "align": "left",
                },
                "elements": [],
                "widgetType": "button",
            },
        ],
        "isInner": True,
    }


def patch_sluzby(elements):
    if find_widget(elements, "scvyc01"):
        print("  Služby: výcvik už existuje")
        return
    row = find_widget(elements, "sa555555")
    row["elements"].append(vycvik_service_card())
    for card in row["elements"]:
        card["settings"]["width"] = {"unit": "%", "size": 24}
        card["settings"]["width_tablet"] = {"unit": "%", "size": 48}


def aktuality_section(post_ids):
    cards = []
    titles = [
        "Jubilejní 10. ročník Hangár párty",
        "Dětský letecký den – ZŠ Bolatice",
        "Letecký den Náměšť nad Oslavou",
    ]
    for i, (pid, title) in enumerate(zip(post_ids, titles)):
        cid = f"aktC{i+1}"
        cards.append(
            {
                "id": cid,
                "elType": "container",
                "settings": {
                    "flex_direction": "column",
                    "width": {"unit": "%", "size": 32},
                    "width_mobile": {"unit": "%", "size": 100},
                    "background_background": "classic",
                    "background_color": "#ffffff",
                    "border_border": "solid",
                    "border_width": {"unit": "px", "top": 1, "right": 1, "bottom": 1, "left": 1, "isLinked": True},
                    "border_color": "#e8eef5",
                    "border_radius": {"unit": "px", "top": 12, "right": 12, "bottom": 12, "left": 12, "isLinked": True},
                    "padding": {"unit": "px", "top": 24, "right": 20, "bottom": 24, "left": 20, "isLinked": True},
                },
                "elements": [
                    {
                        "id": cid + "h",
                        "elType": "widget",
                        "settings": {
                            "title": title,
                            "header_size": "h3",
                            "title_color": "#111827",
                            "typography_font_size": {"unit": "px", "size": 18},
                            "typography_font_weight": "700",
                        },
                        "elements": [],
                        "widgetType": "heading",
                    },
                    {
                        "id": cid + "b",
                        "elType": "widget",
                        "settings": {
                            "text": "Číst více",
                            "link": {"url": f"{SITE}/?p={pid}"},
                            "size": "sm",
                            "background_color": "transparent",
                            "button_text_color": "#1a73e8",
                            "border_border": "none",
                            "typography_text_transform": "none",
                            "align": "left",
                        },
                        "elements": [],
                        "widgetType": "button",
                    },
                ],
                "isInner": True,
            }
        )
    return {
        "id": "aktual01",
        "elType": "container",
        "settings": {
            "flex_direction": "column",
            "content_width": "boxed",
            "boxed_width": {"unit": "px", "size": 1200},
            "background_background": "classic",
            "background_color": "#f8fafc",
            "padding": {"unit": "px", "top": 72, "right": 48, "bottom": 72, "left": 48, "isLinked": False},
            "padding_mobile": {"unit": "px", "top": 48, "right": 24, "bottom": 48, "left": 24, "isLinked": False},
        },
        "elements": [
            {
                "id": "akt001",
                "elType": "widget",
                "settings": {
                    "editor": '<p style="color:#b80000;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;text-align:center;">NOVINKY</p>'
                },
                "elements": [],
                "widgetType": "text-editor",
            },
            {
                "id": "akt002",
                "elType": "widget",
                "settings": {
                    "title": "Aktuality a akce",
                    "header_size": "h2",
                    "align": "center",
                    "title_color": "#0f0f0f",
                    "typography_font_size": {"unit": "px", "size": 32},
                    "typography_font_weight": "800",
                },
                "elements": [],
                "widgetType": "heading",
            },
            {
                "id": "akt003",
                "elType": "container",
                "settings": {
                    "flex_direction": "row",
                    "flex_wrap": "wrap",
                    "gap": {"unit": "px", "size": 24},
                    "content_width": "full",
                    "flex_justify_content": "center",
                },
                "elements": cards,
                "isInner": True,
            },
        ],
        "isInner": False,
    }


def patch_uvod(elements, post_ids):
    w = find_widget(elements, "seofix517")
    html = w["settings"]["html"]
    if "gal00001-two-col" not in html and "</style>" in html:
        w["settings"]["html"] = html.replace("</style>", GAL_CSS + "\n</style>", 1)
    if not find_widget(elements, "aktual01"):
        gal_idx = next(i for i, el in enumerate(elements) if el.get("id") == "gal00001")
        elements.insert(gal_idx, aktuality_section(post_ids))


def patch_functions_php(opener, nonce):
    php = r"""
$path = get_stylesheet_directory() . '/functions.php';
$c = file_get_contents($path);
$c = str_replace('info@letani-zabreh.cz', 'klub@letani-zabreh.cz', $c);
$c = str_replace('it2529@sspu-opava.cz', 'klub@letani-zabreh.cz', $c);
file_put_contents($path, $c);
echo 'functions.php updated';
"""
    b64 = base64.b64encode(php.encode()).decode()
    body = {
        "command": f"eval \"eval(base64_decode('{b64}'));\"",
        "confirm_write": True,
    }
    req = urllib.request.Request(
        f"{SITE}/index.php?rest_route=/wpvibe/v1/cli/run",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-WP-Nonce": nonce},
    )
    return json.loads(opener.open(req).read().decode())


def main():
    if not PWD:
        raise SystemExit("Nastav WP_PASS")

    cj = http.cookiejar.MozillaCookieJar(COOKIE)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        cj.load(ignore_discard=True, ignore_expires=True)
    except FileNotFoundError:
        pass
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

    post_ids = []
    def parse_post_ids(raw):
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

    existing_ids = parse_post_ids(
        cli("post list --post_type=post --format=ids --posts_per_page=10").get("stdout")
    )

    if len(existing_ids) >= 3:
        post_ids = existing_ids[:3]
        print(f"  Používám existující příspěvky: {post_ids}")
    else:
        for p in POSTS:
            title = p["title"].replace("'", "\\'")
            content = p["content"].replace("'", "\\'").replace("\n", " ")
            r = cli(
                f"post create --post_type=post --post_status=publish "
                f"--post_title='{title}' --post_content='{content}' "
                f"--post_date='{p['date']}' --porcelain",
                confirm=True,
            )
            pid = (r.get("stdout") or "").strip()
            if pid.isdigit():
                post_ids.append(int(pid))
                print(f"  Příspěvek vytvořen: {pid} — {p['title'][:40]}")
            else:
                try:
                    data = json.loads(pid)
                    post_ids.append(int(data["ID"]))
                    print(f"  Příspěvek vytvořen: {data['ID']} — {p['title'][:40]}")
                except (json.JSONDecodeError, KeyError, TypeError):
                    print("  Chyba příspěvku:", r)

    if len(post_ids) < 3 and existing_ids:
        post_ids = existing_ids[:3]

    def load_elementor(pid):
        r = cli(f"post meta get {pid} _elementor_data --format=json")
        return json.loads(r.get("stdout") or "[]")

    for pid, patch_fn in [
        (440, patch_kontakt),
        (509, patch_onas),
        (436, patch_sluzby),
    ]:
        print(f"Ukládám stránku {pid}...")
        elements = load_elementor(pid)
        patch_fn(elements)
        r = update_meta_json(opener, nonce, pid, elements)
        print(f"  => {r.get('stdout', r)}")

    print("Ukládám úvod (517)...")
    elements517 = load_elementor(517)
    patch_uvod(elements517, post_ids)
    r = update_meta_json(opener, nonce, 517, elements517)
    print(f"  => {r.get('stdout', r)}")

    print("Upravuji functions.php (e-maily)...")
    r = patch_functions_php(opener, nonce)
    print(f"  => {r.get('stdout', r)}")

    cli("cache flush", confirm=True)
    cli("elementor flush-css", confirm=True)
    print("\nHotovo — vše nasazeno.")


if __name__ == "__main__":
    main()
