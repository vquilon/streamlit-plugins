"""
Ejemplo: write_stream con run_every vs reactlit
===============================================

Compara dos aproximaciones sobre el mismo caso:
- `run_every`: fragmentos nativos que se refrescan por temporizador.
- `reactlit`: fragmentos que reaccionan a cambios en `st.session_state`.

Ejecutar:
    streamlit run example_streaming.py
"""

from __future__ import annotations

import time

import streamlit as st
from streamlit_plugins.framework.reactlit.reactlit import (
    debug_dependency_graph,
    reactlit_fragment,
    set_debug
)

set_debug(True)

STREAM_DURATION_SECONDS = 60.0
STREAM_TICK_SECONDS = 0.2
STREAM_SOURCE = (
    "write_stream sigue generando texto mientras pruebas como reacciona cada enfoque. "
)


def init_state() -> None:
    defaults = {
        "use_run_every": True,
        "editable_counter": 0,
        "target_chars_per_second": 24,
        "stream_requested_id": 0,
        "stream_active_id": 0,
        "stream_running": False,
        "stream_elapsed_seconds": 0.0,
        "streamed_chars": 0,
        "streamed_tens": 0,
        "stream_average_cps": 0.0,
        "stream_source_offset": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_stream_metrics() -> None:
    st.session_state.stream_running = False
    st.session_state.stream_elapsed_seconds = 0.0
    st.session_state.streamed_chars = 0
    st.session_state.streamed_tens = 0
    st.session_state.stream_average_cps = 0.0
    st.session_state.stream_source_offset = 0


def next_chunk(size: int, offset: int) -> tuple[str, int]:
    repeated = STREAM_SOURCE * ((size // len(STREAM_SOURCE)) + 2)
    start = offset % len(STREAM_SOURCE)
    end = start + size
    return repeated[start:end], end % len(STREAM_SOURCE)


def stream_payload():
    started_at = time.monotonic()
    deadline = started_at + STREAM_DURATION_SECONDS
    streamed_chars = 0
    offset = st.session_state.stream_source_offset

    st.session_state.stream_running = True

    while True:
        now = time.monotonic()
        if now >= deadline:
            break

        target_cps = max(1, int(st.session_state.target_chars_per_second))
        chunk_size = max(1, int(round(target_cps * STREAM_TICK_SECONDS)))
        chunk, offset = next_chunk(chunk_size, offset)

        streamed_chars += len(chunk)
        elapsed = max(now - started_at, STREAM_TICK_SECONDS)

        st.session_state.stream_source_offset = offset
        st.session_state.stream_elapsed_seconds = elapsed
        st.session_state.streamed_chars = streamed_chars
        st.session_state.streamed_tens = streamed_chars // 10
        st.session_state.stream_average_cps = streamed_chars / elapsed

        yield chunk
        time.sleep(min(STREAM_TICK_SECONDS, max(deadline - time.monotonic(), 0.0)))

    final_elapsed = max(time.monotonic() - started_at, 1e-6)
    st.session_state.stream_running = False
    st.session_state.stream_elapsed_seconds = final_elapsed
    st.session_state.stream_average_cps = st.session_state.streamed_chars / final_elapsed


def render_metrics(title: str) -> None:
    st.subheader(title)
    col1, col2, col3 = st.columns(3)
    col1.metric("Estado", "running" if st.session_state.stream_running else "idle")
    col2.metric("Chars emitidos", st.session_state.streamed_chars)
    col3.metric("Bloques de 10", st.session_state.streamed_tens)

    col4, col5 = st.columns(2)
    col4.metric("CPS objetivo", st.session_state.target_chars_per_second)
    col5.metric("CPS medio", f"{st.session_state.stream_average_cps:.1f}")

    st.caption(f"Tiempo: {st.session_state.stream_elapsed_seconds:.1f}s / 60.0s")


def controls(with_launch_stream=False):
    st.subheader("Controles")

    counter = st.number_input(
        "Valor del contador",
        min_value=0,
        step=1,
        value=st.session_state.editable_counter,
        key="reactlit_counter_input",
    )
    if counter != st.session_state.editable_counter:
        st.session_state.editable_counter = counter

    cps = st.number_input(
        "Caracteres por segundo objetivo",
        min_value=1,
        max_value=200,
        step=1,
        value=st.session_state.target_chars_per_second,
        key="reactlit_cps_input",
    )
    if cps != st.session_state.target_chars_per_second:
        st.session_state.target_chars_per_second = cps

    if st.button("Reset métricas", key="reactlit_reset", disabled=st.session_state.stream_running):
        reset_stream_metrics()

    if with_launch_stream:
        if st.button("Lanzar stream de 1 minuto", key="reactlit_start", disabled=st.session_state.stream_running):
            st.session_state.stream_requested_id += 1
            reset_stream_metrics()


@st.fragment(run_every=0.2, parallel=True)
def fragment_native_counter_display() -> None:
    st.subheader("Display del contador")
    st.metric("Contador", st.session_state.editable_counter)


@st.fragment(run_every=0.2, parallel=True)
def fragment_native_stream_stats() -> None:
    render_metrics("Métricas del stream")


@st.fragment(parallel=True)
def fragment_native_stream_output() -> None:
    st.subheader("Salida de write_stream")

    requested_id = st.session_state.stream_requested_id
    active_id = st.session_state.stream_active_id

    if requested_id <= active_id:
        st.write("Pulsa el botón para arrancar el stream.")
        return

    st.session_state.stream_active_id = requested_id
    st.write_stream(stream_payload)
    st.success("Stream terminado.")


@st.fragment(parallel=True)
def fragment_native_controls() -> None:
    controls(with_launch_stream=False)

@reactlit_fragment(watch_params=True)
def fragment_reactlit_controls() -> None:
    controls(with_launch_stream=True)


@reactlit_fragment(parallel=True, dependencies=["editable_counter"], watch_params=True)
def fragment_reactlit_counter_display() -> None:
    st.subheader("Display del contador")
    st.metric("Contador", st.session_state.editable_counter)


@reactlit_fragment(
    parallel=True,
    dependencies=[
        "stream_running",
        "streamed_chars",
        "streamed_tens",
        "stream_average_cps",
        "stream_elapsed_seconds",
        "target_chars_per_second",
    ],
    watch_params=True,
)
def fragment_reactlit_stream_stats() -> None:
    render_metrics("Métricas del stream")


@reactlit_fragment(parallel=True, dependencies=["stream_requested_id"], watch_params=True)
def fragment_reactlit_stream_output() -> None:
    st.subheader("Salida de write_stream")

    requested_id = st.session_state.stream_requested_id
    active_id = st.session_state.stream_active_id

    if st.session_state.stream_running:
        st.info("Streaming en curso…")
        return

    if requested_id <= active_id:
        st.write("Pulsa el botón para arrancar el stream.")
        return

    st.session_state.stream_active_id = requested_id
    st.write_stream(stream_payload)
    st.success("Stream terminado.")


def render_native_mode() -> None:
    st.info(
        "Modo nativo: los controles viven fuera de fragmentos para forzar un rerun principal; "
        "la salida corre en un fragmento y los paneles laterales se refrescan en paralelo."
    )

    left, right = st.columns([1, 2])
    with left:
        fragment_native_controls()

        if st.button("Lanzar stream de 1 minuto", key="reactlit_start", disabled=st.session_state.stream_running):
            st.session_state.stream_requested_id += 1
            reset_stream_metrics()

        st.divider()
        fragment_native_counter_display()
        st.divider()
        fragment_native_stream_stats()
    with right:
        fragment_native_stream_output()


def render_reactlit_mode() -> None:
    st.info(
        "Modo `reactlit`: los cambios en `session_state` disparan dependencias, "
        "pero este ejemplo deja visible que `write_stream` mantiene ocupado el fragmento largo."
    )

    left, right = st.columns([1, 2])
    with left:
        fragment_reactlit_controls()
        st.divider()
        fragment_reactlit_counter_display()
        st.divider()
        fragment_reactlit_stream_stats()
    with right:
        fragment_reactlit_stream_output()

    debug_dependency_graph()


def main() -> None:
    st.set_page_config(page_title="write_stream: run_every vs reactlit", layout="wide")
    init_state()

    st.title("write_stream: triggerado vs reactivo")
    st.toggle(
        "Usar run_every (desactiva para probar reactlit)",
        key="use_run_every",
        disabled=st.session_state.stream_running,
    )

    if st.session_state.use_run_every:
        render_native_mode()
        return

    render_reactlit_mode()


if __name__ == "__main__":
    main()
