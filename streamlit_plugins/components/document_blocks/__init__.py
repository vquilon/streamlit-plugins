import base64
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, Literal

from PIL import Image
from streamlit.components.v2 import component as create_component
from streamlit.elements.lib.layout_utils import Width, Height

___HTML = """
<div id="image-viewer-container">
    <div id="filters-bar" class="filters-bar"></div>
    <div class="image-wrapper">
      <img id="doc-image" src="" alt="Documento" />
      <svg id="reading-order-parents-svg" class="reading-order-layer"></svg>
      <div id="bboxes-overlay"></div>
    </div>
</div>
"""
__CSS = """
/* COMPONENTE */
#image-viewer-container {
  flex: 1;
  max-width: 550px;
  background: #fff;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.image-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
}

#doc-image {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 4px;
}

#bboxes-overlay {
  position: absolute;
  top: 0; 
  left: 0; 
  width: 100%; 
  height: 100%;
}

/* CAJAS */
.bbox {
  position: absolute;
  box-sizing: border-box;
  cursor: pointer;
  /* Usamos variables CSS para inyectar los colores desde JS */
  border: 2px solid var(--border-color);
  background-color: var(--bg-normal);
  transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.bbox:hover {
  background-color: var(--bg-hover);
}

.bbox-tooltip {
  position: absolute;
  bottom: 100%;
  left: -2px;
  color: #fff;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  font-weight: bold;
  white-space: nowrap;
  border-radius: 3px 3px 3px 0;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.15s ease;
  pointer-events: none;
  z-index: 100;
}

.bbox:hover > .bbox-tooltip {
  opacity: 1;
  visibility: visible;
}

.bbox-parent {
  z-index: 10;
}

.bbox-child {
  opacity: 0;
  pointer-events: none;
  z-index: 20;
}

/* Manejo del hover nativo a nivel de grupo (Reemplaza los eventos de JS) */
.bbox-group:hover .bbox-child {
  opacity: 1;
  pointer-events: auto;
}

/* ESTADO SELECCIONADO AL HACER CLICK */
.bbox.is-selected {
  background-color: var(--bg-hover) !important;
  border-width: 3px !important;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.9), 0 0 10px rgba(0, 0, 0, 0.6);
  /* Estas dos líneas aseguran que un hijo seleccionado siempre sea visible */
  opacity: 1 !important;
  pointer-events: auto !important;
}

.bbox.is-selected > .bbox-tooltip {
  opacity: 1;
  visibility: visible;
}

.bbox-group:has(.bbox-child.is-selected) .bbox-parent > .bbox-tooltip {
  opacity: 1;
  visibility: visible;
}

/* BARRA DE FILTROS */
.filters-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  min-height: 28px;
}

.filter-btn {
  border: 1px solid #ccc;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  opacity: 0.85;
}

/* Las clases activas usarán los estilos personalizados del objeto */
.filter-btn.is-active {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

/* OCULTAR CAJAS FILTRADAS */
.bbox.is-filtered-out {
  display: none !important;
}

/* PADRE "FANTASMA" (No hace match, pero su hijo sí) */
.bbox.is-ghost {
  border-color: #b0b0b0 !important;
  background-color: rgba(176, 176, 176, 0.15) !important;
  pointer-events: none !important; /* No se puede hacer click */
  z-index: 5 !important;
}

/* Tooltip del padre fantasma (siempre visible y en gris) */
.bbox.is-ghost > .bbox-tooltip {
  background-color: #b0b0b0 !important;
  opacity: 1 !important;
  visibility: visible !important;
}

/* HIJOS QUE HACEN MATCH (Visibles de inmediato sin necesidad de hover) */
.bbox-child.is-forced-visible {
  opacity: 1 !important;
  pointer-events: auto !important;
  z-index: 25 !important;
}

/* CAPA SVG ORDEN DE LECTURA */
.reading-order-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Crucial para no bloquear los clicks de las cajas */
  z-index: 30; /* Por debajo del hover/selección, por encima de las hijas */
  display: none; /* Oculto por defecto */
}

/* Cuando se marca el checkbox HTML */
.reading-order-layer.is-visible {
  display: block;
}

/* Animación de la línea controlada por variable CSS --ro-speed */
.ro-line {
  fill: none;
  stroke-width: 2.5;
  stroke-dasharray: 6;
  animation: dash-animation var(--ro-speed, 20s) linear infinite;
}

/* SVG local de cada grupo (para los hijos) */
.children-ro-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 25; /* Por debajo de los tooltips, por encima de las cajas */
  opacity: 0; /* Oculto por defecto */
  transition: opacity 0.2s ease;
}

/* Solo se muestra si pasas el ratón por el grupo, o si el padre o un hijo tienen .is-selected */
/* Solo se muestra si el ratón pasa por el grupo O si está seleccionado, 
   PERO ÚNICAMENTE si el SVG general de padres está visible */
.image-wrapper:has(#reading-order-parents-svg.is-visible) .bbox-group:hover .children-ro-layer,
.image-wrapper:has(#reading-order-parents-svg.is-visible) .bbox-group:has(.bbox.is-selected) .children-ro-layer {
  opacity: 1 !important;
}
/* Las clases de animación que ya tenías */
.ro-line-child {
  fill: none;
  stroke-width: 2;
  stroke-dasharray: 4;
  animation: dash-animation var(--ro-child-speed, 15s) linear infinite;
}

@keyframes dash-animation {
  to { stroke-dashoffset: -200; }
}
"""
__JS = """
// =====================================================================
// 1. LÓGICA DEL COMPONENTE (Exportable a Streamlit V2)
// =====================================================================

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ponytail: normalize bbox from polygon/bbox format or legacy x,y,w,h
// converts pixel coords to % if document_size provided, otherwise returns as-is
function extractBBoxCoords(box, docSize) {
  let coords = null;
  
  if (box.bbox && Array.isArray(box.bbox)) {
    // bbox format: [x, y, x2, y2]
    coords = { x: box.bbox[0], y: box.bbox[1], x2: box.bbox[2], y2: box.bbox[3] };
  } else if (box.polygon && Array.isArray(box.polygon) && box.polygon.length >= 2) {
    // polygon format: [[x1,y1], [x2,y2], ...]
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    box.polygon.forEach(([x, y]) => {
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    });
    coords = { x: minX, y: minY, x2: maxX, y2: maxY };
  } else if (box.x !== undefined && box.y !== undefined && box.w !== undefined && box.h !== undefined) {
    // legacy format: x, y, w, h (assuming percentages)
    coords = { x: box.x, y: box.y, x2: box.x + box.w, y2: box.y + box.h, isLegacy: true };
  }
  
  if (!coords) return null;
  
  // normalize to percentages if docSize provided and coords are in pixels
  if (docSize && docSize.width && docSize.height && !coords.isLegacy) {
    const isPixel = coords.x > 100 || coords.y > 100 || coords.x2 > 100 || coords.y2 > 100;
    if (isPixel) {
      coords.x = (coords.x / docSize.width) * 100;
      coords.y = (coords.y / docSize.height) * 100;
      coords.x2 = (coords.x2 / docSize.width) * 100;
      coords.y2 = (coords.y2 / docSize.height) * 100;
    }
  }
  
  return coords;
}

// Función auxiliar para gestionar la selección visual sin repintar todo el DOM
function selectBox(boxElement) {
  // 1. Buscamos si hay algún elemento previamente seleccionado y le quitamos la clase
  const currentSelected = document.querySelector('.bbox.is-selected');
  if (currentSelected) {
    currentSelected.classList.remove('is-selected');
  }
  // 2. Añadimos la clase al nuevo elemento clickeado
  if (boxElement !== currentSelected) {
    boxElement.classList.add('is-selected');
  }
}

export default function(component) {
  const { setStateValue, setTriggerValue, parentElement, data } = component;

  const imgEl = parentElement.querySelector('#doc-image');
  const overlay = parentElement.querySelector('#bboxes-overlay');
  const filtersBar = parentElement.querySelector('#filters-bar');
  const svgParents = parentElement.querySelector('#reading-order-parents-svg');

  if (data && data.imageUrl && imgEl.src !== data.imageUrl) {
    imgEl.src = data.imageUrl;
  }

  overlay.innerHTML = '';
  filtersBar.innerHTML = '';
  if (svgParents) svgParents.innerHTML = '';
  if (!data || !data.blocks) return;

  // 0. DOCUMENTO SIZE (para normalizar coordenadas en píxeles a porcentajes)
  const docSize = data.document_size || null;

  // 1. EXTRAEMOS ESTILOS Y CONFIGURACIÓN GLOBAL
  const boxStyles = data.styles && data.styles.blocks ? data.styles.blocks : {};
  const normalAlpha = boxStyles.normalAlpha !== undefined ? boxStyles.normalAlpha : 0.15;
  const hoverAlpha = boxStyles.hoverAlpha !== undefined ? boxStyles.hoverAlpha : 0.35;
  const childNormalAlpha = boxStyles.childNormalAlpha !== undefined ? boxStyles.childNormalAlpha : 0.25;
  const childHoverAlpha = boxStyles.childHoverAlpha !== undefined ? boxStyles.childHoverAlpha : 0.50;

  const initialSelectedId = data.selected_id || null; 

  // Configuración de Orden de Lectura
  // ponytail: orderPath is true (use natural order), string (use path), or null (skip)
  const orderPath = data.reading_order === true || typeof data.reading_order === 'string' ? data.reading_order : null;
  const roStyles = data.styles && data.styles.reading_order ? data.styles.reading_order : {};
  const cColor = roStyles.children_color || '#00e5ff';
  const cSpeed = roStyles.children_dashAnimationSpeed !== undefined ? roStyles.children_dashAnimationSpeed : 1;
  const cMarkerHTML = roStyles.children_markerHeadHTML || `
    <marker id="arrowHeadC" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${cColor}" />
    </marker>
  `;

  // 2. CREACIÓN DE CAJAS Y SVGs LOCALES (HIJOS)
  data.blocks.forEach(parentBox => {
    const pCoords = extractBBoxCoords(parentBox, docSize);
    if (!pCoords) return;
    
    const group = document.createElement('div');
    group.className = 'bbox-group';
    group.style.position = 'absolute';
    const pW = pCoords.x2 - pCoords.x;
    const pH = pCoords.y2 - pCoords.y;
    const isPercent = true;
    const unit = '%';
    group.style.left = `${pCoords.x}${unit}`;
    group.style.top = `${pCoords.y}${unit}`;
    group.style.width = `${pW}${unit}`;
    group.style.height = `${pH}${unit}`;

    // --- CAJA PADRE ---
    const pDiv = document.createElement('div');
    pDiv.className = 'bbox bbox-parent';
    pDiv.id = parentBox.id;
    pDiv.style.width = '100%';
    pDiv.style.height = '100%';
    
    if (initialSelectedId === parentBox.id) pDiv.classList.add('is-selected');
    
    const pColor = parentBox.color || '#ff4b4b';
    pDiv.style.setProperty('--border-color', pColor);
    pDiv.style.setProperty('--bg-normal', hexToRgba(pColor, normalAlpha));
    pDiv.style.setProperty('--bg-hover', hexToRgba(pColor, hoverAlpha));

    const pTooltip = document.createElement('div');
    pTooltip.className = 'bbox-tooltip';
    pTooltip.style.backgroundColor = pColor;
    pTooltip.textContent = parentBox.type;
    pDiv.appendChild(pTooltip);

    if (data.set_state_on === 'hover') {
      pDiv.onmouseenter = () => {
        selectBox(pDiv);
        if (typeof setStateValue === 'function') setStateValue('selected_id', parentBox.id);
      };
      pDiv.onmouseleave = () => {
        if (typeof setStateValue === 'function') setStateValue('selected_id', null);
      };
    } else {
      pDiv.onclick = (e) => {
        e.stopPropagation();
        selectBox(pDiv);
        if (typeof setStateValue === 'function') setStateValue('selected_id', parentBox.id);
      };
    }

    group.appendChild(pDiv);

    // --- CAJAS HIJAS ---
    if (parentBox.children && parentBox.children.length > 0) {
      parentBox.children.forEach(childBox => {
        const cCoords = extractBBoxCoords(childBox, docSize);
        if (!cCoords) return;
        
        const cDiv = document.createElement('div');
        cDiv.className = 'bbox bbox-child';
        cDiv.id = childBox.id;
        
        if (initialSelectedId === childBox.id) cDiv.classList.add('is-selected');

        const relX = ((cCoords.x - pCoords.x) / pW) * 100;
        const relY = ((cCoords.y - pCoords.y) / pH) * 100;
        const cW = cCoords.x2 - cCoords.x;
        const cH = cCoords.y2 - cCoords.y;
        const relW = (cW / pW) * 100;
        const relH = (cH / pH) * 100;

        cDiv.style.left = `${relX}%`;
        cDiv.style.top = `${relY}%`;
        cDiv.style.width = `${relW}%`;
        cDiv.style.height = `${relH}%`;

        const cColorBox = childBox.color || '#00cc66';
        cDiv.style.setProperty('--border-color', cColorBox);
        cDiv.style.setProperty('--bg-normal', hexToRgba(cColorBox, childNormalAlpha));
        cDiv.style.setProperty('--bg-hover', hexToRgba(cColorBox, childHoverAlpha));

        const cTooltip = document.createElement('div');
        cTooltip.className = 'bbox-tooltip';
        cTooltip.style.backgroundColor = cColorBox;
        cTooltip.textContent = childBox.type;
        cDiv.appendChild(cTooltip);

        if (data.set_state_on === 'hover') {
          cDiv.onmouseenter = () => {
            selectBox(cDiv);
            if (typeof setStateValue === 'function') setStateValue('selected_id', childBox.id);
          };
          cDiv.onmouseleave = () => {
            if (typeof setStateValue === 'function') setStateValue('selected_id', null);
          };
        } else {
          cDiv.onclick = (e) => {
            e.stopPropagation();
            selectBox(cDiv);
            if (typeof setStateValue === 'function') setStateValue('selected_id', childBox.id);
          };
        }

        group.appendChild(cDiv);
      });
    }

    // --- ORDEN DE LECTURA (SVG LOCAL PARA HIJOS) ---
    if (orderPath && parentBox.children && parentBox.children.length >= 2) {
      const orderedChildren = parentBox.children.map((child, index) => {
        const orderVal = orderPath === true ? index : parseInt(orderPath.split('.').reduce((acc, part) => acc && acc[part], child), 10);
        return { child, orderVal };
      }).filter(item => !isNaN(item.orderVal)).sort((a, b) => a.orderVal - b.orderVal);

      if (orderedChildren.length > 1) {
        const localSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        localSvg.setAttribute('class', 'children-ro-layer');
        localSvg.style.setProperty('--ro-child-speed', `${15 * cSpeed}s`);

        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = cMarkerHTML;
        localSvg.appendChild(defs);

        for (let i = 0; i < orderedChildren.length - 1; i++) {
          const current = orderedChildren[i].child;
          const next = orderedChildren[i + 1].child;
          
          const curCoords = extractBBoxCoords(current, docSize);
          const nextCoords = extractBBoxCoords(next, docSize);
          if (!curCoords || !nextCoords) continue;

          // Centro superior absoluto
          const curW = curCoords.x2 - curCoords.x;
          const nextW = nextCoords.x2 - nextCoords.x;
          const absX1 = curCoords.x + (curW / 2);
          const absY1 = curCoords.y;
          const absX2 = nextCoords.x + (nextW / 2);
          const absY2 = nextCoords.y;

          // Convertimos a porcentajes relativos al grupo padre
          const relX1 = ((absX1 - pCoords.x) / pW) * 100;
          const relY1 = ((absY1 - pCoords.y) / pH) * 100;
          const relX2 = ((absX2 - pCoords.x) / pW) * 100;
          const relY2 = ((absY2 - pCoords.y) / pH) * 100;

          const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          line.setAttribute('x1', `${relX1}%`);
          line.setAttribute('y1', `${relY1}%`);
          line.setAttribute('x2', `${relX2}%`);
          line.setAttribute('y2', `${relY2}%`);
          line.setAttribute('class', 'ro-line-child');
          line.style.stroke = cColor;

          const matchIdC = cMarkerHTML.match(/id="([^"]+)"/);
          line.setAttribute('marker-end', `url(#${matchIdC ? matchIdC[1] : 'arrowHeadC'})`);
          
          localSvg.appendChild(line);
        }
        group.appendChild(localSvg);
      }
    }

    overlay.appendChild(group);
  });

  // 3. MOTOR DE FILTROS
  if (data.filters) {
    const activeFilters = new Set();
    const filterStylesConfig = data.styles && data.styles.filters ? data.styles.filters : {};

    Object.entries(data.filters).forEach(([filterName, expression]) => {
      const btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.textContent = filterName;
      btn.style.background = '#f0f0f0';
      btn.style.color = '#333';

      const customStyle = filterStylesConfig[filterName] || {};

      btn.onclick = () => {
        const isActive = btn.classList.toggle('is-active');

        if (isActive) {
          activeFilters.add(expression);
          Object.assign(btn.style, customStyle);
        } else {
          activeFilters.delete(expression);
          btn.style.background = '#f0f0f0';
          btn.style.color = '#333';
        }

        if (activeFilters.size === 0) {
          parentElement.querySelectorAll('.bbox').forEach(el => {
            el.classList.remove('is-filtered-out', 'is-ghost', 'is-forced-visible');
          });
          return;
        }

        const parsedFilters = Array.from(activeFilters).map(expr => {
          const match = expr.match(/^([\\w.]+)\\s*([=><])\\s*(.*)$/);
          return match ? { path: match[1], operator: match[2], target: match[3] } : null;
        }).filter(Boolean);

        const evaluateBox = (boxData) => {
          return parsedFilters.some(({ path, operator, target }) => {
            const resolvedValue = path.split('.').reduce((acc, part) => acc && acc[part], boxData);
            const evaluate = (v) => {
              if (v === undefined || v === null) return false;
              if (operator === '=') {
                const regexMatch = target.match(/^\\/(.*)\\/([gimsuy]*)$/);
                if (regexMatch) {
                  try { return new RegExp(regexMatch[1], regexMatch[2]).test(String(v)); } catch(e) { return false; }
                }
                return String(v) === String(target);
              }
              if (operator === '>') return Number(v) > Number(target);
              if (operator === '<') return Number(v) < Number(target);
              return false;
            };
            return Array.isArray(resolvedValue) ? resolvedValue.some(evaluate) : evaluate(resolvedValue);
          });
        };

        data.blocks.forEach(parentBox => {
          const pMatch = evaluateBox(parentBox);
          const matchingChildren = [];
          
          if (parentBox.children) {
            parentBox.children.forEach(childBox => {
              if (evaluateBox(childBox)) matchingChildren.push(childBox.id);
            });
          }

          const pEl = document.getElementById(parentBox.id);
          if (!pEl) return;

          if (pMatch || matchingChildren.length > 0) {
            pEl.classList.remove('is-filtered-out');
            if (!pMatch && matchingChildren.length > 0) pEl.classList.add('is-ghost');
            else pEl.classList.remove('is-ghost');
          } else {
            pEl.classList.add('is-filtered-out');
            pEl.classList.remove('is-ghost');
          }

          if (parentBox.children) {
            parentBox.children.forEach(childBox => {
              const cEl = document.getElementById(childBox.id);
              if (!cEl) return;
              if (matchingChildren.includes(childBox.id)) {
                cEl.classList.remove('is-filtered-out');
                cEl.classList.add('is-forced-visible');
              } else {
                cEl.classList.add('is-filtered-out');
                cEl.classList.remove('is-forced-visible');
              }
            });
          }
        });
      };
      filtersBar.appendChild(btn);
    });
  }

  // 4. ORDEN DE LECTURA (SVG GLOBAL PARA PADRES)
  if (orderPath && svgParents) {
    svgParents.classList.add('is-visible');
    const pColor = roStyles.color || '#ff9800';
    const pSpeed = roStyles.dashAnimationSpeed !== undefined ? roStyles.dashAnimationSpeed : 1;
    svgParents.style.setProperty('--ro-speed', `${20 * pSpeed}s`);

    const orderedParents = data.blocks.map((box, index) => {
      const orderVal = orderPath === true ? index : parseInt(orderPath.split('.').reduce((acc, part) => acc && acc[part], box), 10);
      return { box, orderVal };
    }).filter(item => !isNaN(item.orderVal)).sort((a, b) => a.orderVal - b.orderVal);

    if (orderedParents.length > 1) {
      const defsP = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
      defsP.innerHTML = roStyles.markerHeadHTML || `
        <marker id="arrowHeadP" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="${pColor}" />
        </marker>
      `;
      svgParents.appendChild(defsP);

      for (let i = 0; i < orderedParents.length - 1; i++) {
        const current = orderedParents[i].box;
        const next = orderedParents[i + 1].box;
        
        const curCoords = extractBBoxCoords(current, docSize);
        const nextCoords = extractBBoxCoords(next, docSize);
        if (!curCoords || !nextCoords) continue;
        
        const curW = curCoords.x2 - curCoords.x;
        const nextW = nextCoords.x2 - nextCoords.x;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', `${curCoords.x + (curW / 2)}%`);
        line.setAttribute('y1', `${curCoords.y}%`);
        line.setAttribute('x2', `${nextCoords.x + (nextW / 2)}%`);
        line.setAttribute('y2', `${nextCoords.y}%`);
        line.setAttribute('class', 'ro-line');
        line.style.stroke = pColor;
        
        const matchId = (roStyles.markerHeadHTML || '').match(/id="([^"]+)"/);
        line.setAttribute('marker-end', `url(#${matchId ? matchId[1] : 'arrowHeadP'})`);
        svgParents.appendChild(line);
      }
    }
  }
};
"""

_DOCUMENT_BLOCKS_COMPONENT = create_component(
    "document_blocks",
    html=___HTML,
    css=__CSS,
    js=__JS,
    isolate_styles=False,
)

ImageLike = Union[
    str,
    Path,
    Image.Image
]


def _to_image_src(image: ImageLike) -> str:
    """Normalize supported image inputs into an HTML img.src-compatible string."""
    if isinstance(image, str):
        # Accept URL, relative path served by app, or already-encoded data URL.
        return image

    if isinstance(image, Path):
        mime_type = mimetypes.guess_type(image.name)[0] or "image/png"
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    if isinstance(image, Image.Image):
        img_format = (image.format or "PNG").upper()
        mime_type = Image.MIME.get(img_format, f"image/{img_format.lower()}")
        buffer = BytesIO()
        image.save(buffer, format=img_format)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    raise ValueError("Unsupported image type")


def st_document_blocks(
        image: ImageLike,
        filters: dict,
        blocks: list,
        document_size: Optional[tuple[float | int, float | int]] = None,
        reading_order: Optional[str | bool] = None,
        set_state_on: Literal["hover", "click"] = "click",
        default_selected: Optional[str | int] = None,
        custom_styles: Optional[dict] = None,
        key: Optional[str] = None, width: Width = "stretch", height: Height = "content"
) -> Optional[str|int]:
    image_url = _to_image_src(image)

    doc_size = None
    if document_size:
        doc_size = {"width": document_size[0], "height": document_size[1]}

    data = {
        "imageUrl": image_url,
        "filters": filters,
        "reading_order": reading_order,
        "blocks": blocks,
        "document_size": doc_size,
        "set_state_on": set_state_on,
        "selected_id": default_selected,
        "styles": custom_styles,
    }

    result = _DOCUMENT_BLOCKS_COMPONENT(
        key=key,
        data=data,
        default={'selected_id': default_selected},
        on_selected_id_change=lambda: None,
        width=width,
        height=height,
    )

    return result.get("selected_id")


__all__ = ["st_document_blocks"]
