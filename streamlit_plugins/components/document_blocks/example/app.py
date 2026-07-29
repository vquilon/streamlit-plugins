from streamlit_plugins.components.document_blocks import Block
from typing import Optional

import streamlit as st

from streamlit_plugins.components.document_blocks import st_document_blocks
from streamlit_plugins.extension.dynamic_container import st_dynamic_container

st.set_page_config(
    page_title="Documentos",
    layout="wide",
)

# EJEMPLOS
image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/ReceiptSwiss.jpg/500px-ReceiptSwiss.jpg"
filters = {
    "Solo Titulos": "type=Section-Header",
    "Filtro Regex (06.)": r"content=/^\d/",
    "Bests": "metadata.confidence>0.8"
}
reading_order: Optional[str | bool] = True
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
    "boxes": {
        "normalAlpha": 0.1,  # Opacidad reposo padres más tenue
        "hoverAlpha": 0.4,  # Opacidad hover padres
        "childNormalAlpha": 0.2,  # Opacidad reposo hijas
        "childHoverAlpha": 0.6  # Opacidad hover hijas
    },
    "filters": {
        "Solo Titulos": {"color": "#ffffff", "backgroundColor": "#00cc66"},
        "Bests": {"color": "#ffffff", "backgroundColor": "#3366ff"}
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


def _search_recursive(_selected_id: str | int, _blocks) -> tuple[dict | None, dict | None]:
    for block in _blocks:
        if block["id"] == _selected_id:
            return block, None
        if "children" in block:
            result, _ = _search_recursive(_selected_id, block["children"])
            if result:
                return result, block
    return None, None


def on_tab_change():
    pass


BLOCK_HTML_TEMPLATE = """
<article id="{id}" class="article-block" style="--label-color: {color};">
<label class="label">{label}</label>
{content}
</article>
"""

HOVER_BLOCK_RESULT_KEY = "hover_block_result"
if HOVER_BLOCK_RESULT_KEY not in st.session_state:
    st.session_state[HOVER_BLOCK_RESULT_KEY] = None

RESULT_ACTIVE_OBSERVED_KEY = "selected_id"

with st.container(horizontal=True, key="app-container"):
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

    with st.container(width="content"):
        show_reading_order = st.toggle("Mostrar orden de lectura?")
        if not show_reading_order:
            reading_order = None
        st.space(size=1)
        dynamic_selected_block_result = st.session_state[HOVER_BLOCK_RESULT_KEY]

        dynamic_selected_block_id = None
        if dynamic_selected_block_result:
            dynamic_selected_block_id = dynamic_selected_block_result.get(RESULT_ACTIVE_OBSERVED_KEY)
            if dynamic_selected_block_id:
                dynamic_selected_block_id = dynamic_selected_block_id[1:]

        selected_block_id = st_document_blocks(
            image_url,
            filters,
            blocks,
            document_size=document_size,
            reading_order=reading_order,
            custom_styles=custom_styles,
            default_selected=dynamic_selected_block_id,
            set_state_on="hover",
            width="content",
            height=600,
            key="document_blocks"
        )

    blocks_col, json_col = st.tabs(
        ["Blocks", "JSON"],
        on_change=on_tab_change
    )
    block_selected = None
    if selected_block_id is not None:
        block_selected, parent_block = _search_recursive(selected_block_id, blocks)
        if parent_block is not None:
            block_selected = parent_block

    if blocks_col.open:
        dynamic_container_css = """
            .st-key-view-container .stVerticalBlock:has( .article-block) {
                padding: 0.5rem;
                padding-right: 0;
                border-radius: 0.5rem;
            }
            .st-key-view-container .article-block {
                position: relative;
                padding: 0.5rem;
                top: -0.5rem;
                width: 100%;
                border-radius: 0.5rem;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
                cursor: pointer;
            }
            .st-key-view-container .article-block p {
                margin: 0;
            }
            .st-key-view-container .article-block:after,
            .st-key-view-container .article-block.highlight-item:before {
                content: "";
                position: absolute;
                width: calc(100% + 0.5rem);
                height: 100%;
                left: calc(-1 * (0.5rem));
                top: 0;
                border-radius: 0.5rem;
            }
            .st-key-view-container .article-block.highlight-item:before {
                background-color: color-mix(in srgb, var(--label-color) 20%, transparent);
            }
            .st-key-view-container .article-block:after {
                border-left: 0.5rem solid var(--label-color);    
            }
            .st-key-view-container .article-block .label {
                border-bottom: 1px solid color-mix(in srgb, var(--label-color) 50%, transparent);
                width: 100%;
                position: relative;
                display: inline-block;
            }
        """
        with blocks_col:
            with st_dynamic_container(
                    container_source_key="document_blocks",
                    key="view-container",
                    mimic_vertical=True,
                    active_observed_item_key=HOVER_BLOCK_RESULT_KEY,
                    result_active_observed_key=RESULT_ACTIVE_OBSERVED_KEY,
                    active_highlight_item_class="highlight-item",
                    active_observed_selector=".article-block",
                    active_keep_item_on_leave_mouse=True,
                    custom_css=dynamic_container_css,
                    observer_type="hover",
                    border=False, gap="xsmall",
            ) as data_input:
                for block in blocks:
                    with st.container(border=True):
                        dynamic_block_id = f"d{str(block['id'])}"
                        st.markdown(
                            BLOCK_HTML_TEMPLATE.format(
                                id=dynamic_block_id,
                                content=block.get('content', block.get('content', '')),
                                label=block.get('label', block.get('type', 'Undefined')),
                                color=block.get('color', 'red'),
                            ),
                            unsafe_allow_html=True
                        )
                if block_selected is not None:
                    block_selected = block_selected or {}
                    dynamic_selected_block_id = f"d{str(block_selected['id'])}"
                    data_input.scrollToSelector = f"#{dynamic_selected_block_id}"
                    data_input.flashBrightScrollTarget = True
                    data_input.flashBrightScrollBg = block_selected.get('color', '#ff4b4b')

    if json_col.open:
        with json_col:
            with st_dynamic_container(
                    container_source_key="document_blocks",
                    key="view-container", mimic_vertical=True, border=True
            ):
                st.json(blocks)
