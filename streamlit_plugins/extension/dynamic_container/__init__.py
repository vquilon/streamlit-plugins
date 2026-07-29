import contextlib
from dataclasses import dataclass
from typing import Generator, Any, Optional, Literal

import streamlit as st
from streamlit.components.v2 import component as create_component
from streamlit.elements.lib.layout_utils import Width, Height, HorizontalAlignment, VerticalAlignment, Gap

__HTML = """"""
__CSS = """
.scroll-select {
    animation: scroll-select-animation 1s ease-in-out;
}
@keyframes scroll-select-animation {
    0% { background-color: color-mix(in srgb, var(--scroll-bg-color) 50%, transparent); }
    100% { background-color: transparent; }
}
"""
__JS = """
       export default function (component) {
           const {setStateValue, parentElement, data} = component;
           document.querySelector(data.componentKeySelector).style.display = "none";

           const sourceContainer = document.querySelector(data.sourceContainerSelector);
           const targetContainer = document.querySelector(data.targetContainerSelector);

           const resolveScrollTarget = (selectorOrId) => {
               if (!selectorOrId) return null;

               try {
                   return document.querySelector(selectorOrId);
               } catch (_) {
                   // Fallback: treat value as an element id and escape special chars.
               }

               const normalized = String(selectorOrId).trim();
               if (!normalized) return null;

               const rawId = normalized.startsWith('#') ? normalized.slice(1) : normalized;
               if (!rawId) return null;

               try {
                   const escapedId = (typeof CSS !== 'undefined' && typeof CSS.escape === 'function')
                       ? CSS.escape(rawId)
                       : rawId;
                   return document.querySelector(`#${escapedId}`);
               } catch (_) {
                   return null;
               }
           };

           const scrollTo = resolveScrollTarget(data.scrollToSelector);
           if (!sourceContainer || !targetContainer) return;

           if (data.customCSS) {
               const style = parentElement.querySelector("style.dynamic-container-custom-css");
               if (style) {
                   style.textContent = data.customCSS;
               } else {
                   const newStyle = document.createElement("style");
                   newStyle.className = "dynamic-container-custom-css";
                   newStyle.textContent = data.customCSS;
                   parentElement.appendChild(newStyle);
               }
           }

           const syncSize = () => {
               const sourceHeight = sourceContainer.clientHeight;
               const sourceWidth = sourceContainer.clientWidth;

               if (data.mimicVertical) {
                   targetContainer.style.height = `${sourceHeight}px`;
                   targetContainer.parentElement.style.height = `${sourceHeight}px`;
               }
               if (data.mimicHorizontal) {
                   targetContainer.style.width = `${sourceWidth}px`;
                   targetContainer.parentElement.style.width = `${sourceWidth}px`;
               }
           };

           // Set overflow
           if (data.mimicVertical && !data.mimicHorizontal) {
               targetContainer.style.overflowY = 'auto';
           }
           if (data.mimicHorizontal && !data.mimicVertical) {
               targetContainer.style.overflowX = 'auto';
           }
           if (data.mimicVertical && data.mimicHorizontal) {
               targetContainer.style.overflow = 'auto';
           }

           if (!parentElement.firstResized) {
               syncSize();
               parentElement.firstResized = true;
               // Observer pattern: sync on resize
               const observer = new ResizeObserver(syncSize);
               observer.observe(sourceContainer);
               window.addEventListener('resize', syncSize);
           }

           if (scrollTo) {
               const previousActive = document.activeElement;
               targetContainer.focus({preventScroll: true});
               scrollTo.scrollIntoView({
                   block: 'center',    // Centra verticalmente respecto al padre
                   inline: 'center',   // Centra horizontalmente si aplica
                   behavior: 'smooth'
               });
               if (data.flashBrightScrollTarget) {
                   if (data.highlightItemClass) {
                       document.querySelectorAll(`.${data.highlightItemClass}`).forEach(el => {
                           el.classList.remove(data.highlightItemClass);
                       });
                       scrollTo.classList.add(data.highlightItemClass);
                   }
                   scrollTo.style.setProperty("--scroll-bg-color", data.flashBrightScrollBg || "yellow")
                   scrollTo.classList.add("scroll-select");
                   setTimeout(function () {
                       scrollTo.classList.remove("scroll-select");
                   }, 1000);
               }

               previousActive?.focus({preventScroll: true});
           }

           if (data.observeType !== null && data.activeScrollFrom) {
               const emitSelected = (item) => {
                   if (typeof setStateValue === 'function') {
                       setStateValue('selected_id', item?.id || null);
                   }
               };

               const getActiveItem = (event) => {
                   const eventTarget = event.target;
                   if (!(eventTarget instanceof Element)) return null;

                   const item = eventTarget.closest(data.activeScrollFrom);
                   return item && targetContainer.contains(item) ? item : null;
               };

               if (data.observeType === 'hover') {
                   let activeItem = null;

                   targetContainer.onmousemove = (event) => {
                       const item = getActiveItem(event);
                       if (item === activeItem) return;
                       if (data.activeKeepOnLeave && item === null) return;
                       activeItem = item;

                       if (activeItem !== null) {
                           if (data.highlightItemClass) {
                               document.querySelectorAll(`.${data.highlightItemClass}`).forEach(el => {
                                   el.classList.remove(data.highlightItemClass);
                               });
                               activeItem.classList.add(data.highlightItemClass);
                           }
                       }
                       emitSelected(item);
                   };

                   // targetContainer.onmouseleave = () => {
                   //     activeItem = null;
                   //     emitSelected(null);
                   // };
               }
               targetContainer.onclick = (event) => {
                   const item = getActiveItem(event);
                   if (!item) return;
                   event.stopPropagation();

                   if (data.highlightItemClass) {
                       document.querySelectorAll(`.${data.highlightItemClass}`).forEach(el => {
                           el.classList.remove(data.highlightItemClass);
                       });
                       item.classList.add(data.highlightItemClass);
                   }


                   emitSelected(item);
               };
           }
       }
       """
_DYNAMIC_CONTAINER_COMPONENT = create_component(
    "dynamic_container_script",
    # html=__HTML,
    css=__CSS,
    js=__JS,
    isolate_styles=False,
)

@dataclass
class DynamicContainerDataInput:
    sourceContainerSelector: str
    targetContainerSelector: str
    componentKeySelector: str
    sourceContainerKey: str
    resultActiveObservedKey: str
    targetContainerKey: str
    mimicVertical: bool
    mimicHorizontal: bool

    scrollToSelector: Optional[str] = None
    flashBrightScrollTarget: Optional[bool] = None
    flashBrightScrollBg: Optional[str] = None
    highlightItemClass: Optional[str] = None
    activeScrollFrom: Optional[str] = None
    activeKeepOnLeave: bool = True
    customCSS: Optional[str] = None
    observeType: Optional[Literal["hover", "click"]] = None

    def to_dict(self):
        return self.__dict__

@contextlib.contextmanager
def st_dynamic_container(
        *,
        container_source_key: str,
        key: str,
        mimic_vertical: bool = True,
        mimic_horizontal: bool = False,
        active_observed_item_key: Optional[str] = None,
        result_active_observed_key: str = "selected_id",
        active_observed_selector: Optional[str] = None,
        active_keep_item_on_leave_mouse: bool = True,
        active_highlight_item_class: Optional[str] = None,
        observer_type: Optional[Literal["hover", "click"]] = None,
        custom_css: Optional[str] = None,
        border: bool | None = None,
        width: Width = "stretch",
        height: Height = "content",
        horizontal: bool = False,
        horizontal_alignment: HorizontalAlignment = "left",
        vertical_alignment: VerticalAlignment = "top",
        gap: Gap | None = "small",
        autoscroll: bool | None = None,
) -> Generator[DynamicContainerDataInput, Any, None]:
    component_key = active_observed_item_key if active_observed_item_key is not None else f"{container_source_key}-{key}-sync"
    data = DynamicContainerDataInput(
        sourceContainerSelector=f".st-key-{container_source_key}",
        targetContainerSelector=f".st-key-{key}",
        componentKeySelector=f".st-key-{component_key}",
        resultActiveObservedKey=result_active_observed_key,
        sourceContainerKey=container_source_key,
        targetContainerKey=key,
        mimicVertical=mimic_vertical,
        highlightItemClass=active_highlight_item_class,
        mimicHorizontal=mimic_horizontal,
        activeScrollFrom=active_observed_selector,
        activeKeepOnLeave=active_keep_item_on_leave_mouse,
        observeType=observer_type,
        customCSS=custom_css
    )

    with st.container(
            key=key,
            border=border,
            width=width,
            height=height,
            horizontal=horizontal,
            horizontal_alignment=horizontal_alignment,
            vertical_alignment=vertical_alignment,
            gap=gap,
            autoscroll=autoscroll,
    ):
        yield data
        _DYNAMIC_CONTAINER_COMPONENT(
            key=component_key,
            data=data.to_dict()
        )

__all__ = ["st_dynamic_container"]
