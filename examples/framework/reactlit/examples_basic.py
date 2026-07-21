"""
Ejemplo básico: Reactive Framework
===================================

Demuestra:
- Fragmentos reactivos simples
- Dependencias lineales
- Detección de cambios
"""
import time

import streamlit as st
from streamlit_plugins.framework.reactlit.reactlit import (
    reactlit_fragment,
    enqueue_fragment_rerun,
    debug_dependency_graph,
    set_debug
)

set_debug(True)

def init_state():
    if 'counter' not in st.session_state:
        st.session_state.counter = 0


@reactlit_fragment(watch_params=True)
def fragment_counter_input():
    """Input para el contador"""
    st.subheader("Contador")

    new_val = st.number_input(
        "Valor:",
        value=st.session_state.counter,
        key="counter_input"
    )

    if new_val != st.session_state.counter:
        st.session_state.counter = new_val


@reactlit_fragment(
    dependencies=['counter'],
    watch_params=True
)
def fragment_counter_display():
    """Display del contador"""
    st.subheader("Valor Actual")
    st.metric("Contador", st.session_state.counter)



@reactlit_fragment(
    dependencies=['counter'],
    watch_params=True
)
def fragment_is_odd_display():
    """Display si el contador es impar"""
    st.subheader("Es impar")
    st.metric("Impar", st.session_state.counter % 2 != 0)


def heavy_task():
    for _ in range(10):
        time.sleep(1)
        yield _


def main():
    st.title("Reactive Fragment - Ejemplo Básico")

    init_state()

    fragment_counter_input()

    # Se deben llamar para que queden registrados
    with st.container(horizontal=True):
        fragment_counter_display()
        fragment_is_odd_display()

    st.toggle("Activa para accionar el rerun global")
    st.write_stream(heavy_task)

    debug_dependency_graph()


if __name__ == "__main__":
    main()

