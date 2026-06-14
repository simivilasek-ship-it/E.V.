<?php
/**
 * Jednorázový deploy: kontakt, O nás, služby, aktuality, galerie 2 sl., e-maily.
 */

function &klz_find_widget( array &$elements, string $id ) {
    foreach ( $elements as &$el ) {
        if ( ( $el['id'] ?? '' ) === $id ) {
            return $el;
        }
        if ( ! empty( $el['elements'] ) ) {
            $found = &klz_find_widget( $el['elements'], $id );
            if ( null !== $found ) {
                return $found;
            }
        }
    }
    $null = null;
    return $null;
}

function klz_save_elementor( int $post_id, array $elements ) {
    update_post_meta( $post_id, '_elementor_data', wp_slash( wp_json_encode( $elements ) ) );
    delete_post_meta( $post_id, '_elementor_element_cache' );
}

function klz_get_elementor( int $post_id ): array {
    $raw = get_post_meta( $post_id, '_elementor_data', true );
    $data = json_decode( $raw, true );
    return is_array( $data ) ? $data : array();
}

function klz_patch_kontakt( array $elements ): array {
    $icons = &klz_find_widget( $elements, 'eb333334' );
    if ( $icons ) {
        $icons['settings']['icon_list'] = array(
            array(
                '_id'           => 'ic1',
                'text'          => 'klub@letani-zabreh.cz',
                'selected_icon' => array( 'value' => 'fas fa-envelope', 'library' => 'fa-solid' ),
                'link'          => array( 'url' => 'mailto:klub@letani-zabreh.cz' ),
            ),
            array(
                '_id'           => 'ic2',
                'text'          => '+420 737 871 590',
                'selected_icon' => array( 'value' => 'fas fa-phone', 'library' => 'fa-solid' ),
                'link'          => array( 'url' => 'tel:+420737871590' ),
            ),
            array(
                '_id'           => 'ic3',
                'text'          => 'LKZA Zábřeh, Dolní Benešov',
                'selected_icon' => array( 'value' => 'fas fa-map-marker-alt', 'library' => 'fa-solid' ),
                'link'          => array( 'url' => '' ),
            ),
            array(
                '_id'           => 'ic4',
                'text'          => 'letani-zabreh.cz',
                'selected_icon' => array( 'value' => 'fas fa-globe', 'library' => 'fa-solid' ),
                'link'          => array( 'url' => 'https://letani-zabreh.cz', 'is_external' => 'on' ),
            ),
            array(
                '_id'           => 'ic5',
                'text'          => '@klub_letani_zabreh',
                'selected_icon' => array( 'value' => 'fab fa-instagram', 'library' => 'fa-brands' ),
                'link'          => array(
                    'url'          => 'https://www.instagram.com/klub_letani_zabreh/',
                    'is_external'  => 'on',
                ),
            ),
        );
    }

    $addr = &klz_find_widget( $elements, 'eb999999' );
    if ( $addr ) {
        $addr['settings']['editor'] =
            '<p style="color:#555;font-size:15px;line-height:1.8;margin:0 0 16px;"><strong>Sídlo klubu</strong><br>'
            . 'Klub létání Zábřeh – Dolní Benešov, z.s.<br>Dobrovského 874/29, Přívoz<br>702 00 Ostrava</p>'
            . '<p style="color:#555;font-size:15px;line-height:1.8;margin:0 0 16px;"><strong>Letiště</strong><br>'
            . 'Letiště Zábřeh (LKZA)<br>Dolní Benešov<br>747 22</p>'
            . '<p style="color:#555;font-size:15px;line-height:1.8;margin:0;"><strong>IČ:</strong> 03522245<br>'
            . '<strong>Bankovní spojení:</strong> Fio banka, č. ú. 2100690327/2010</p>';
    }

    $seo = &klz_find_widget( $elements, 'seofix440' );
    if ( $seo && ! empty( $seo['settings']['html'] ) ) {
        $html = $seo['settings']['html'];
        $html = preg_replace( '/"email"\s*:\s*"[^"]*"/', '"email": "klub@letani-zabreh.cz"', $html );
        $html = preg_replace( '/"telephone"\s*:\s*"[^"]*"/', '"telephone": "+420737871590"', $html );
        if ( strpos( $html, '"telephone"' ) === false ) {
            $html = str_replace(
                '"name": "Kontakt',
                '"telephone": "+420737871590", "email": "klub@letani-zabreh.cz", "name": "Kontakt',
                $html
            );
        }
        $seo['settings']['html'] = $html;
    }

    return $elements;
}

function klz_fleet_card( string $cid, string $title, string $desc ): array {
    return array(
        'id'       => $cid,
        'elType'   => 'container',
        'settings' => array(
            'flex_direction'       => 'column',
            'content_width'        => 'full',
            '_flex_size'           => 'grow',
            'width'                => array( 'unit' => '%', 'size' => 48 ),
            'width_mobile'         => array( 'unit' => '%', 'size' => 100 ),
            'background_background'=> 'classic',
            'background_color'     => '#f8fafc',
            'border_border'        => 'solid',
            'border_width'         => array( 'unit' => 'px', 'top' => 1, 'right' => 1, 'bottom' => 1, 'left' => 1, 'isLinked' => true ),
            'border_color'         => '#e8eef5',
            'border_radius'        => array( 'unit' => 'px', 'top' => 12, 'right' => 12, 'bottom' => 12, 'left' => 12, 'isLinked' => true ),
            'padding'              => array( 'unit' => 'px', 'top' => 28, 'right' => 24, 'bottom' => 28, 'left' => 24, 'isLinked' => true ),
        ),
        'elements' => array(
            array(
                'id' => $cid . 'h', 'elType' => 'widget', 'widgetType' => 'heading',
                'settings' => array( 'title' => $title, 'header_size' => 'h3', 'title_color' => '#111827', 'typography_font_weight' => '700' ),
                'elements' => array(),
            ),
            array(
                'id' => $cid . 't', 'elType' => 'widget', 'widgetType' => 'text-editor',
                'settings' => array( 'editor' => $desc ),
                'elements' => array(),
            ),
        ),
        'isInner' => true,
    );
}

function klz_patch_onas( array $elements ): array {
    if ( klz_find_widget( $elements, 'onfleet1' ) ) {
        return $elements;
    }

    $fleet = array(
        'id' => 'onfleet1', 'elType' => 'container', 'isInner' => false,
        'settings' => array(
            'container_type' => 'flex', 'flex_direction' => 'column', 'content_width' => 'boxed',
            'boxed_width' => array( 'unit' => 'px', 'size' => 1100 ),
            'background_background' => 'classic', 'background_color' => '#ffffff',
            'padding' => array( 'unit' => 'px', 'top' => 72, 'right' => 48, 'bottom' => 48, 'left' => 48, 'isLinked' => false ),
            'padding_mobile' => array( 'unit' => 'px', 'top' => 48, 'right' => 24, 'bottom' => 32, 'left' => 24, 'isLinked' => false ),
            'flex_align_items' => 'center',
        ),
        'elements' => array(
            array( 'id' => 'onfl001', 'elType' => 'widget', 'widgetType' => 'text-editor',
                'settings' => array( 'editor' => '<p style="color:#b80000;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;text-align:center;">FLOTA</p>' ),
                'elements' => array() ),
            array( 'id' => 'onfl002', 'elType' => 'widget', 'widgetType' => 'heading',
                'settings' => array( 'title' => 'Čím létáme', 'header_size' => 'h2', 'align' => 'center', 'title_color' => '#0f0f0f', 'typography_font_size' => array( 'unit' => 'px', 'size' => 32 ), 'typography_font_weight' => '800' ),
                'elements' => array() ),
            array( 'id' => 'onfl003', 'elType' => 'widget', 'widgetType' => 'text-editor',
                'settings' => array( 'editor' => '<p style="text-align:center;color:#555;font-size:17px;line-height:1.75;margin:16px 0 36px;">V hangáru na LKZA provozujeme dvě ultralehká letadla pro výcvik i vyhlídkové lety.</p>' ),
                'elements' => array() ),
            array(
                'id' => 'onfl004', 'elType' => 'container', 'isInner' => true,
                'settings' => array( 'flex_direction' => 'row', 'content_width' => 'full', 'flex_wrap' => 'wrap', 'gap' => array( 'unit' => 'px', 'size' => 24 ), 'flex_justify_content' => 'center' ),
                'elements' => array(
                    klz_fleet_card( 'onflc1', 'DV-1 SKYLARK', '<p style="color:#555;font-size:16px;line-height:1.75;margin:0;">Ultralehký dvoumístný <strong>dolnoplošník</strong>. Stabilní let, vhodný pro výcvik ULL i vyhlídkové prolety nad okolím letiště.</p>' ),
                    klz_fleet_card( 'onflc2', 'GP-7 SKYLEADER', '<p style="color:#555;font-size:16px;line-height:1.75;margin:0;">Ultralehký dvoumístný <strong>hornoplošník</strong>. Moderní kokpit a pohodlné sedadla pro instruktora a žáka.</p>' ),
                ),
            ),
        ),
    );

    $train = array(
        'id' => 'ontrain1', 'elType' => 'container', 'isInner' => false,
        'settings' => array(
            'container_type' => 'flex', 'flex_direction' => 'column', 'content_width' => 'boxed',
            'boxed_width' => array( 'unit' => 'px', 'size' => 900 ),
            'background_background' => 'classic', 'background_color' => '#f8fafc',
            'padding' => array( 'unit' => 'px', 'top' => 56, 'right' => 48, 'bottom' => 72, 'left' => 48, 'isLinked' => false ),
            'padding_mobile' => array( 'unit' => 'px', 'top' => 40, 'right' => 24, 'bottom' => 56, 'left' => 24, 'isLinked' => false ),
            'flex_align_items' => 'center',
        ),
        'elements' => array(
            array( 'id' => 'ontr001', 'elType' => 'widget', 'widgetType' => 'text-editor',
                'settings' => array( 'editor' => '<p style="color:#b80000;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;text-align:center;">VÝCVIK</p>' ),
                'elements' => array() ),
            array( 'id' => 'ontr002', 'elType' => 'widget', 'widgetType' => 'heading',
                'settings' => array( 'title' => 'Výcvik ULL a VFR', 'header_size' => 'h2', 'align' => 'center', 'title_color' => '#0f0f0f', 'typography_font_size' => array( 'unit' => 'px', 'size' => 28 ), 'typography_font_weight' => '800' ),
                'elements' => array() ),
            array( 'id' => 'ontr003', 'elType' => 'widget', 'widgetType' => 'text-editor',
                'settings' => array( 'editor' => '<p style="text-align:center;color:#555;font-size:17px;line-height:1.85;margin:16px 0 0;">Nabízíme výcvik pilota ultralehkých letadel (ULL) i navazující výcvik VFR. Teorie i praktický výcvik probíhá na letišti LKZA Zábřeh s certifikovanými instruktory. Více informací: <a href="mailto:klub@letani-zabreh.cz">klub@letani-zabreh.cz</a> nebo <a href="tel:+420737871590">+420 737 871 590</a>.</p>' ),
                'elements' => array() ),
        ),
    );

    foreach ( $elements as $i => $el ) {
        if ( ( $el['id'] ?? '' ) === 'onstory1' ) {
            array_splice( $elements, $i, 0, array( $fleet, $train ) );
            break;
        }
    }
    return $elements;
}

function klz_patch_sluzby( array $elements ): array {
    if ( klz_find_widget( $elements, 'scvyc01' ) ) {
        return $elements;
    }
    $row = &klz_find_widget( $elements, 'sa555555' );
    if ( ! $row ) {
        return $elements;
    }
    $row['elements'][] = array(
        'id' => 'scvyc01', 'elType' => 'container', 'isInner' => true,
        'settings' => array(
            'flex_direction' => 'column', 'content_width' => 'full', '_flex_size' => 'grow',
            'width' => array( 'unit' => '%', 'size' => 24 ), 'width_mobile' => array( 'unit' => '%', 'size' => 100 ),
            'background_background' => 'classic', 'background_color' => '#ffffff',
            'border_border' => 'solid', 'border_width' => array( 'unit' => 'px', 'top' => 1, 'right' => 1, 'bottom' => 1, 'left' => 1, 'isLinked' => true ),
            'border_color' => '#e8e8e8', 'border_radius' => array( 'unit' => 'px', 'top' => 16, 'right' => 16, 'bottom' => 16, 'left' => 16, 'isLinked' => true ),
            'padding' => array( 'unit' => 'px', 'top' => 36, 'right' => 28, 'bottom' => 36, 'left' => 28, 'isLinked' => false ),
        ),
        'elements' => array(
            array( 'id' => 'scvyc02', 'elType' => 'widget', 'widgetType' => 'text-editor', 'elements' => array(),
                'settings' => array( 'editor' => '<p style="color:#b80000;font-size:11px;font-weight:700;letter-spacing:2px;margin:0 0 12px;">VÝCVIK</p>' ) ),
            array( 'id' => 'scvyc03', 'elType' => 'widget', 'widgetType' => 'heading', 'elements' => array(),
                'settings' => array( 'title' => 'Výcvik ULL / VFR', 'title_color' => '#111827', 'typography_font_size' => array( 'unit' => 'px', 'size' => 22 ), 'typography_font_weight' => '700' ) ),
            array( 'id' => 'scvyc04', 'elType' => 'widget', 'widgetType' => 'text-editor', 'elements' => array(),
                'settings' => array( 'editor' => '<p style="color:#444;font-size:15px;line-height:1.7;">Kompletní výcvik pilota ultralehkých letadel a navazující VFR na letišti LKZA.</p><ul style="color:#444;font-size:15px;line-height:1.9;margin-top:16px;"><li>Teorie a praktický výcvik</li><li>Instruktoři s dlouholetou praxí</li><li>Letadla DV-1 Skylark a GP-7 Skyleader</li></ul>' ) ),
            array( 'id' => 'scvyc05', 'elType' => 'widget', 'widgetType' => 'button', 'elements' => array(),
                'settings' => array( 'text' => 'Mám zájem', 'link' => array( 'url' => 'https://it2529.sspu-opava.eu/?page_id=440' ), 'size' => 'md', 'background_color' => '#0f0f0f', 'button_text_color' => '#ffffff', 'border_radius' => array( 'unit' => 'px', 'top' => 100, 'right' => 100, 'bottom' => 100, 'left' => 100, 'isLinked' => true ), 'typography_text_transform' => 'none', 'align' => 'left' ) ),
        ),
    );
    foreach ( $row['elements'] as &$card ) {
        $card['settings']['width'] = array( 'unit' => '%', 'size' => 24 );
        $card['settings']['width_tablet'] = array( 'unit' => '%', 'size' => 48 );
    }
    return $elements;
}

function klz_ensure_posts(): array {
    $posts = array(
        array(
            'title'   => 'Jubilejní 10. ročník Hangár párty Letiště Zábřeh',
            'content' => '<p>Klub létání Zábřeh zve na tradiční Hangár párty na letišti LKZA v Dolním Benešově. Oslavíme desátý ročník akce — prohlídka hangáru, grilování a setkání pilotů.</p>',
            'date'    => '2025-08-15 10:00:00',
        ),
        array(
            'title'   => 'Dětský letecký den – Základní škola Bolatice',
            'content' => '<p>Ve spolupráci se ZŠ Bolatice pořádáme dětský letecký den na letišti Zábřeh. Kontakt: <a href="mailto:klub@letani-zabreh.cz">klub@letani-zabreh.cz</a>.</p>',
            'date'    => '2025-05-20 10:00:00',
        ),
        array(
            'title'   => 'Letecký den na letišti Náměšť nad Oslavou',
            'content' => '<p>Členové klubu se zúčastnili leteckého dne v Náměšti nad Oslavou — setkání pilotů, ukázky letadel a sdílení zkušeností z ULL i VFR výcviku.</p>',
            'date'    => '2025-06-01 10:00:00',
        ),
    );
    $ids = array();
    foreach ( $posts as $p ) {
        $existing = get_page_by_title( $p['title'], OBJECT, 'post' );
        if ( $existing ) {
            $ids[] = (int) $existing->ID;
            continue;
        }
        $id = wp_insert_post(
            array(
                'post_title'   => $p['title'],
                'post_content' => $p['content'],
                'post_status'  => 'publish',
                'post_type'    => 'post',
                'post_date'    => $p['date'],
            )
        );
        if ( $id && ! is_wp_error( $id ) ) {
            $ids[] = (int) $id;
        }
    }
    if ( count( $ids ) < 3 ) {
        $more = get_posts( array( 'post_type' => 'post', 'numberposts' => 3, 'fields' => 'ids' ) );
        $ids  = array_slice( array_unique( array_merge( $ids, $more ) ), 0, 3 );
    }
    return $ids;
}

function klz_aktuality_section( array $post_ids ): array {
    $titles = array(
        'Jubilejní 10. ročník Hangár párty',
        'Dětský letecký den – ZŠ Bolatice',
        'Letecký den Náměšť nad Oslavou',
    );
    $cards = array();
    foreach ( array_slice( $post_ids, 0, 3 ) as $i => $pid ) {
        $cid = 'aktC' . ( $i + 1 );
        $cards[] = array(
            'id' => $cid, 'elType' => 'container', 'isInner' => true,
            'settings' => array(
                'flex_direction' => 'column', 'width' => array( 'unit' => '%', 'size' => 32 ), 'width_mobile' => array( 'unit' => '%', 'size' => 100 ),
                'background_background' => 'classic', 'background_color' => '#ffffff',
                'border_border' => 'solid', 'border_width' => array( 'unit' => 'px', 'top' => 1, 'right' => 1, 'bottom' => 1, 'left' => 1, 'isLinked' => true ),
                'border_color' => '#e8eef5', 'border_radius' => array( 'unit' => 'px', 'top' => 12, 'right' => 12, 'bottom' => 12, 'left' => 12, 'isLinked' => true ),
                'padding' => array( 'unit' => 'px', 'top' => 24, 'right' => 20, 'bottom' => 24, 'left' => 20, 'isLinked' => true ),
            ),
            'elements' => array(
                array( 'id' => $cid . 'h', 'elType' => 'widget', 'widgetType' => 'heading', 'elements' => array(),
                    'settings' => array( 'title' => $titles[ $i ] ?? 'Aktualita', 'header_size' => 'h3', 'title_color' => '#111827', 'typography_font_size' => array( 'unit' => 'px', 'size' => 18 ), 'typography_font_weight' => '700' ) ),
                array( 'id' => $cid . 'b', 'elType' => 'widget', 'widgetType' => 'button', 'elements' => array(),
                    'settings' => array( 'text' => 'Číst více', 'link' => array( 'url' => home_url( '/?p=' . $pid ) ), 'size' => 'sm', 'background_color' => 'transparent', 'button_text_color' => '#1a73e8', 'typography_text_transform' => 'none', 'align' => 'left' ) ),
            ),
        );
    }
    return array(
        'id' => 'aktual01', 'elType' => 'container', 'isInner' => false,
        'settings' => array(
            'flex_direction' => 'column', 'content_width' => 'boxed', 'boxed_width' => array( 'unit' => 'px', 'size' => 1200 ),
            'background_background' => 'classic', 'background_color' => '#f8fafc',
            'padding' => array( 'unit' => 'px', 'top' => 72, 'right' => 48, 'bottom' => 72, 'left' => 48, 'isLinked' => false ),
            'padding_mobile' => array( 'unit' => 'px', 'top' => 48, 'right' => 24, 'bottom' => 48, 'left' => 24, 'isLinked' => false ),
        ),
        'elements' => array(
            array( 'id' => 'akt001', 'elType' => 'widget', 'widgetType' => 'text-editor', 'elements' => array(),
                'settings' => array( 'editor' => '<p style="color:#b80000;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;text-align:center;">NOVINKY</p>' ) ),
            array( 'id' => 'akt002', 'elType' => 'widget', 'widgetType' => 'heading', 'elements' => array(),
                'settings' => array( 'title' => 'Aktuality a akce', 'header_size' => 'h2', 'align' => 'center', 'title_color' => '#0f0f0f', 'typography_font_size' => array( 'unit' => 'px', 'size' => 32 ), 'typography_font_weight' => '800' ) ),
            array(
                'id' => 'akt003', 'elType' => 'container', 'isInner' => true,
                'settings' => array( 'flex_direction' => 'row', 'flex_wrap' => 'wrap', 'gap' => array( 'unit' => 'px', 'size' => 24 ), 'content_width' => 'full', 'flex_justify_content' => 'center' ),
                'elements' => $cards,
            ),
        ),
    );
}

function klz_patch_uvod( array $elements, array $post_ids ): array {
    $gal_css = '@media (min-width:768px){body.page-id-517 .e-con[data-id="gal00001"]>.e-con-inner{display:grid!important;grid-template-columns:1fr 1fr!important;gap:24px!important}body.page-id-517 .e-con[data-id="gal00001"] .elementor-element-gal00002,body.page-id-517 .e-con[data-id="gal00001"] .elementor-element-gal00003,body.page-id-517 .e-con[data-id="gal00001"] .elementor-element-gal00005{grid-column:1/-1!important}body.page-id-517 .e-con[data-id="gal00001"] [data-id="f151ad9"],body.page-id-517 .e-con[data-id="gal00001"] [data-id="e9f1b47"],body.page-id-517 .e-con[data-id="gal00001"] [data-id="e8c51ae"],body.page-id-517 .e-con[data-id="gal00001"] [data-id="e6aaa59"]{width:100%!important;max-width:100%!important}body.page-id-517 .e-con[data-id="gal00001"] .elementor-widget-image img{width:100%!important;height:260px!important;object-fit:cover!important;border-radius:12px!important}}@media (max-width:767px){body.page-id-517 .e-con[data-id="gal00001"]>.e-con-inner{display:flex!important;flex-direction:column!important;gap:16px!important}}';

    $seo = &klz_find_widget( $elements, 'seofix517' );
    if ( $seo && strpos( $seo['settings']['html'], 'gal00001-two-col' ) === false ) {
        $seo['settings']['html'] = str_replace( '</style>', $gal_css . "\n</style>", $seo['settings']['html'] );
    }

    if ( ! klz_find_widget( $elements, 'aktual01' ) ) {
        foreach ( $elements as $i => $el ) {
            if ( ( $el['id'] ?? '' ) === 'gal00001' ) {
                array_splice( $elements, $i, 0, array( klz_aktuality_section( $post_ids ) ) );
                break;
            }
        }
    }
    return $elements;
}

function klz_patch_functions_php(): void {
    $path = get_stylesheet_directory() . '/functions.php';
    if ( ! is_readable( $path ) ) {
        return;
    }
    $c = file_get_contents( $path );
    $c = str_replace( 'info@letani-zabreh.cz', 'klub@letani-zabreh.cz', $c );
    $c = str_replace( 'it2529@sspu-opava.cz', 'klub@letani-zabreh.cz', $c );
    file_put_contents( $path, $c );
}

function klz_unify_emails_in_elementor( array $elements ): array {
    $json = wp_json_encode( $elements );
    $json = str_replace( 'it2529@sspu-opava.cz', 'klub@letani-zabreh.cz', $json );
    $json = str_replace( 'info@letani-zabreh.cz', 'klub@letani-zabreh.cz', $json );
    $decoded = json_decode( $json, true );
    return is_array( $decoded ) ? $decoded : $elements;
}

$post_ids = klz_ensure_posts();
echo 'Posts: ' . implode( ',', $post_ids ) . "\n";

foreach (
    array(
        440 => 'klz_patch_kontakt',
        509 => 'klz_patch_onas',
        436 => 'klz_patch_sluzby',
    ) as $pid => $fn
) {
    $data = klz_get_elementor( $pid );
    $data = $fn( $data );
    $data = klz_unify_emails_in_elementor( $data );
    klz_save_elementor( $pid, $data );
    echo "Saved page $pid\n";
}

$uvod = klz_get_elementor( 517 );
$uvod = klz_patch_uvod( $uvod, $post_ids );
$uvod = klz_unify_emails_in_elementor( $uvod );
klz_save_elementor( 517, $uvod );
echo "Saved page 517\n";

klz_patch_functions_php();
echo "functions.php emails updated\n";

if ( class_exists( '\Elementor\Plugin' ) ) {
    \Elementor\Plugin::$instance->files_manager->clear_cache();
}

echo 'DEPLOY OK';
