import time

import streamlit as st

from streamlit_plugins.components.document_blocks import st_document_blocks

st.set_page_config(
    page_title="Documentos",
    layout="wide",
)

# EJEMPLOS
image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/ReceiptSwiss.jpg/500px-ReceiptSwiss.jpg"
filters = {
    "Solo Fechas": "label=Fecha",
    "Precios > 20": "meta.val_price>20",
    "Filtro Regex (06.)": "meta.text=/^06\\./",
    "Es Sello": "meta.type=Stamp"
}
reading_order = "meta.ro"
blocks = [
    {
        "id": "parent_header", "x": 15, "y": 5, "w": 70, "h": 18,
        "label": "Cabecera", "color": "#ff4b4b",
        "meta": {"ro": 1, "section": "Header", "confidence": 0.98},
        "children": [
            {"id": "child_title", "x": 20, "y": 7, "w": 60, "h": 5, "label": "Nombre Negocio", "color": "#00cc66",
             "meta": {"ro": 1, "text": "Restaurant Tell-Höckli"}},
            {"id": "child_date", "x": 20, "y": 13, "w": 30, "h": 4, "label": "Fecha", "color": "#00cc66",
             "meta": {"ro": 2, "text": "06.07.2007"}}
        ]
    },
    {
        "id": "parent_body", "x": 10, "y": 28, "w": 80, "h": 42,
        "label": "Líneas de Factura", "color": "#3366ff",
        "meta": {"ro": 2, "section": "Table", "total_items": 2},
        "children": [
            {"id": "child_item1", "x": 12, "y": 34, "w": 76, "h": 6, "label": "Producto 1", "color": "#ffa500",
             "meta": {"ro": 1, "text": "Grosses Bier", "val_price": 9.00}},
            {"id": "child_item2", "x": 12, "y": 42, "w": 76, "h": 6, "label": "Producto 2", "color": "#ffa500",
             "meta": {"ro": 2, "text": "Cordon Bleu", "val_price": 22.50}}
        ]
    },
    # ==========================================
    # CAJAS SUPERPUESTAS (Para probar los filtros)
    # ==========================================
    {
        "id": "parent_footer", "x": 10, "y": 75, "w": 80, "h": 20,
        "label": "Zona de Firmas", "color": "#9c27b0",
        "meta": {"ro": 3, "section": "Footer"},
        "children": [
            # La firma
            {"id": "child_sig", "x": 15, "y": 77, "w": 40, "h": 15, "label": "Firma", "color": "#e91e63",
             "meta": {"ro": 1, "type": "Signature"}},
            # El sello (solapado casi perfectamente encima de la firma)
            {"id": "child_stamp", "x": 15, "y": 77, "w": 30, "h": 12, "label": "Sello", "color": "#00bcd4",
             "meta": {"ro": 2, "type": "Stamp"}}
        ]
    }
]
custom_styles = {
    "boxes": {
        "normalAlpha": 0.1,  # Opacidad reposo padres más tenue
        "hoverAlpha": 0.4,  # Opacidad hover padres
        "childNormalAlpha": 0.2,  # Opacidad reposo hijas
        "childHoverAlpha": 0.6  # Opacidad hover hijas
    },
    "filters": {
        "Solo Fechas": {"color": "#ffffff", "backgroundColor": "#00cc66"},
        "Precios > 20": {"color": "#ffffff", "backgroundColor": "#3366ff"}
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


def _search_recursive(_selected_id: str, _blocks) -> dict | None:
    for block in _blocks:
        if block["id"] == _selected_id:
            return block
        if "children" in block:
            result = _search_recursive(_selected_id, block["children"])
            if result:
                return result
    return None


show_reading_order = st.toggle("Mostrar orden de lectura?")
if not show_reading_order:
    reading_order = None

with st.container(horizontal=True):
    selected_block_id = st_document_blocks(
        image_url,
        filters,
        blocks,
        reading_order=reading_order,
        custom_styles=custom_styles,
        width="content"
    )
    block_selected = _search_recursive(selected_block_id, blocks)
    if block_selected:
        st.write(block_selected)
