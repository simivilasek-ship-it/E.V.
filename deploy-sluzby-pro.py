#!/usr/bin/env python3
"""Profesionální úprava stránky Služby (436)."""
import base64
import importlib.util
import json
import os

_spec = importlib.util.spec_from_file_location(
    "p", os.path.join(os.path.dirname(__file__), "deploy-content-updates.py")
)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

_spec2 = importlib.util.spec_from_file_location(
    "d", os.path.join(os.path.dirname(__file__), "deploy-pages-api.py")
)
D = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(D)

SITE = D.SITE

LABEL = (
    '<p style="color:#b80000;font-size:11px;font-weight:700;'
    'letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;">{text}</p>'
)

CARD_W = {
    "width": {"unit": "%", "size": 48},
    "width_tablet": {"unit": "%", "size": 48},
    "width_mobile": {"unit": "%", "size": 100},
}

SLUZBY_CSS = """<style id="klz-sluzby-grid">
@media (min-width:768px){
  body.page-id-436 .e-con[data-id="sa555555"]{display:flex!important;flex-wrap:wrap!important;justify-content:center!important;gap:24px!important;align-items:stretch!important}
  body.page-id-436 .e-con[data-id="sa666666"],
  body.page-id-436 .e-con[data-id="sb111111"],
  body.page-id-436 .e-con[data-id="sc111111"],
  body.page-id-436 .e-con[data-id="scvyc01"]{
    width:calc(50% - 16px)!important;max-width:calc(50% - 16px)!important;
    flex:0 0 calc(50% - 16px)!important;box-sizing:border-box!important;
    display:flex!important;flex-direction:column!important;align-items:center!important;
    text-align:center!important;min-height:420px!important}
  body.page-id-436 .e-con[data-id="sa666666"] ul,
  body.page-id-436 .e-con[data-id="sb111111"] ul,
  body.page-id-436 .e-con[data-id="sc111111"] ul,
  body.page-id-436 .e-con[data-id="scvyc01"] ul{text-align:left!important;display:inline-block!important;margin:0 auto!important}
  body.page-id-436 .e-con[data-id="sa666666"] .elementor-widget-button,
  body.page-id-436 .e-con[data-id="sb111111"] .elementor-widget-button,
  body.page-id-436 .e-con[data-id="sc111111"] .elementor-widget-button,
  body.page-id-436 .e-con[data-id="scvyc01"] .elementor-widget-button{
    margin-top:auto!important;width:100%!important;display:flex!important;justify-content:center!important}
  body.page-id-436 .e-con[data-id="sa666666"] .elementor-button-wrapper,
  body.page-id-436 .e-con[data-id="sb111111"] .elementor-button-wrapper,
  body.page-id-436 .e-con[data-id="sc111111"] .elementor-button-wrapper,
  body.page-id-436 .e-con[data-id="scvyc01"] .elementor-button-wrapper{
    display:flex!important;justify-content:center!important;width:100%!important;margin:0!important}
}
@media (max-width:767px){
  body.page-id-436 .e-con[data-id="sa666666"],
  body.page-id-436 .e-con[data-id="sb111111"],
  body.page-id-436 .e-con[data-id="sc111111"],
  body.page-id-436 .e-con[data-id="scvyc01"]{width:100%!important;max-width:100%!important}
}
</style>"""

MU_SLUZBY_CSS = r"""
add_action('wp_head', function () {
    if (!is_page(436)) return;
    echo '<style id="klz-sluzby-mu">';
    echo '@media(min-width:768px){';
    echo '.page-id-436 .e-con[data-id="sa555555"]{display:flex!important;flex-wrap:wrap!important;justify-content:center!important;gap:24px!important}';
    echo '.page-id-436 .e-con[data-id="sa666666"],.page-id-436 .e-con[data-id="sb111111"],';
    echo '.page-id-436 .e-con[data-id="sc111111"],.page-id-436 .e-con[data-id="scvyc01"]{';
    echo 'width:calc(50% - 16px)!important;max-width:calc(50% - 16px)!important;flex:0 0 calc(50% - 16px)!important;';
    echo 'display:flex!important;flex-direction:column!important;align-items:center!important;text-align:center!important;min-height:420px!important}';
    echo '.page-id-436 .e-con[data-id="sa666666"] .elementor-widget-button,';
    echo '.page-id-436 .e-con[data-id="sb111111"] .elementor-widget-button,';
    echo '.page-id-436 .e-con[data-id="sc111111"] .elementor-widget-button,';
    echo '.page-id-436 .e-con[data-id="scvyc01"] .elementor-widget-button{margin-top:auto!important;width:100%}';
    echo '}';
    echo '</style>';
}, 99);
"""


def patch_sluzby_pro(elements):
    P.find_widget(elements, "sa333333")["settings"]["editor"] = (
        '<p style="text-align:center;color:#555;font-size:18px;line-height:1.75;max-width:720px;margin:0 auto;">'
        "Vyhlídkové lety a výcvik pilotů na letišti LKZA Zábřeh. Ať hledáte první let nad krajinou, "
        "dárek pro blízké, nebo cestu k průkazu pilota ULL — domluvíme termín podle počasí a vašich přání.</p>"
    )

    cards = {
        "sa666666": {
            "label": "Vyhlídkový let",
            "title": "Krátký let",
            "desc": (
                '<p style="color:#444;font-size:15px;line-height:1.7;margin:0 0 12px;">'
                "<strong>15–20 minut</strong> ve vzduchu. Ideální jako první let nebo rychlý dárek.</p>"
                '<ul style="color:#444;font-size:15px;line-height:1.85;margin:0;padding-left:18px;">'
                "<li>Okruh nad okolím letiště LKZA</li>"
                "<li>Bezpečný let s instruktorem</li>"
                "<li>Možnost focení z kokpitu</li></ul>"
            ),
            "btn": "Rezervovat",
        },
        "sb111111": {
            "label": "Nejoblíbenější",
            "title": "Prodloužený let",
            "desc": (
                '<p style="color:#444;font-size:15px;line-height:1.7;margin:0 0 12px;">'
                "<strong>30–45 minut</strong> nad Moravskoslezskem. Více času na výhledy a delší trasu.</p>"
                '<ul style="color:#444;font-size:15px;line-height:1.85;margin:0;padding-left:18px;">'
                "<li>Trasa dle vašich přání a počasí</li>"
                "<li>Přelety nad Hlučínskem a okolím</li>"
                "<li>Vhodné pro dva cestující</li></ul>"
            ),
            "btn": "Rezervovat",
            "highlight": True,
        },
        "sc111111": {
            "label": "Dárkový poukaz",
            "title": "Let jako dárek",
            "desc": (
                '<p style="color:#444;font-size:15px;line-height:1.7;margin:0 0 12px;">'
                "Dárkový poukaz na vyhlídkový let. Platnost <strong>12 měsíců</strong>, termín si obdarovaný zvolí sám.</p>"
                '<ul style="color:#444;font-size:15px;line-height:1.85;margin:0;padding-left:18px;">'
                "<li>Originální dárek k narozeninám nebo výročí</li>"
                "<li>Vhodné pro páry i rodinu</li>"
                "<li>Osobní předání nebo zaslání e-mailem</li></ul>"
            ),
            "btn": "Objednat poukaz",
        },
        "scvyc01": {
            "label": "Výcvik",
            "title": "Výcvik ULL / VFR",
            "desc": (
                '<p style="color:#444;font-size:15px;line-height:1.7;margin:0 0 12px;">'
                "Kompletní výcvik pilota ultralehkých letadel (ULL) a navazující VFR na letišti LKZA Zábřeh.</p>"
                '<ul style="color:#444;font-size:15px;line-height:1.85;margin:0;padding-left:18px;">'
                "<li>Teorie i praktický výcvik s instruktorem</li>"
                "<li>Letadla DV-1 SKYLARK a GP-7 SKYLEADER</li>"
                "<li>Individuální tempo dle vašich možností</li></ul>"
            ),
            "btn": "Mám zájem",
        },
    }

    id_map = {
        "sa666666": ("saeye01", "sa777777", "sa888888", "sa999999"),
        "sb111111": ("sb222222", "sb333333", "sb444444", "sb555555"),
        "sc111111": ("sceye01", "sc222222", "sc333333", "sc444444"),
        "scvyc01": ("scvyc02", "scvyc03", "scvyc04", "scvyc05"),
    }

    kontakt = f"{SITE}/?pagename=kontakt"
    row = P.find_widget(elements, "sa555555")
    row["settings"]["flex_justify_content"] = "center"

    for cid, data in cards.items():
        card = P.find_widget(elements, cid)
        card["settings"].update(CARD_W)
        if data.get("highlight"):
            card["settings"]["border_border"] = "solid"
            card["settings"]["border_width"] = {
                "unit": "px", "top": 2, "right": 2, "bottom": 2, "left": 2, "isLinked": True
            }
            card["settings"]["border_color"] = "#b80000"
        label_id, title_id, desc_id, btn_id = id_map[cid]
        P.find_widget(elements, label_id)["settings"]["editor"] = LABEL.format(text=data["label"])
        P.find_widget(elements, title_id)["settings"]["title"] = data["title"]
        P.find_widget(elements, desc_id)["settings"]["editor"] = data["desc"]
        btn = P.find_widget(elements, btn_id)
        btn["settings"]["text"] = data["btn"]
        btn["settings"]["link"] = {"url": kontakt}
        btn["settings"]["align"] = "center"
        if cid == "sb111111":
            btn["settings"]["background_color"] = "#b80000"

    P.find_widget(elements, "sd333333")["settings"]["editor"] = (
        '<p style="color:#b80000;font-size:11px;font-weight:700;letter-spacing:2px;'
        'text-transform:uppercase;margin:0 0 8px;text-align:center;">Jak to probíhá</p>'
    )
    P.find_widget(elements, "sd444444")["settings"]["title"] = "3 kroky k vašemu letu"
    P.find_widget(elements, "se444444")["settings"]["editor"] = (
        '<p style="color:rgba(255,255,255,0.75);font-size:14px;line-height:1.65;">'
        "Napište nám přes kontaktní formulář nebo e-mail. Poradíme s výběrem vhodného letu.</p>"
    )
    P.find_widget(elements, "se888888")["settings"]["editor"] = (
        '<p style="color:rgba(255,255,255,0.75);font-size:14px;line-height:1.65;">'
        "Domluvíme termín podle počasí, dostupnosti letadla a vašich představ o trase.</p>"
    )
    P.find_widget(elements, "sf333333")["settings"]["editor"] = (
        '<p style="color:rgba(255,255,255,0.75);font-size:14px;line-height:1.65;">'
        "Přijďte na letiště Zábřeh (LKZA), absolvujte briefing a vyrazíte do vzduchu.</p>"
    )

    css_w = P.find_widget(elements, "sluzcss1")
    if css_w:
        css_w["settings"]["html"] = SLUZBY_CSS
    else:
        elements.insert(0, {
            "id": "sluzcss1",
            "elType": "widget",
            "widgetType": "html",
            "settings": {"html": SLUZBY_CSS},
            "elements": [],
        })


def deploy_mu_sluzby_css(wp):
    path = "wp-content/mu-plugins/klz-stable.php"
    r = wp.cli(f'eval "echo base64_encode(file_get_contents(ABSPATH . \\"{path}\\"));"', confirm=True)
    raw = r.get("stdout", "").strip()
    if not raw:
        print("mu-plugin chybí, přeskakuji CSS")
        return
    import base64 as b64mod

    code = b64mod.b64decode(raw).decode("utf-8", "replace")
    marker = "/* KLZ sluzby css */"
    if marker not in code:
        code = code.rstrip() + "\n\n" + marker + MU_SLUZBY_CSS + "\n"
        esc = b64mod.b64encode(code.encode()).decode().replace("\\", "\\\\").replace('"', '\\"')
        runner = f"""add_action('init', function () {{
    file_put_contents(ABSPATH . '{path}', base64_decode('{esc}'));
    update_option('klz_sluzby_css_done', time());
}}, 1);
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


def deploy_elementor_page(wp, pid, elements, done_key):
    wp.cli(f"option delete {done_key}", confirm=True)
    b64 = base64.b64encode(json.dumps(elements, ensure_ascii=False).encode()).decode()
    prefix = f"klz_el{pid}"
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
    update_post_meta({pid}, '_elementor_data', wp_slash(wp_json_encode($data)));
    delete_post_meta({pid}, '_elementor_element_cache');
    update_option('{done_key}', time());
}}, 1);
"""
    s6 = wp.rest("GET", "/code-snippets/v1/snippets/6")
    orig6 = s6["code"]
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": runner, "active": True, "name": s6["name"], "scope": "global", "priority": 1},
    )
    wp.op.open(f"{SITE}/?pagename=sluzby").read(32768)
    wp.rest(
        "PUT",
        "/code-snippets/v1/snippets/6",
        {"code": orig6, "active": False, "name": s6["name"], "scope": "global"},
    )


def main():
    if not os.environ.get("WP_PASS"):
        raise SystemExit("Nastav WP_PASS")
    wp = D.WP()
    wp.login()
    el = wp.load_el(436)
    patch_sluzby_pro(el)
    deploy_elementor_page(wp, 436, el, "klz_sluzby_pro")
    deploy_mu_sluzby_css(wp)
    wp.cli("post meta delete 436 _elementor_element_cache", confirm=True)
    wp.cli("post meta delete 436 _elementor_css", confirm=True)
    wp.cli("elementor flush-css --regenerate", confirm=True)
    wp.cli("cache flush", confirm=True)
    wp.purge_cache()
    print("Služby hotovo.")


if __name__ == "__main__":
    main()
