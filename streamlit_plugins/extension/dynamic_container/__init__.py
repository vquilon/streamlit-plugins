import contextlib
from typing import Optional

import streamlit as st
from streamlit.components.v2 import component as create_component
from streamlit.elements.lib.layout_utils import Width, Height, HorizontalAlignment, VerticalAlignment, Gap

___HTML = """"""
__CSS = """
.scroll-select {
    animation: scroll-select-animation 1s ease-in-out;
}
@keyframes scroll-select-animation {
    0% { background-color: color-mix(in srgb, var(--scroll-bg-color) 50%, transparent);; }
    100% { background-color: transparent; }
}
"""
__JS = """
export default function(component) {
  const { data } = component;
  document.querySelector(`.st-key-${data.sourceContainerKey}-${data.targetContainerKey}-sync`).style.display = "none";
  setTimeout(function() {
      const sourceContainer = document.querySelector(data.sourceContainerSelector);
      const targetContainer = document.querySelector(data.targetContainerSelector);
      const scrollTo = document.querySelector(data.scrollToSelector);
      
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
      
      syncSize();
      
      // Observer pattern: sync on resize
      const observer = new ResizeObserver(syncSize);
      observer.observe(sourceContainer);
      window.addEventListener('resize', syncSize);
      
      if (scrollTo) {
        const previousActive = document.activeElement;
        targetContainer.focus({ preventScroll: true });
        scrollTo.scrollIntoView({
            block: 'center',    // Centra verticalmente respecto al padre
            inline: 'center',   // Centra horizontalmente si aplica
            behavior: 'smooth'
        });
        if (data.brightScrollTarget) {
            scrollTo.style.setProperty("--scroll-bg-color", data.brightScrollBg || "yellow")
            scrollTo.classList.add("scroll-select");
            setTimeout(function() {
                scrollTo.classList.remove("scroll-select");
            }, 1000);
        }
        
        previousActive?.focus({ preventScroll: true });
      }
      
  }, 500);
}
"""
_DYNAMIC_CONTAINER_COMPONENT = create_component(
    "dynamic_container_script",
    # html=___HTML,
    css=__CSS,
    js=__JS,
    isolate_styles=False,
)


@contextlib.contextmanager
def st_dynamic_container(
        *,
        container_source_key: str,
        key: str,
        mimic_vertical: bool = True,
        mimic_horizontal: bool = False,
        border: bool | None = None,
        width: Width = "stretch",
        height: Height = "content",
        horizontal: bool = False,
        horizontal_alignment: HorizontalAlignment = "left",
        vertical_alignment: VerticalAlignment = "top",
        gap: Gap | None = "small",
        autoscroll: bool | None = None,
):
    data = {
        "sourceContainerSelector": f".st-key-{container_source_key}",
        "targetContainerSelector": f".st-key-{key}",
        "sourceContainerKey": container_source_key,
        "targetContainerKey": key,
        "mimicVertical": mimic_vertical,
        "mimicHorizontal": mimic_horizontal,
    }

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
            key=f"{container_source_key}-{key}-sync",
            data=data
        )


__all__ = ["st_dynamic_container"]
