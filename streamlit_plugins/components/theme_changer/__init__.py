import logging

import streamlit as st
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

logger = logging.getLogger(__name__)

from streamlit_plugins.extension.button_group import st_button_group
try:
    from streamlit.web.server.routes import _DEFAULT_ALLOWED_MESSAGE_ORIGINS
except ImportError as e:
    _DEFAULT_ALLOWED_MESSAGE_ORIGINS = None


def add_trusted_url(url: str):
    if _DEFAULT_ALLOWED_MESSAGE_ORIGINS is not None:
        if url not in _DEFAULT_ALLOWED_MESSAGE_ORIGINS:
            st.web.server.routes._DEFAULT_ALLOWED_MESSAGE_ORIGINS.append(url)
    else:
        try:
            allowed_origins = list(st._config.get_option("client.allowedOrigins"))
        except RuntimeError:
            allowed_origins = []

        if url not in allowed_origins:
            allowed_origins.append(url)

        st._config.set_option("client.allowedOrigins", allowed_origins)

add_trusted_url("http://localhost")

import time

import streamlit as st
from typing import Literal

from .inject_script import inject_crossorigin_interface, change_theme_coi
from .entity import ThemeInput, ThemeInfo, ThemeBaseLight, ThemeBaseDark

KEY = "ThemeChangerComponent"

DEFAULT_CUSTOM_THEMES = {
    "dark": ThemeInput(
        name="dark",
        order=1,
        icon="brightness_2",
        themeInfo=ThemeInfo(
            base=ThemeBaseLight.base,
            primaryColor=ThemeBaseLight.primaryColor,
            backgroundColor=ThemeBaseLight.backgroundColor,
            secondaryBackgroundColor=ThemeBaseLight.secondaryBackgroundColor,
            textColor=ThemeBaseLight.textColor,
            font=ThemeBaseLight.font,
            widgetBackgroundColor=ThemeBaseLight.widgetBackgroundColor,
            widgetBorderColor=ThemeBaseLight.widgetBorderColor,
            skeletonBackgroundColor=ThemeBaseLight.skeletonBackgroundColor,
            bodyFont=ThemeBaseLight.bodyFont,
            codeFont=ThemeBaseLight.codeFont,
            fontFaces=ThemeBaseLight.fontFaces,
            radii=ThemeBaseLight.radii,
            fontSizes=ThemeBaseLight.fontSizes
        )
    ),
    "light": ThemeInput(
        name="light",
        order=2,
        icon="wb_sunny",
        themeInfo=ThemeInfo(
            base=ThemeBaseDark.base,
            primaryColor=ThemeBaseDark.primaryColor,
            backgroundColor=ThemeBaseDark.backgroundColor,
            secondaryBackgroundColor=ThemeBaseDark.secondaryBackgroundColor,
            textColor=ThemeBaseDark.textColor,
            font=ThemeBaseDark.font,
            widgetBackgroundColor=ThemeBaseDark.widgetBackgroundColor,
            widgetBorderColor=ThemeBaseDark.widgetBorderColor,
            skeletonBackgroundColor=ThemeBaseDark.skeletonBackgroundColor,
            bodyFont=ThemeBaseDark.bodyFont,
            codeFont=ThemeBaseDark.codeFont,
            fontFaces=ThemeBaseDark.fontFaces,
            radii=ThemeBaseDark.radii,
            fontSizes=ThemeBaseDark.fontSizes
        )
    )
}
DEFAULT_THEMES = {
    "light": ThemeInput(
        name="light",
        order=0,
        icon=":material/wb_sunny:",
        themeInfo=ThemeInfo(
            base=0
        )
    ),
    "dark": ThemeInput(
        name="dark",
        order=1,
        icon=":material/brightness_2:",
        themeInfo=ThemeInfo(
            base=1
        )
    )
}


@st.fragment
def _button_mode(theme_names, unique_key, render_mode, themes_data, timeout_rendering_theme_change, cross_key_theme_changers):
    theme_index: str = st.session_state[f"{KEY}_theme_index"]
    change_theme = st.button(
        icon=themes_data[theme_index].icon, label="Change Theme",
        key=f"{unique_key}_{render_mode}"
    )
    st.session_state[f"{unique_key}_need_update"] = False
    st.session_state[unique_key] = theme_index

    if change_theme:
        current_key = theme_names[theme_names.index(theme_index)]
        theme_index = theme_names[(theme_names.index(current_key) + 1) % len(theme_names)]

        # print(f"Changing theme to {themes_data[theme_index].name} from button[{unique_key}]")
        st.session_state[f"{KEY}_theme_index"] = theme_index

        for cross_theme_key in cross_key_theme_changers:
            st.session_state[f"{cross_theme_key}_need_update"] = True

        with st.container(key=f"{KEY}-{render_mode}-theme-index"):
            get_hide_style_coi_change_iframe(f"{KEY}-{render_mode}-theme-index")
            change_theme_coi(KEY, themes_data[theme_index])

        time.sleep(timeout_rendering_theme_change)
        if cross_key_theme_changers:
            st.rerun()
        else:
            st.rerun(scope="fragment")

@st.fragment
def _pills_mode(theme_names, unique_key, render_mode, themes_data, timeout_rendering_theme_change, cross_key_theme_changers):
    theme_index: str = st.session_state[f"{KEY}_theme_index"]
    if f"{unique_key}_{render_mode}" in st.session_state:
        new_theme_index = st.session_state[f"{unique_key}_{render_mode}"]

        # Si tiene valor significa que se esta ejecutando localmente, lanzado por la interfaz
        if st.session_state[f"{unique_key}_need_update"]:
            if theme_index != new_theme_index:
                # Actualizacion valor visual
                st.session_state[f"{unique_key}_{render_mode}"] = theme_index
                # Actualizacion valor interno
                st.session_state[unique_key] = theme_index
                # Desactivar flag de modificacion cruzada
                st.session_state[f"{unique_key}_need_update"] = False

    new_theme_index = st_button_group(
        "Change Theme",
        theme_names,
        default=theme_index,
        format_func=lambda option: themes_data[option].icon,
        style="segmented_control",
        keep_selection="always_visible",
        selection_mode="single",
        key=f"{unique_key}_{render_mode}",
    )

    if theme_index != new_theme_index:
        # print(f"Changing theme to {themes_data[new_theme_index].name} from pills[{unique_key}]")
        st.session_state[f"{KEY}_theme_index"] = new_theme_index
        # A partir de aqui continua si se cambio activamente en el pills widget
        for cross_theme_key in cross_key_theme_changers:
            st.session_state[f"{cross_theme_key}_need_update"] = True

        with st.container(key=f"{KEY}-{render_mode}-theme-index"):
            get_hide_style_coi_change_iframe(f"{KEY}-{render_mode}-theme-index")
            change_theme_coi(KEY, themes_data[new_theme_index])
        time.sleep(timeout_rendering_theme_change)
        st.rerun()

def get_hide_style_coi_change_iframe(key: str):
    st.markdown(
        """<style>
            :has(> KEY){
                display: none;
            }
        </style>
        """.replace(
            "KEY",
            f".st-key-{key}"
        ),
        unsafe_allow_html=True
    )

def st_theme_changer(
    themes_data: dict[str, ThemeInput] | None = None,
    render_mode: Literal["init", "change", "next", "button", "pills"] = "button",
    default_init_theme_name: str | None = None,
    timeout_rendering_theme_change: float = 0.2,
    key: str = "default",
    connected_theme_changers: list[str] = None
):
    """
    A Streamlit component to change the theme of the app.
    """

    if connected_theme_changers is None:
        connected_theme_changers = []
    cross_key_theme_changers = []
    for cross_theme_key in connected_theme_changers:
        cross_key_theme_changers.append(f"{KEY}_{cross_theme_key}")

    # -------------------------
    # Verification key index (Is different o each instance)
    if KEY not in st.session_state:
        st.session_state[KEY] = True

    unique_key = f"{KEY}_{key}"
    if f"{unique_key}_need_update" not in st.session_state:
        st.session_state[unique_key] = None
        st.session_state[f"{unique_key}_need_update"] = False
    # -------------------------

    if themes_data is None:
        themes_data = DEFAULT_THEMES.copy()

    # Sort themes by order
    theme_names = sorted(themes_data.keys(), key=lambda k: (themes_data[k].order, themes_data[k].name))

    # -------------------------
    # Theme changer logic (Is common to all instances)
    if f"{KEY}_theme_index" not in st.session_state:
        st.session_state[f"{KEY}_theme_index"] = theme_names[0]

    if f"{KEY}_COI_injected" not in st.session_state:
        inject_crossorigin_interface()
        st.session_state[f"{KEY}_COI_injected"] = True

        st_void = st.empty()
        with st_void.container(key=f"{KEY}-{render_mode}-theme-index"):
            get_hide_style_coi_change_iframe(f"{KEY}-{render_mode}-theme-index")
            change_theme_coi(KEY, themes_data[st.session_state[f"{KEY}_theme_index"]])
        time.sleep(0.1)  # Ensure enough time for client to load the script
        st_void.empty()

    render_init_condition = (render_mode == "init" and not st.session_state.get(f"{KEY}_init", False))

    if render_init_condition or render_mode == "change":
        st.session_state[f"{KEY}_init"] = True
        default_init_theme_name = default_init_theme_name or st.session_state[f"{KEY}_theme_index"]
        if default_init_theme_name not in theme_names:
            raise StreamlitAPIException(f"change_none_theme_index must be in {theme_names}")

        st.session_state[f"{KEY}_theme_index"] = default_init_theme_name
    
    elif render_mode == "next":
        next_theme_index = theme_names[(theme_names.index(st.session_state[f"{KEY}_theme_index"]) + 1) % len(theme_names)]
        st.session_state[f"{KEY}_theme_index"] = next_theme_index
    
    if render_mode in ["change", "next"] or render_init_condition:
        st_void = st.empty()
        inc = st.session_state.get(f"{KEY}_inc", 0)
        st.session_state[f"{KEY}_inc"] = inc + 1
        with st_void.container(key=f"{KEY}-{render_mode}-{inc}-theme-index"):
            get_hide_style_coi_change_iframe(f"{KEY}-{render_mode}-{inc}-theme-index")
            change_theme_coi(KEY, themes_data[st.session_state[f"{KEY}_theme_index"]])

            if render_mode == "next" or render_mode == "change":
                if connected_theme_changers:
                    st.rerun()
        
        time.sleep(0.1)  # Ensure enough time for client to load the script
        st_void.empty()


    # ctx = get_script_run_ctx()
    # Una vez creado el fragment_id, almacenarlo, y despues recuperarlo con el fragment_storage
    # ctx.fragment_storage.get
    # Despues, si se quiere hacer un rerun del mismo fragment y de otros, recuperar los fragment_id y lanzar el RerunData

    # ctx.script_requests.request_rerun(
    #     RerunData(
    #         query_string=query_string,
    #         page_script_hash=page_script_hash,
    #         fragment_id_queue=_new_fragment_id_queue(ctx, scope),
    #         is_fragment_scoped_rerun=scope == "fragment",
    #     )
    # )
    # # Force a yield point so the runner can do the rerun
    # st.empty()

    # -------------------------

    if render_mode == "button":
        _button_mode(theme_names, unique_key, render_mode, themes_data, timeout_rendering_theme_change, cross_key_theme_changers)

    elif render_mode == "pills":
        _pills_mode(theme_names, unique_key, render_mode, themes_data, timeout_rendering_theme_change, cross_key_theme_changers)


def get_active_theme_key() -> str | None:
    return st.session_state.get(f"{KEY}_theme_index", None)