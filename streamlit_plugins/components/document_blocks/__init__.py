import base64
import contextlib
import mimetypes
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, TypedDict, Callable
from typing import Generator
from typing import Optional, Union, Literal

import streamlit as st
from PIL import Image
from streamlit.components.v2 import component as create_component
from streamlit.delta_generator import DeltaGenerator
from streamlit.elements.lib.layout_utils import Width, Height
from streamlit.elements.lib.mutable_tab_container import TabContainer

from streamlit_plugins.extension.dynamic_container import st_dynamic_container


ImageLike = Union[
    str,
    Path,
    Image.Image
]


@dataclass
class Block:
    id: str | int
    content: str
    label: str
    bbox: list[int]
    polygon: list[list[int]]
    metadata: dict
    children: Optional[list["Block"]] = None


@dataclass
class Document:
    name: str
    size: tuple[int, int]
    blocks: dict[int, list[Block | dict]]
    images: dict[int, ImageLike]

    @property
    def pages(self) -> int:
        return len(self.blocks)


__HTML = """
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
               coords = {x: box.bbox[0], y: box.bbox[1], x2: box.bbox[2], y2: box.bbox[3]};
           } else if (box.polygon && Array.isArray(box.polygon) && box.polygon.length >= 2) {
               // polygon format: [[x1,y1], [x2,y2], ...]
               let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
               box.polygon.forEach(([x, y]) => {
                   minX = Math.min(minX, x);
                   minY = Math.min(minY, y);
                   maxX = Math.max(maxX, x);
                   maxY = Math.max(maxY, y);
               });
               coords = {x: minX, y: minY, x2: maxX, y2: maxY};
           } else if (box.x !== undefined && box.y !== undefined && box.w !== undefined && box.h !== undefined) {
               // legacy format: x, y, w, h (assuming percentages)
               coords = {x: box.x, y: box.y, x2: box.x + box.w, y2: box.y + box.h, isLegacy: true};
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

       export default function (component) {
           const {setStateValue, setTriggerValue, parentElement, data} = component;

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
           const blockStyles = data.styles && data.styles.blocks ? data.styles.blocks : {};
           const normalAlpha = blockStyles.normalAlpha !== undefined ? blockStyles.normalAlpha : 0.15;
           const hoverAlpha = blockStyles.hoverAlpha !== undefined ? blockStyles.hoverAlpha : 0.35;
           const childNormalAlpha = blockStyles.childNormalAlpha !== undefined ? blockStyles.childNormalAlpha : 0.25;
           const childHoverAlpha = blockStyles.childHoverAlpha !== undefined ? blockStyles.childHoverAlpha : 0.50;

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
                       return {child, orderVal};
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
                           return match ? {path: match[1], operator: match[2], target: match[3]} : null;
                       }).filter(Boolean);

                       const evaluateBox = (boxData) => {
                           return parsedFilters.some(({path, operator, target}) => {
                               const resolvedValue = path.split('.').reduce((acc, part) => acc && acc[part], boxData);
                               const evaluate = (v) => {
                                   if (v === undefined || v === null) return false;
                                   if (operator === '=') {
                                       const regexMatch = target.match(/^\\/(.*)\\/([gimsuy]*)$/);
                                       if (regexMatch) {
                                           try {
                                               return new RegExp(regexMatch[1], regexMatch[2]).test(String(v));
                                           } catch (e) {
                                               return false;
                                           }
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
                   return {box, orderVal};
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
       }; \
       """

_DOCUMENT_BLOCKS_COMPONENT = create_component(
    "document_blocks",
    html=__HTML,
    css=__CSS,
    js=__JS,
    isolate_styles=False,
)

REQUIRED_BLOCK_FIELDS = [
    'id',
    'type',
    'content',
    ('bbox', 'polygon'),
    'color'
    # 'section_hierarchy',
    # 'metadata',
    # 'children'
]


class BlockFieldAssociation(TypedDict):
    id: str
    type: str
    content: str
    bbox: str
    color: str | Callable[["BlockFieldAssociation"], str]
    section_hierarchy: Optional[str]
    metadata: Optional[str]
    children: Optional[str]
    html: Optional[str]
    markdown: Optional[str]


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

def _check_required_fields(block: dict) -> bool:
    for field in REQUIRED_BLOCK_FIELDS:
        if isinstance(field, str):
            if field not in block:
                raise ValueError(f"Missing required field {field}")
        elif isinstance(field, tuple):
            if not any(f in block for f in field):
                raise ValueError(f"Missing required field(s) {field}")

        if 'children' in block:
            for child_block in block['children']:
                return _check_required_fields(child_block)

    return True

@st.cache_data(show_spinner=True, show_time=True)
def _normalize_fields(blocks: list[dict], _block_field_spec: BlockFieldAssociation, delete_prev_fields=False) -> list[dict]:
    for block in blocks:
        children_field = "children"
        if "children" in _block_field_spec:
            children_field = _block_field_spec['children']

        if children_field in block:
            block["children"] = _normalize_fields(block[children_field], _block_field_spec)
            if children_field != "children" and delete_prev_fields:
                del block[children_field]

        for normalized_field, block_field in _block_field_spec.items():
            if "children" == normalized_field:
                continue

            if callable(block_field):
                block[normalized_field] = block_field(block)
            else:
                block[normalized_field] = block[block_field]
                if delete_prev_fields:
                    del block[block_field]

    return blocks

@st.cache_data(show_spinner=True, show_time=True)
def _concat_content(blocks: list[dict], content_type: Literal["html", "markdown"], parent_content_has_children: bool = True) -> str:
    whole_content = ""
    for block in blocks:
        if content_type in block:
            whole_content += block[content_type]
        if not parent_content_has_children and "children" in block:
            whole_content += _concat_content(block["children"], content_type, parent_content_has_children=parent_content_has_children)

    return whole_content

def st_document_blocks(
        image: ImageLike,
        filters: dict,
        blocks: list[dict],
        block_field_spec: Optional[BlockFieldAssociation] = None,
        document_size: Optional[tuple[float | int, float | int]] = None,
        reading_order: Optional[str | bool] = None,
        set_state_on: Literal["hover", "click"] = "click",
        default_selected: Optional[str | int] = None,
        custom_styles: Optional[dict] = None,
        key: Optional[str] = None, width: Width = "stretch", height: Height = "content"
) -> tuple[list[dict], Optional[str | int]]:
    image_url = _to_image_src(image)

    doc_size = None
    if document_size:
        doc_size = {"width": document_size[0], "height": document_size[1]}

    blocks_normalized = blocks.copy()
    if block_field_spec is not None:
        blocks_normalized = _normalize_fields(blocks_normalized, block_field_spec)

    assert all(_check_required_fields(block) for block in blocks_normalized)

    data = {
        "imageUrl": image_url,
        "filters": filters,
        "reading_order": reading_order,
        "blocks": blocks_normalized,
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

    return blocks_normalized, result.get("selected_id")


def search_block_recursive(search_by: dict, _blocks: list[dict], any_match=False) -> tuple[dict | None, dict | None]:
    for block in _blocks:
        if (
            any(block[key] == value if key in block else False for key, value in search_by.items()) if any_match
            else all(block[key] == value if key in block else False for key, value in search_by.items())
        ):
            return block, None
        if "children" in block:
            result, _ = search_block_recursive(search_by, block["children"], any_match=any_match)
            if result:
                return result, block
    return None, None

def _format_raw_code(language: Literal["html", "markdown"], content: str):
    if language == "html":
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("BeautifulSoup4 is required for HTML formatting. Please install it with `pip install beautifulsoup4`.")

        soup = BeautifulSoup(content, "html.parser")

        # Aplicar el beautifier
        clean_html = soup.prettify()
        return clean_html

    elif language == "markdown":
        try:
            import mdformat
        except ImportError:
            raise ImportError("Markdown and Markdownify are required for Markdown formatting. Please install them with `pip install mdformat mdformat-gfm`.")

        # Convertir a HTML y luego de vuelta a Markdown para formatear
        clean_markdown = mdformat.text(content)
        return clean_markdown

    else:
        raise ValueError("Unknown language {}".format(language))



def search_blocks_recursive(search_by: dict, _blocks: list[dict], any_match=False, level=0) -> list[tuple[dict, int]]:
    """
    Devuelve unas tuplas con los bloques que cumplen los criterios pero de forma anidada incluyendo el nivel de recursividad
    :param search_by:
    :param _blocks:
    :param any_match:
    :return:
    """

    results = []
    for block in _blocks:
        if (
                any(block[key] == value if key in block else False for key, value in search_by.items()) if any_match
                else all(block[key] == value if key in block else False for key, value in search_by.items())
        ):
            results.append((block, level))
        if "children" in block:
            child_results = search_blocks_recursive(search_by, block["children"], any_match=any_match, level=level + 1)
            for child_result, child_level in child_results:
                results.append((child_result, child_level))
    return results



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


@contextlib.contextmanager
@st.fragment
def st_documents_blocks_info(
        document: Document,
        filters: dict,
        block_field_spec: Optional[BlockFieldAssociation] = None,
        custom_styles: Optional[dict] = None,
        reading_order: Optional[str | bool] = None,
        parent_content_has_children: bool = True,
        show_blocks: bool | str = True,
        show_json: bool | str = True,
        show_html: bool | str = True,
        show_markdown: bool | str = True,
        tab_order: Optional[list[Literal["Blocks", "JSON", "HTML", "Markdown"] | str]] = None,
        custom_tabs: Optional[list[str]] = None,
        format_raw_code: bool = False,
) -> Generator[tuple[list[dict], list[TabContainer]], Any, None]:
    main_container = st.container(horizontal=True)
    page_selected = 1
    if document.pages > 1:
        with st.container(horizontal_alignment="right"):
            page_selected = st.pagination(
                document.pages,
            )

    blocks_page = document.blocks[page_selected]
    image = document.images[page_selected]

    with main_container:
        with st.container(width="content"):
            show_reading_order = st.toggle("Reading Order")
            if not show_reading_order:
                reading_order = None
            st.space(size=1)

            dynamic_selected_block_result = st.session_state.get(HOVER_BLOCK_RESULT_KEY)

            dynamic_selected_block_id = None
            if dynamic_selected_block_result:
                dynamic_selected_block_id = dynamic_selected_block_result.get(RESULT_ACTIVE_OBSERVED_KEY)
                if dynamic_selected_block_id:
                    dynamic_selected_block_id = dynamic_selected_block_id[1:]

            blocks_normalized, selected_block_id = st_document_blocks(
                image,
                filters,
                blocks_page,
                block_field_spec=block_field_spec,
                document_size=document.size,
                reading_order=reading_order,
                custom_styles=custom_styles,
                default_selected=dynamic_selected_block_id,
                set_state_on="hover",
                width="content",
                height=600,
                key="document_blocks"
            )

        tabs = []
        blocks_label = "Blocks"
        json_label = "JSON"
        html_label = "HTML"
        markdown_label = "Markdown"

        if show_blocks:
            if isinstance(show_blocks, str):
                blocks_label = show_blocks
            tabs.append(blocks_label)

        if show_json:
            if isinstance(show_json, str):
                json_label = show_json
            tabs.append(json_label)

        if show_html:
            if isinstance(show_html, str):
                html_label = show_html
            tabs.append(html_label)

        if show_markdown:
            if isinstance(show_markdown, str):
                markdown_label = show_markdown
            tabs.append(markdown_label)

        if custom_tabs is not None and custom_tabs:
            tabs.extend(custom_tabs)

        if tab_order is not None:
            tabs = [tab for tab in tab_order if tab in tabs]

        st_cols = st.tabs(
            tabs,
            on_change=on_tab_change
        )

        blocks_col = None
        json_col = None
        html_col = None
        markdown_col = None

        if show_blocks:
            blocks_col = st_cols[tabs.index(blocks_label)]
        if show_json:
            json_col = st_cols[tabs.index(json_label)]
        if show_html:
            html_col = st_cols[tabs.index(html_label)]
        if show_markdown:
            markdown_col = st_cols[tabs.index(markdown_label)]

        block_selected = None
        if selected_block_id is not None:
            block_selected, parent_block = search_block_recursive({"id": selected_block_id}, blocks_page)
            if parent_block is not None:
                block_selected = parent_block

        if custom_tabs:
            # Return custom tabs
            st_custom_cols = [st_cols[tabs.index(tab)] for tab in tabs if tab in custom_tabs]
            yield blocks_normalized, st_custom_cols

        if blocks_col and blocks_col.open:
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
                    for block in blocks_normalized:
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

        elif json_col and json_col.open:
            with json_col:
                with st_dynamic_container(
                        container_source_key="document_blocks",
                        key="view-container", mimic_vertical=True, border=True
                ):
                    st.json(blocks_page)

        elif html_col and html_col.open:
            with html_col:
                render_col, raw_col = st.tabs(
                    ["Renderer", "Raw"],
                    on_change=on_tab_change
                )
                with st_dynamic_container(
                        container_source_key="document_blocks",
                        key="view-container", mimic_vertical=True, border=True
                ):

                    html_content = _concat_content(blocks_normalized, content_type="html", parent_content_has_children=parent_content_has_children)
                    if not html_content:
                        st.warning("HTML content is empty. Please ensure that the blocks contain valid HTML content.")
                    if render_col.open:
                        with render_col:
                            st.write(html_content, unsafe_allow_html=True)
                    elif raw_col.open:
                        with raw_col:
                            if format_raw_code:
                                html_content = _format_raw_code("html", html_content)
                            st.code(html_content, language="html", line_numbers=True, wrap_lines=True)

        elif markdown_col and markdown_col.open:
            with markdown_col:
                with st_dynamic_container(
                    container_source_key="document_blocks",
                    key="view-container", mimic_vertical=True, border=True
                ):
                    render_col, raw_col = st.tabs(
                        ["Renderer", "Raw"],
                        on_change=on_tab_change
                    )
                    markdown_content = _concat_content(blocks_normalized, content_type="markdown", parent_content_has_children=parent_content_has_children)
                    if not markdown_content:
                        st.warning("Markdown content is empty. Please ensure that the blocks contain valid Markdown content.")
                    if render_col.open:
                        with render_col:
                            st.markdown(markdown_content, unsafe_allow_html=True)
                    elif raw_col.open:
                        with raw_col:
                            if format_raw_code:
                                markdown_content = _format_raw_code("markdown", markdown_content)
                            st.code(markdown_content, language="markdown", line_numbers=True, wrap_lines=True)

__all__ = ["st_document_blocks", "st_documents_blocks_info"]
