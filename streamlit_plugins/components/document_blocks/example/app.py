import colorsys
import hashlib
from typing import Optional

import streamlit as st

from streamlit_plugins.components.document_blocks import BlockFieldAssociation, st_documents_blocks_info, Document, \
    search_blocks_recursive

st.set_page_config(
    page_title="Documentos",
    layout="wide",
)



def _parse_color(c: str) -> tuple:
    """Convierte un color string ('white', '#RRGGBB') a una tupla RGB (0-1)."""
    if c.startswith("#"):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    mapping = {
        "white": (1.0, 1.0, 1.0),
        "black": (0.0, 0.0, 0.0),
        "gray": (0.5, 0.5, 0.5),
        "red": (1.0, 0.0, 0.0),
        "green": (0.0, 1.0, 0.0),
        "blue": (0.0, 0.0, 1.0),
    }
    return mapping.get(c.lower(), (0.0, 0.0, 0.0))


def _get_luminance(rgb: tuple) -> float:
    """Calcula la luminancia relativa estándar de un color RGB (0-1)."""
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def hash_color(text: str, forecolor="white", background="black") -> str:
    """
    Función que devuelve el color asociado a un hash de texto,
    garantizando colores saturados que contrastan con el fondo y el texto.
    """
    # 1. Obtener luminancias de referencia de los parámetros
    bg_rgb = _parse_color(background)
    fg_rgb = _parse_color(forecolor)
    bg_lum = _get_luminance(bg_rgb)
    fg_lum = _get_luminance(fg_rgb)

    # 2. Hash determinista consistente
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()

    # 3. Tono (Hue) y Saturación (Saturation) fijos/deterministas del hash
    hue = int.from_bytes(hash_bytes[:2], byteorder="big") / 65535.0
    saturation = 0.75 + (hash_bytes[2] / 255.0) * 0.25  # Forzar colores vivos/saturados

    # 4. Encontrar el mejor Brillo (Value) que garantice el contraste
    best_value = 0.7
    best_score = -1.0

    # Probamos distintos niveles de brillo para el color del hash (de 0.2 a 0.95)
    for v in [i / 100.0 for i in range(20, 96, 5)]:
        rgb = colorsys.hsv_to_rgb(hue, saturation, v)
        lum = _get_luminance(rgb)

        # Queremos maximizar la diferencia de luminancia con el fondo y con el texto
        contrast_bg = abs(lum - bg_lum)
        contrast_fg = abs(lum - fg_lum)
        score = contrast_bg + contrast_fg

        if score > best_score:
            best_score = score
            best_value = v

    # 5. Convertir a RGB final y luego a Hexadecimal
    final_rgb = colorsys.hsv_to_rgb(hue, saturation, best_value)
    hex_color = "#{:02x}{:02x}{:02x}".format(
        int(final_rgb[0] * 255),
        int(final_rgb[1] * 255),
        int(final_rgb[2] * 255)
    )

    return hex_color


# EJEMPLOS
image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/ReceiptSwiss.jpg/500px-ReceiptSwiss.jpg"
filters = {
    "Solo Titulos": "type=Section-Header",
    "Filtro Regex (\\d)": r"content=/^\d/",
    "Bests": "metadata.confidence>0.8"
}
reading_order: Optional[str | bool] = True
block_field_spec = BlockFieldAssociation(
    # id='id',
    # type='type',
    # content='content',
    # bbox='bbox',
    # section_hierarchy='section_hierarchy',
    # metadata='metadata',
    color=lambda x: hash_color(x['type']),
    html='content',
    markdown='content'
)

blocks = [
    {
        'id': '/page/0/Section-Header/0',
        'type': 'Section-Header',
        'content': '<h1><b><span data-bbox="602 261 902 331" data-confidence="1">Berghotel</span></b></h1><h1><b><span data-bbox="502 322 703 388" data-confidence="1">Grosse</span> <span data-bbox="737 322 1034 392" data-confidence="1">Scheidegg</span></b></h1><p><span data-bbox="568 388 662 441" data-confidence="0.999">3818</span> <span data-bbox="682 388 927 441" data-confidence="1">Grindelwald</span></p><p><span data-bbox="568 449 728 502" data-confidence="1">Familie</span> <span data-bbox="748 449 788 502" data-confidence="1">R.</span> <span data-bbox="794 449 927 502" data-confidence="0.999">Müller</span></p>',
        'page': 0,
        'polygon': [[500, 257], [1036, 257], [1036, 490], [500, 490]],
        'bbox': [500, 257, 1036, 490],
        'section_hierarchy': {},

        'metadata': {
            'confidence': 0.9997497184919896
        }
    },
    {
        'id': '/page/0/Text/1',
        'type': 'Text',
        'content': '<p><span data-bbox="235 570 344 627" data-confidence="1">Rech.</span> <span data-bbox="352 574 415 623" data-confidence="1">Nr.</span> <span data-bbox="438 572 526 627" data-confidence="1">4572</span></p>',
        'page': 0,
        'polygon': [[231, 564], [531, 564], [531, 619],
                    [231, 619]],
        'bbox': [231, 564, 531, 619], 'section_hierarchy': {},

        'metadata': {'confidence': 1}
    },
    {'id': '/page/0/Text/2', 'type': 'Text',
     'content': '<p><span data-bbox="770 574 1190 627" data-confidence="1">30.07.2007/13:29:17</span></p>',
     'page': 0,
     'polygon': [[765, 564], [1193, 564], [1193, 619], [765, 619]], 'bbox': [765, 564, 1193, 619],
     'section_hierarchy': {}, 'metadata': {'confidence': 1}},
    {'id': '/page/0/Text/3', 'type': 'Text',
     'content': '<p><span data-bbox="235 635 303 686" data-confidence="1">Bar</span></p>',
     'page': 0, 'polygon': [[231, 627], [308, 627], [308, 674], [231, 674]],
     'bbox': [231, 627, 308, 674], 'section_hierarchy': {},
     'metadata': {'confidence': 1}},
    {'id': '/page/0/Text/4', 'type': 'Text',
     'content': '<p><span data-bbox="927 635 1041 690" data-confidence="1">Tisch</span> <span data-bbox="1101 637 1196 690" data-confidence="1">7/01</span></p>',
     'page': 0, 'polygon': [[920, 627], [1193, 627], [1193, 680], [920, 680]], 'bbox': [920, 627, 1193, 680],
     'section_hierarchy': {}, 'metadata': {'confidence': 1}},
    {
        'id': '/page/0/List-Item/5',
        'type': 'List-Item',
        'content': '<div><p><span data-bbox="258 758 415 813" data-confidence="0.955">2xLatte</span> <span data-bbox="438 758 640 813" data-confidence="0.998">Macchiato</span> <span data-bbox="706 758 728 813" data-confidence="1">à</span> <span data-bbox="794 758 883 813" data-confidence="1">4.50</span> <span data-bbox="927 758 993 813" data-confidence="1">CHF</span> <span data-bbox="1082 758 1173 813" data-confidence="1">9.00</span></p><p><span data-bbox="261 821 415 874" data-confidence="1">1xGloki</span> <span data-bbox="706 817 728 874" data-confidence="1">à</span> <span data-bbox="794 819 883 874" data-confidence="1">5.00</span> <span data-bbox="927 821 993 874" data-confidence="1">CHF</span> <span data-bbox="1082 821 1173 874" data-confidence="1">5.00</span></p><p><span data-bbox="260 883 665 934" data-confidence="1">1xSchweinschnitzel</span> <span data-bbox="706 878 731 934" data-confidence="1">à</span> <span data-bbox="770 880 883 934" data-confidence="1">22.00</span> <span data-bbox="927 878 993 934" data-confidence="1">CHF</span> <span data-bbox="1059 883 1173 934" data-confidence="1">22.00</span></p><p><span data-bbox="261 942 549 993" data-confidence="1">1xChässpätzli</span> <span data-bbox="706 942 728 993" data-confidence="1">à</span> <span data-bbox="776 942 883 993" data-confidence="1">18.50</span> <span data-bbox="927 942 997 993" data-confidence="1">CHF</span> <span data-bbox="1070 942 1173 993" data-confidence="1">18.50</span></p></div>',
        'page': 0,
        'polygon': [[254, 752], [1178, 752], [1178, 983], [254, 983]],
        'bbox': [254, 752, 1178, 983],
        'section_hierarchy': {},
        'metadata': {'confidence': 0.9976163308517917},
        'children': [
            {
                'id': '/page/0/List-Item/5/Text/0',
                'type': 'Text',
                'content': '<p><span data-bbox="258 758 415 813" data-confidence="0.955">2xLatte</span> <span data-bbox="438 758 640 813" data-confidence="0.998">Macchiato</span> <span data-bbox="706 758 728 813" data-confidence="1">à</span> <span data-bbox="794 758 883 813" data-confidence="1">4.50</span> <span data-bbox="927 758 993 813" data-confidence="1">CHF</span> <span data-bbox="1082 758 1173 813" data-confidence="1">9.00</span></p>',
                'polygon': [[254, 752], [1178, 752], [1178, 983], [254, 983]],
                'bbox': [254, 752, 1178, 809.25],
                'metadata': {'confidence': 0.955},
            },
            {
                'id': '/page/0/List-Item/5/Text/1',
                'type': 'Text',
                'content': '<p><span data-bbox="261 821 415 874" data-confidence="1">1xGloki</span> <span data-bbox="706 817 728 874" data-confidence="1">à</span> <span data-bbox="794 819 883 874" data-confidence="1">5.00</span> <span data-bbox="927 821 993 874" data-confidence="1">CHF</span> <span data-bbox="1082 821 1173 874" data-confidence="1">5.00</span></p>',
                'polygon': [[254, 752], [1178, 752], [1178, 983], [254, 983]],
                'bbox': [254, 809.75, 1178, 867],
                'metadata': {'confidence': 1},
            },
            {
                'id': '/page/0/List-Item/5/Text/2',
                'type': 'Text',
                'content': '<p><span data-bbox="260 883 665 934" data-confidence="1">1xSchweinschnitzel</span> <span data-bbox="706 878 731 934" data-confidence="1">à</span> <span data-bbox="770 880 883 934" data-confidence="1">22.00</span> <span data-bbox="927 878 993 934" data-confidence="1">CHF</span> <span data-bbox="1059 883 1173 934" data-confidence="1">22.00</span></p>',
                'polygon': [[254, 752], [1178, 752], [1178, 983], [254, 983]],
                'bbox': [254, 867.5, 1178, 925],
                'metadata': {'confidence': 1},
            },
            {
                'id': '/page/0/List-Item/5/Text/3',
                'type': 'Text',
                'content': '<p><span data-bbox="261 942 549 993" data-confidence="1">1xChässpätzli</span> <span data-bbox="706 942 728 993" data-confidence="1">à</span> <span data-bbox="776 942 883 993" data-confidence="1">18.50</span> <span data-bbox="927 942 997 993" data-confidence="1">CHF</span> <span data-bbox="1070 942 1173 993" data-confidence="1">18.50</span></p>',
                'polygon': [[254, 752], [1178, 752], [1178, 983], [254, 983]],
                'bbox': [254, 925.5, 1178, 983],
                'metadata': {'confidence': 1},
            }
        ]
    },
    {'id': '/page/0/Text/6', 'type': 'Text',
     'content': '<p><span data-bbox="526 1069 640 1126" data-confidence="1">Total</span> <span data-bbox="668 1069 688 1126" data-confidence="1">:</span> <span data-bbox="776 1069 842 1126" data-confidence="1">CHF</span> <span data-bbox="980 1062 1136 1126" data-confidence="1">54.50</span></p>',
     'page': 0, 'polygon': [[520, 1056], [1142, 1056], [1142, 1116], [520, 1116]],
     'bbox': [520, 1056, 1142, 1116],
     'section_hierarchy': {}, 'metadata': {'confidence': 1}},
    {'id': '/page/0/Text/7', 'type': 'Text',
     'content': '<p><span data-bbox="232 1189 344 1244" data-confidence="1">Incl.</span> <span data-bbox="368 1189 460 1244" data-confidence="1">7.6%</span> <span data-bbox="483 1189 571 1244" data-confidence="0.997">MwSt</span> <span data-bbox="637 1189 754 1244" data-confidence="1">54.50</span> <span data-bbox="776 1189 865 1244" data-confidence="1">CHF:</span> <span data-bbox="956 1189 1047 1244" data-confidence="1">3.85</span></p>',
     'page': 0,
     'polygon': [[231, 1181], [1050, 1181], [1050, 1236], [231, 1236]],
     'bbox': [231, 1181, 1050, 1236], 'section_hierarchy': {},
     'metadata': {'confidence': 0.9994981190458571}},
    {'id': '/page/0/Text/8', 'type': 'Text',
     'content': '<p><span data-bbox="231 1318 460 1373" data-confidence="1">Entspricht</span> <span data-bbox="483 1318 529 1373" data-confidence="1">in</span> <span data-bbox="549 1318 643 1373" data-confidence="1">Euro</span> <span data-bbox="706 1318 823 1373" data-confidence="1">36.33</span> <span data-bbox="865 1318 931 1373" data-confidence="0.999">EUR</span></p>',
     'page': 0, 'polygon': [[226, 1310], [939, 1310], [939, 1365], [226, 1365]], 'bbox': [226, 1310, 939, 1365],
     'section_hierarchy': {}, 'metadata': {'confidence': 0.9997997597597917}},
    {'id': '/page/0/Text/9', 'type': 'Text',
     'content': '<p><span data-bbox="231 1385 277 1436" data-confidence="0.999">Es</span> <span data-bbox="298 1381 483 1436" data-confidence="1">bediente</span> <span data-bbox="505 1381 595 1436" data-confidence="1">Sie:</span> <span data-bbox="616 1381 754 1436" data-confidence="1">Ursula</span></p>',
     'page': 0,
     'polygon': [[226, 1373], [757, 1373], [757, 1426],
                 [226, 1426]],
     'bbox': [226, 1373, 757, 1426], 'section_hierarchy': {},

     'metadata': {'confidence': 0.9997497184919896}},
    {'id': '/page/0/Text/10', 'type': 'Text',
     'content': '<p><span data-bbox="574 1508 665 1565" data-confidence="1">MwSt</span> <span data-bbox="688 1508 782 1565" data-confidence="1">Nr.:</span> <span data-bbox="800 1508 871 1565" data-confidence="1">430</span> <span data-bbox="890 1508 962 1565" data-confidence="1">234</span></p>',
     'page': 0, 'polygon': [[566, 1502], [962, 1502], [962, 1555], [566, 1555]], 'bbox': [566, 1502, 962, 1555],
     'section_hierarchy': {}, 'metadata': {'confidence': 1}},
    {'id': '/page/0/Text/11', 'type': 'Text',
     'content': '<p><span data-bbox="529 1573 643 1629" data-confidence="1">Tel.:</span> <span data-bbox="665 1573 737 1629" data-confidence="1">033</span> <span data-bbox="757 1573 823 1629" data-confidence="1">853</span> <span data-bbox="848 1573 896 1629" data-confidence="1">67</span> <span data-bbox="920 1573 962 1629" data-confidence="1">16</span></p>',
     'page': 0,
     'polygon': [[523, 1565], [962, 1565], [962, 1616], [523, 1616]],
     'bbox': [523, 1565, 962, 1616], 'section_hierarchy': {},
     'metadata': {'confidence': 1}},
    {
        'id': '/page/0/Text/12', 'type': 'Text',
        'content': '<p><span data-bbox="526 1637 643 1692" data-confidence="1">Fax.:</span> <span data-bbox="665 1637 734 1692" data-confidence="1">033</span> <span data-bbox="757 1637 823 1692" data-confidence="1">853</span> <span data-bbox="848 1637 896 1692" data-confidence="1">67</span> <span data-bbox="914 1637 962 1692" data-confidence="1">19</span></p>',
        'page': 0, 'polygon': [[523, 1627], [962, 1627], [962, 1678], [523, 1678]], 'bbox': [523, 1627, 962, 1678],
        'section_hierarchy': {}, 'metadata': {'confidence': 1}
    },
    {
        'id': '/page/0/Text/13', 'type': 'Text',
        'content': '<p><span data-bbox="300 1700 463 1755" data-confidence="1">E-mail:</span> <span data-bbox="483 1700 1070 1747" data-confidence="1">grossescheidegg@bluewin.ch</span></p>',
        'page': 0,
        'polygon': [[295, 1690], [1078, 1690], [1078, 1745], [295, 1745]],
        'bbox': [295, 1690, 1078, 1745], 'section_hierarchy': {},
        'metadata': {'confidence': 1}
    }
]
document_size = (1540, 2044)
custom_styles = {
    "blocks": {
        "normalAlpha": 0.1,  # Opacidad reposo padres más tenue
        "hoverAlpha": 0.4,  # Opacidad hover padres
        "childNormalAlpha": 0.2,  # Opacidad reposo hijas
        "childHoverAlpha": 0.6  # Opacidad hover hijas
    },
    "filters": {
        "Solo Titulos": {"color": "#ffffff", "backgroundColor": "#00cc66"},
        "Bests": {"color": "#ffffff", "backgroundColor": "#3366ff"},
        "Filtro Regex (\\d)": {"color": "#ffffff", "backgroundColor": "#ff6600"}
    },
    "reading_order": {
        "color": "#e91e63",  # Línea de color rosa/fucsia
        "dashAnimationSpeed": 0.5,  # Más rápido (20s * 0.5 = 10s)
        # Ejemplo usando un punto circular en lugar de una flecha tradicional
        "markerHeadHTML": """
            <marker id="customArrow" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <circle cx="6" cy="6" r="5" fill="#e91e63" />
            </marker>
        """,
        # Personalización exclusiva para los hijos
        "children_color": "#00e5ff",  # Color azul claro para hijos
        "children_dashAnimationSpeed": 0.8,
        "children_markerHeadHTML": """
            <marker id="customChildArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
              <circle cx="5" cy="5" r="4" fill="#00e5ff" />
            </marker>
        """
    }
}

with st.container(key="app-container"):
    st.markdown(
        """
        <style>
        .st-key-app-container > div:has(style:only-child):only-child {
            display: none;
        }
        .stMainBlockContainer {
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st_documents_blocks_info(
            document=Document(
                name="receipt",
                size=document_size,
                blocks={1: blocks},
                images={1: image_url},
            ),
            reading_order=reading_order,
            filters=filters,
            block_field_spec=block_field_spec,
            custom_styles=custom_styles,
            custom_tabs=["Sections"],
            format_raw_code=True
    ) as document_blocks_delta:
        blocks_normalized, st_custom_tabs = document_blocks_delta

        section_blocks = search_blocks_recursive({"type": "Section-Header"}, blocks_normalized)

        st_sections_col = st_custom_tabs[0]

        if st_sections_col.open:
            with st_sections_col:
                for section_block, level in section_blocks:
                    st.write(f"- [Level {level}] {section_block['content']}")
