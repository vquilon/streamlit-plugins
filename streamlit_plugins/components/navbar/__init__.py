import inspect
import time
from typing import Literal
import warnings
import logging
from urllib.parse import urlparse

import requests
import streamlit

import streamlit as st
import streamlit.components.v1 as components
from streamlit.navigation.page import StreamlitPage
# from streamlit.runtime.scriptrunner import RerunException, get_script_run_ctx
# from streamlit.proto.WidgetStates_pb2 import WidgetState, WidgetStates
try:
    from streamlit.web.server.routes import _DEFAULT_ALLOWED_MESSAGE_ORIGINS
except ImportError as e:
    _DEFAULT_ALLOWED_MESSAGE_ORIGINS = None

try:
    from streamlit.runtime.scriptrunner.script_requests import ScriptRequestType, RerunData
except ModuleNotFoundError:
    from streamlit.runtime.scriptrunner_utils.script_requests import ScriptRequestType, RerunData

from .config import dev_url, build_path, _RELEASE
from .inject_script import apply_styles, inject_crossorigin_interface, instantiate_crossorigin_interface

if _RELEASE:
    _component_func = components.declare_component("nav_bar", path=str(build_path))
else:
    _component_func = components.declare_component("nav_bar", url=dev_url)


logger = logging.getLogger(__name__)

NavbarPositionType = Literal["top", "under", "side", "static", "hidden"]

NAVIGATION_KEY_PREFIX = "__navigation"
NAVBAR_KEY_PREFIX = "__navbar"
NAVIGATION_COMPONENT_KEY = "navigation-component"
GAP_BETWEEN_COMPS = 1
TOP_SIDE_ELEMENTS_MARGIN = 1.05
TOP_SIDE_ELEMENTS_WIDTH = 4
TOP_LINE_HEIGHT = 0.125
MARGIN_SIDE_NARROW_DIFF = 2
MARGIN_SIDE_NAVBAR = 0.5
SCROLLBAR_WIDTH = 6  # px
HEADER_HEIGHT = 3.75

APP_VIEWER_SELECTOR = ".stAppViewContainer"
COLLAPSE_CONTROLL_CLASS = "collapsedControl"
major, minnor, bug = st.__version__.split('.')
major, minnor, bug = int(major), int(minnor), int(bug)
if major == 1:
    if 36 < minnor <= 37:
        APP_VIEWER_SELECTOR = '[data-testid="stAppViewContainer"]'
        COLLAPSE_CONTROLL_CLASS = "collapsedControl"
    if minnor >= 38:
        APP_VIEWER_SELECTOR = ".stAppViewContainer"
        COLLAPSE_CONTROLL_CLASS = "stSidebarCollapsedControl"


def add_trusted_url(url: str):
    if _DEFAULT_ALLOWED_MESSAGE_ORIGINS is not None:
        if url not in _DEFAULT_ALLOWED_MESSAGE_ORIGINS:
            streamlit.web.server.routes._DEFAULT_ALLOWED_MESSAGE_ORIGINS.append(url)
    else:
        try:
            allowed_origins = list(st._config.get_option("client.allowedOrigins"))
        except RuntimeError:
            allowed_origins = []

        if url not in allowed_origins:
            allowed_origins.append(url)

        st._config.set_option("client.allowedOrigins", allowed_origins)

add_trusted_url("http://localhost")


NAV_TOP_UNDER_STYLE = f"""
div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"] {{
    height: 3.75rem;
}}
div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"],
iframe[title="{_component_func.name}"] {{
    outline: 1px solid #c3c3c326;
    border-radius: 5px;
    width: 100%;
}}
div:has(> iframe[title="{_component_func.name}"]) {{
    position: sticky;
    opacity: 1 !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0;
    margin-top: calc(-1 * {GAP_BETWEEN_COMPS}rem);
}}
"""

UNDER_NAV_STYLE = f"""
    .reportview-container .sidebar-content {{
        padding-top: 0rem;
    }}
    .reportview-container .main .block-container {{
        padding-top: 0rem;
        padding-right: 4rem;
        padding-left: 4rem;
        padding-bottom: 4rem;
    }}
    .stApp > header {{
        border-bottom: 1px solid #c3c3c326;
    }}
    div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"],
    iframe[title="{_component_func.name}"] {{
        position: relative;
        z-index: 1000;
        top: 0;
        background-color: var(--background-color);
        /* box-shadow: none !important; */
    }}
    div:has(> iframe[title="{_component_func.name}"]) {{
        z-index: 1000;
    }}
    @media (min-width: 576px) {{
        div:has(> iframe[title="{_component_func.name}"]) {{
            width: 100%;
        }}
    }}
    @media (max-width: 575.98px) {{
        div:has(> iframe[title="{_component_func.name}"]) {{
            width: 100%;
        }}
    }}
    @media (min-width: 768px) {{
        div:has(> iframe[title="{_component_func.name}"]) {{
            width: 100%;
        }}
    }}
"""

UNDER_NAV_STICKY_STYLE = f"""
    div:has(> iframe[title="{_component_func.name}"]) {{
        top: calc({HEADER_HEIGHT}rem + 1rem);
    }}
"""

UNDER_NAV_FIXED_STYLE = f"""
    div:has(> iframe[title="{_component_func.name}"]) {{
        top: calc({HEADER_HEIGHT}rem - 5px);
    }}
"""

NAV_TOP_STYLE = f"""
    #header {{
        background: transparent !important;
    }}
    div:has(> iframe[title="{_component_func.name}"]) {{
        top: {TOP_LINE_HEIGHT}rem;
        z-index: 999990;
        padding: 0;
    }}
    div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"],
    iframe[title="{_component_func.name}"] {{
        position: relative;
        top: {TOP_LINE_HEIGHT}rem;
        border-top-right-radius: 0;
        border-top-left-radius: 0;
    }}
    [data-testid="{COLLAPSE_CONTROLL_CLASS}"] {{
        border-right: solid 1px #c3c3c380;
    }}
    [data-testid="{COLLAPSE_CONTROLL_CLASS}"]:has(> [data-testid="stLogoSpacer"]) {{
        flex-direction: row !important;
    }}
    div:has(> iframe[title="{_component_func.name}"]) + div {{
        margin-top: 2rem;
    }}
    
    /* AJUSTE DEL ANCHO */
    @media (min-width: 576px) {{
        div:has(> iframe[title="{_component_func.name}"]) {{
            width: calc(100% - {MARGIN_SIDE_NAVBAR}rem + {SCROLLBAR_WIDTH}px);
        }}
        [data-layout="narrow"] div:has(> iframe[title="{_component_func.name}"]) {{
            width: calc(100% - {MARGIN_SIDE_NAVBAR}rem + {SCROLLBAR_WIDTH}px - 2 * {MARGIN_SIDE_NARROW_DIFF}rem);
            left: calc({TOP_SIDE_ELEMENTS_MARGIN}rem + {TOP_SIDE_ELEMENTS_WIDTH}rem);
        }}
        [data-layout="narrow"]:has(> [data-testid="stSidebar"][aria-expanded="true"]) div:has(> iframe[title="{_component_func.name}"]) {{
            left: 0;
        }}
    }}
    @media(max-width: 575.98px) {{
        div:has(> iframe[title="{_component_func.name}"]) {{
            width: calc(100% - 2*({TOP_SIDE_ELEMENTS_WIDTH}rem + {MARGIN_SIDE_NAVBAR}rem));
            left: calc({TOP_SIDE_ELEMENTS_MARGIN}rem + {TOP_SIDE_ELEMENTS_WIDTH}rem + {MARGIN_SIDE_NAVBAR}rem);
        }}
        [data-layout="narrow"] div:has(> iframe[title="{_component_func.name}"]) {{
            width: calc(100% - 2*({TOP_SIDE_ELEMENTS_WIDTH}rem + {MARGIN_SIDE_NAVBAR}rem - {MARGIN_SIDE_NARROW_DIFF}rem));
            left: calc({TOP_SIDE_ELEMENTS_MARGIN}rem + {TOP_SIDE_ELEMENTS_WIDTH}rem + {MARGIN_SIDE_NAVBAR}rem);
        }}
        [data-layout="wide"]:not(:has(> [data-testid="{COLLAPSE_CONTROLL_CLASS}"])) div:has(> iframe[title="{_component_func.name}"]) {{
            width: calc(100% - {TOP_SIDE_ELEMENTS_WIDTH}rem);
            left: 0;
        }}
        [data-layout="narrow"]:not(:has(> [data-testid="{COLLAPSE_CONTROLL_CLASS}"])) div:has(> iframe[title="{_component_func.name}"]) {{
            width: 100%;
            margin-left: calc(-1*({MARGIN_SIDE_NARROW_DIFF}rem));
            left: 0;
        }}
    }}
"""

NAV_TOP_FIXED_STYLE = f"""
"""

NAV_TOP_STICKY_STYLE = f"""
"""

VERTICAL_ST_STYLE = f"""
    header {{
        position: static;
    }}
    @media(max-width: 575px) {{
        body:has( [data-testid="{COLLAPSE_CONTROLL_CLASS}"] > [data-testid="stLogo"]) [data-testid="stHeader"] {{
            height: 5.75rem;
        }}
    }}
    [data-testid="{COLLAPSE_CONTROLL_CLASS}"], [data-testid="stToolbar"] {{
        max-width: {TOP_SIDE_ELEMENTS_WIDTH}rem;
        width: {TOP_SIDE_ELEMENTS_WIDTH}rem;
        backdrop-filter: blur(5px);
        max-height: 3rem;
    }}
    [data-testid="stToolbar"] {{
        display: flex;
        flex-direction: column-reverse;
        flex-wrap: nowrap;
        align-items: flex-end;
        border-left: solid 1px #c3c3c380;
        justify-content: flex-end;
        overflow: visible;
        
        /* AJUSTE DEL LATERAL */
        right: calc({TOP_SIDE_ELEMENTS_MARGIN}rem + {SCROLLBAR_WIDTH}px);
    }}
    [data-testid="{COLLAPSE_CONTROLL_CLASS}"] {{
        flex-direction: column !important;
        justify-content: flex-start;
        
        /* AJUSTE DEL LATERAL */
        left: {TOP_SIDE_ELEMENTS_MARGIN}rem;
    }}
    [data-testid="{COLLAPSE_CONTROLL_CLASS}"]:has([data-testid="stLogoSpacer"]) {{
        flex-direction: column-reverse !important;
    }}
    [data-testid="{COLLAPSE_CONTROLL_CLASS}"] [data-testid="stLogoSpacer"] {{
        display: none;
    }}
    [data-testid="stStatusWidget"] {{
        position: relative;
        right: 0;
        top: 100%;
        margin-top: 1rem;
        backdrop-filter: blur(5px);
        background: radial-gradient(transparent, #dcdcdc2e);
        padding: 0.5em;
        border: 1px solid #dcdcdc2e;
        border-radius: 5px;
    }}
    
    [data-testid="stToolbar"] > [data-testid="stToolbarActions"] {{
        display: flex;
        -webkit-box-align: center;
        align-items: flex-end;
        flex-direction: column;
        flex-wrap: nowrap;
    }}
"""

STICKY_NAV_STYLE = f"""
    div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"],
    iframe[title="{_component_func.name}"] {{
        box-shadow: 0 0px 10px 5px #00000012;
        border-radius: 5px;
    }}
"""

FIXED_NAV_STYLE = f"""
.stMainBlockContainer {{
    padding-top: 3rem;
}}
div:has(> iframe[title="{_component_func.name}"]) {{
    margin-bottom: 1rem;
}}
div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"],
iframe[title="{_component_func.name}"] {{
    border-top-right-radius: 0;
    border-top-left-radius: 0;
}}
"""

HIDE_ST_STYLE = """
    div[data-testid="stToolbar"] {
        display: none;
        position: none;
    }
    
    div[data-testid="stDecoration"] {
        display: none;
        position: none;
    }
    
    div[data-testid="stStatusWidget"] {
        display: none;
        position: none;
    }
    
    #MainMenu {
        display: none;
    }
    header {
        display: none;
    }
"""

SIDE_NAV_STYLE = f"""
/* Inject COI */
{APP_VIEWER_SELECTOR}, [data-testid="{COLLAPSE_CONTROLL_CLASS}"] {{
    margin-left: 4rem;
    /* transition: margin-left 0.5s ease; */
}}
div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"] {{
    height: 100vh !important;
}}
div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"], iframe[title="{_component_func.name}"] {{
    outline: 1px solid #c3c3c326;
    border-radius: 5px;
    width: 100%;
    height: 100vh !important;
    box-shadow: 5px 0 10px -5px #00000012;
}}
div:has(> iframe[title="{_component_func.name}"]) {{
    position: sticky;
    opacity: 1 !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0;
    margin-top: calc(-1 * {GAP_BETWEEN_COMPS}rem);
}}
div:has(> iframe[title="{_component_func.name}"]) {{
    position: fixed;
    height: 100vh;
    top: 0;
    margin: 0;
    margin-top: 0.125rem;
    left: 0;
    width: 4rem;
    z-index: 999999;
}}
body.nav-open {APP_VIEWER_SELECTOR},
body.nav-open [data-testid="{COLLAPSE_CONTROLL_CLASS}"] {{
    margin-left: 10rem;
}}
body.nav-open div:has(> iframe[title="{_component_func.name}"]) {{
    width: 10rem;
}}
"""

HIDE_SKELETON_STYLE = f"""
div:has(> iframe[title="{_component_func.name}"]) [data-testid="stSkeleton"],
div:has(> iframe[title="{_component_func.name}"]) .stSkeleton {{
    display: none;
}}
"""

# TODO: Hay que poner margenes en el iframe para que no ocupe el 100% de ancho si es menor la pantalla a 575

MATERIAL_ICON_HOME = ":material/home:"
MATERIAL_ICON_LOGIN = ":material/login:"
MATERIAL_ICON_LOGOUT = ":material/logout:"
MATERIAL_ICON_SETTINGS = ":material/settings:"
MATERIAL_ICON_USER_CIRCLE = ":material/account_circle:"

DEFAULT_CUSTOM_THEMES = [
    {
        "name": "dark",
        "icon": "brightness_2",
        "themeInfo": {
            "base": 1,
            "primaryColor": "#079E5A",
            "backgroundColor": "#423E2E",
            "secondaryBackgroundColor": "#2D3419", 
            "textColor": "#D7FF94",
            "font": 2,
            # Nuevos parámetros
            "widgetBackgroundColor": "#625625",
            "widgetBorderColor": "#079E5A",
            "skeletonBackgroundColor": "#545B3C",
            "bodyFont": '"Victor Mono Italic", Source Sans Pro, sans-serif',
            "codeFont": '"Victor Mono", Source Code Pro, monospace',
            "fontFaces": [
                {
                    "family": "Inter",
                    "url": "https://rsms.me/inter/font-files/Inter-Regular.woff2?v=3.19",
                    "weight": 400
                },
                # Victor Mono Regular (400)
                {
                    "family": "Victor Mono",
                    "url": "https://rubjo.github.io/victor-mono/fonts/VictorMono-Regular.80e21ec6.woff",
                    "weight": 400
                },
                # Victor Mono Italic (400)
                {
                    "family": "Victor Mono Italic", 
                    "url": "https://rubjo.github.io/victor-mono/fonts/VictorMono-Italic.ab9b5a67.woff",
                    "weight": 400,
                }
            ],
            "radii": {
                "checkboxRadius": 3,
                "baseWidgetRadius": 6
            },
            "fontSizes": {
                "tinyFontSize": 10,
                "smallFontSize": 12,
                "baseFontSize": 14
            }
        }
    },
    {
        "name": "light",
        "icon": "wb_sunny",
        "themeInfo": {
            "base": 0,
            "primaryColor": "#00BD00",
            "backgroundColor": "#FDFEFE",
            "secondaryBackgroundColor": "#D2ECCD",
            "textColor": "#050505",
            "font": 0,
            # Nuevos parámetros
            "widgetBackgroundColor": "#FFFFFF",
            "widgetBorderColor": "#D3DAE8",
            "skeletonBackgroundColor": "#CCDDEE",
            "bodyFont": "Inter, Source Sans Pro, sans-serif",
            "codeFont": "Apercu Mono, Source Code Pro, monospace",
            "fontFaces": [
                {
                    "family": "Inter",
                    "url": "https://rsms.me/inter/font-files/Inter-Regular.woff2?v=3.19",
                    "weight": 400
                }
            ],
            "radii": {
                "checkboxRadius": 3,
                "baseWidgetRadius": 6
            },
            "fontSizes": {
                "tinyFontSize": 10,
                "smallFontSize": 12,
                "baseFontSize": 14
            }
        }
    }
]

DEFAULT_THEMES = [
    {
        "name": "light",
        "icon": "wb_sunny",
        "themeInfo": {
            "base": 0
        }
    },
    {
        "name": "dark",
        "icon": "brightness_2",
        "themeInfo": {
            "base": 1
        }
    }
]

def build_menu_from_st_pages(
    *pages: StreamlitPage | dict,
    home_page: StreamlitPage | None = None,
    login_page: StreamlitPage | None = None, logout_page: StreamlitPage | None = None,
    account_page: StreamlitPage | None = None,
    settings_page: StreamlitPage | None = None
) -> tuple[list[dict], dict, dict, dict[str, StreamlitPage]]:
    if login_page and not logout_page:
        raise ValueError("You must provide a logout page if you provide a login page")

    menu = []
    page_map = {}
    home_definition = {}
    account_login_definition = {}
    for page in pages:
        if isinstance(page, dict):
            section = page["name"]
            sub_pages = page["subpages"]
            icon = page.get("icon", None)
            ttip = page.get("ttip", section)
            submenu, sub_home_def, _, sub_app_map = build_menu_from_st_pages(*sub_pages)
            menu.append({
                'id': section.lower().replace(" ", "_"),
                'label': section,
                'submenu': submenu,
                'icon': icon,
                'ttip': ttip
            })
            page_map.update(sub_app_map)
            # home_definition = sub_home_def

        elif isinstance(page, StreamlitPage):
            page_id = page._script_hash
            menu.append({
                'label': page.title, 'id': page_id,
                'icon': page.icon, 'ttip': page.title, 'style': {},
                'url': page._url_path,
                'is_page': True
            })
            page_map[page_id] = page
        else:
            raise ValueError(f"Invalid page type: {type(page)}")

    if home_page:
        home_definition = {
            'id': home_page._script_hash,
            'label': home_page.title or "Home",
            'icon': home_page.icon or MATERIAL_ICON_HOME,
            'ttip': home_page.title or "Home",
            'url': home_page._url_path
        }
        page_map[home_page._script_hash] = home_page

    if login_page:
        page_map[login_page._script_hash] = login_page

    if settings_page or account_page or logout_page:
        account_login_definition = {
            'id': "account_menu",
            'label': "Account",
            'icon': MATERIAL_ICON_USER_CIRCLE,
            'ttip': "Account", 'style': {},
            'submenu': []
        }
        if account_page:
            account_login_definition['submenu'].append(
                {
                    'id': account_page._script_hash,
                    'label': account_page.title or "Profile",
                    'icon': account_page.icon or MATERIAL_ICON_USER_CIRCLE,
                    'ttip': account_page.title or "Profile",
                    'url': account_page._url_path
                },
            )
            page_map[account_page._script_hash] = account_page

        if settings_page:
            account_login_definition['submenu'].append(
                {
                    'id': settings_page._script_hash,
                    'label': settings_page.title or "Settings",
                    'icon': settings_page.icon or MATERIAL_ICON_SETTINGS,
                    'ttip': settings_page.title or "Settings",
                    'url': settings_page._url_path
                }
            )
            page_map[settings_page._script_hash] = settings_page

        if logout_page:
            account_login_definition['submenu'].append(
                {
                    'id': logout_page._script_hash,
                    'label': logout_page.title or "Logout",
                    'icon': logout_page.icon or MATERIAL_ICON_LOGOUT,
                    'ttip': logout_page.title or"Logout",
                    'url': logout_page._url_path
                }
            )
            page_map[logout_page._script_hash] = logout_page

    return menu, home_definition, account_login_definition, page_map

def load_st_styles():
    if _RELEASE:
        interface_script_path = build_path / "st-styles.css"
        with open(interface_script_path) as reader:
            content = reader.read()
    else:
        # Load the script from dev_url
        response = requests.get(f"{dev_url}/st-styles.css")
        content = response.text
        pass

    return content


def get_page_id_by_url_path(pages_map: dict[str, StreamlitPage], url: str, prefix_url: str = "") -> str | None:
    # Elimina el prefijo si existe
    url_path = urlparse(url).path
    url_path = url_path.strip("/")
    prefix_url = prefix_url.strip("/")
    if prefix_url and url_path.startswith(prefix_url):
        url_path = url_path[len(prefix_url):]

    for page_id, page in pages_map.items():
        if getattr(page, "_default", False) and url_path == "":
            return page_id
        if getattr(page, "url_path", None) == url_path:
            return page_id
    return None

def st_navbar(
    menu_definition: list[dict], first_select=0, home_definition: dict | None = None, login_definition: dict | None = None,
    override_theme=None, hide_streamlit_markers=True,
    position_mode: NavbarPositionType = 'static', sticky_nav=False,
    force_value=None,
    option_menu=False,
    default_page_selected_id=None,
    override_page_selected_id=None,
    reclick_load=True,
    input_styles: str | None = None,
    themes_data: list[dict]| None = None,
    theme_changer: bool = False,
    hide_skeleton: bool = False,
    collapsible: bool = True,
    prefix_url: str = "",
    # url_navigation: bool = False,
    key="NavBarComponent",
):
    if home_definition is None:
        home_definition = menu_definition.pop(0)

    is_navigation = False
    # se recupera del callstack si se ha llamado desde la anterior funcion desde st_navigation
    inspect_stack = inspect.stack()
    if len(inspect_stack) > 2:
        caller = inspect_stack[1]
        if caller.function == 'st_navigation' and caller.filename == __file__:
            is_navigation = True
    
    if not is_navigation:
        if position_mode != "static":
            raise ValueError("The position_mode parameter can only be 'static' when calling st_navbar directly")
        if sticky_nav:
            # Mostrar un warning de python de que no tendra efecto
            warnings.warn("The sticky_nav parameter will have no effect when calling st_navbar directly")

    if f"{NAVBAR_KEY_PREFIX}_coi_instance" not in st.session_state:
        st.session_state[f"{NAVBAR_KEY_PREFIX}_coi_instance"] = False

    if f"{NAVBAR_KEY_PREFIX}_st_styles_loaded" not in st.session_state:
        st.session_state[f"{NAVBAR_KEY_PREFIX}_st_styles_loaded"] = False

    if is_navigation:
        if themes_data is None and theme_changer:
            themes_data = DEFAULT_THEMES
        elif not theme_changer:
            themes_data = []
    else:
        theme_changer = False

    navbar_view = st.container(key=f"{NAVBAR_KEY_PREFIX}_{key}_container_navbar")
    coi_styles_view = st.container(key=f"{NAVBAR_KEY_PREFIX}_{key}_container_coi_styles")

    # https://github.com/SnpM/streamlit-scroll-navigation
    with coi_styles_view:
        inject_crossorigin_interface()
        # time.sleep(0.1)

    # ctx = get_script_run_ctx(suppress_warning=True)

    # first_select = math.floor(first_select / 10)

    override_theme = override_theme or {
        "menu_background": "var(--background-color)",
        "txc_inactive": "var(--text-color)",
        "txc_active": "var(--text-color)",
        "option_active": "var(--primary-color)",
    }

    home_data = None
    if home_definition and home_definition is not None:
        home_data = home_definition
        home_data['icon'] =home_definition.get('icon', MATERIAL_ICON_HOME)

    login_data = None
    if login_definition and login_definition is not None:
        login_data = login_definition
        login_data['icon'] = login_definition.get('icon', MATERIAL_ICON_USER_CIRCLE)

    if option_menu:
        max_len = 0
        for mitem in menu_definition:
            label_len = len(mitem.get('label', ''))
            if label_len > max_len:
                max_len = label_len

        for i, mitem in enumerate(menu_definition):
            menu_definition[i]['label'] = f"{mitem.get('label', ''):^{max_len + 10}}"

    for i, mitem in enumerate(menu_definition):
        menu_definition[i]['label'] = menu_definition[i].get('label', f'Label_{i}')
        menu_definition[i]['id'] = menu_definition[i].get('id', f"app_{menu_definition[i]['label']}")
        if 'submenu' in menu_definition[i]:
            for _i, _msubitem in enumerate(menu_definition[i]['submenu']):
                menu_definition[i]['submenu'][_i]['label'] = menu_definition[i]['submenu'][_i].get(
                    'label', f'{i}_Label_{_i}'
                )
                menu_definition[i]['submenu'][_i]['id'] = menu_definition[i]['submenu'][_i].get(
                    'id', f"app_{menu_definition[i]['submenu'][_i]['label']}"
                )

    if default_page_selected_id is None:
        items = menu_definition
        if home_definition is not None:
            items = [home_data] + items
        if login_definition is not None:
            items = items + [login_data]
        
        first_select_item = items[first_select] or {}
        default_page_selected_id = first_select_item.get('id', None)
        if first_select_item.get('submenu', []):
            default_page_selected_id = first_select_item['submenu'][0].get('id', None)

    if override_page_selected_id:
        default_page_selected_id = override_page_selected_id

    input_styles = input_styles or ""
    styles = f"\ndiv:has(> .st-key-{NAVBAR_KEY_PREFIX}_{key}_container_coi_styles) {{\nheight: 0;\nposition: absolute;\n}}\n"
    if not st.session_state.get(f"{NAVBAR_KEY_PREFIX}_st_styles_loaded", False):
        styles += load_st_styles()
        if hide_skeleton:
            styles += HIDE_SKELETON_STYLE
        with coi_styles_view:
            st.markdown(f"<style>\n{input_styles}\n{styles}\n<style>", unsafe_allow_html=True)

    # if not st.session_state.get(f"{NAVBAR_KEY_PREFIX}_coi_instance", False):
    # styles = load_st_styles()
    with coi_styles_view:
        instantiate_crossorigin_interface(_component_func.name, key, is_navigation, default_page_selected_id, position_mode, sticky_nav)
        st.session_state[f"{NAVBAR_KEY_PREFIX}_coi_instance"] = True

    with navbar_view:
        component_value = _component_func(
            menu_definition=menu_definition, home=home_data or None, login=login_data or None,
            override_theme=override_theme,
            position_mode=position_mode, is_sticky=sticky_nav,
            default_page_selected_id=default_page_selected_id,
            override_page_selected_id=override_page_selected_id,
            reclick_load=reclick_load,
            styles=styles, custom_styles=input_styles,
            is_navigation=is_navigation,
            themes_data=themes_data,
            theme_changer=theme_changer,
            collapsible=collapsible,
            prefix_url=prefix_url,
            # url_navigation=url_navigation and is_navigation,
            default=default_page_selected_id,
            is_visible=True,
            key=key, fvalue=force_value,
        )
    
    # with coi_scripts_styles.container():
    #     apply_styles(key, f"`{input_styles}`")
        # time.sleep(0.1)

    # print(f"FROM Navbar: {component_value}")

    if component_value is None:
        component_value = default_page_selected_id

    if override_page_selected_id:
        component_value = override_page_selected_id

    # print(f"FROM Navbar FINAL: {component_value}")
    # print()
    return component_value

def st_which_page() -> str:
    return st.session_state[f"{NAVIGATION_KEY_PREFIX}_page_id"]

def st_navigation(
    pages: list[StreamlitPage] | dict[str, list[StreamlitPage]],
    section_info: dict[str, dict[str, str]] | None = None,
    position_mode: NavbarPositionType = 'side', sticky_nav=True,
    login_page: StreamlitPage | None = None,
    logout_page: StreamlitPage | None = None,
    account_page: StreamlitPage | None = None,
    settings_page: StreamlitPage | None = None,
    native_way=False, # url_navigation=False,
    input_styles: str | None = None,
    themes_data: list[dict]| None = None,
    theme_changer: bool = True,
    prefix_url: str = ""
) -> StreamlitPage:
    prev_url_page_id_key = f"{NAVIGATION_KEY_PREFIX}_prev_url_page_id"
    prev_page_id_key = f"{NAVIGATION_KEY_PREFIX}_prev_page_id"
    page_id_key = f"{NAVIGATION_KEY_PREFIX}_page_id"
    force_page_id_key = f"{NAVIGATION_KEY_PREFIX}_force_page_id"
    history_key = f"{NAVIGATION_KEY_PREFIX}_history"

    if prev_url_page_id_key not in st.session_state:
        st.session_state[prev_url_page_id_key] = None

    if prev_page_id_key not in st.session_state:
        st.session_state[prev_page_id_key] = None

    if page_id_key not in st.session_state:
        st.session_state[page_id_key] = None

    if force_page_id_key not in st.session_state:
        st.session_state[force_page_id_key] = None

    if history_key not in st.session_state:
        st.session_state[history_key] = []

    # Build state
    # {
    #     "": [dashboard],
    #     "Account": [account_page, settings_page, logout_page],
    #     "Reports": [bugs, alerts],
    #     "Tools": [search, history],
    # }
    if section_info is None:
        section_info = {}
    

    default_page = None
    if isinstance(pages, dict):
        st_pages = {**pages}
        if account_page or settings_page or logout_page or login_page:
            st_pages["Account"] = []
        if account_page:
            st_pages["Account"].append(account_page)
        if settings_page:
            st_pages["Account"].append(settings_page)
        if logout_page:
            st_pages["Account"].append(logout_page)
        if login_page:
            st_pages["Account"].append(login_page)
        
        organized_pages = []
        for section, sub_pages in pages.items():
            no_default_pages = []
            for sub_page in sub_pages:
                if sub_page._default:
                    if default_page is None:
                        default_page = sub_page
                    else:
                        raise ValueError("You can only have one default page")
                else:
                    no_default_pages.append(sub_page)

            if section == "":
                organized_pages.extend(no_default_pages)
            else:
                organized_pages.append(
                    {
                        "name": section,
                        "subpages": no_default_pages,
                        "icon": section_info.get(section, {}).get("icon", None),
                        "ttip": section_info.get(section, {}).get("ttip", section)
                    }
                )
    else:
        organized_pages = []
        for page in pages:
            if page._default:
                if default_page is None:
                    default_page = page
                else:
                    raise ValueError("You can only have one default page")
            else:
                organized_pages.append(page)
        st_pages = {
            "": [*pages]
        }
        if account_page:
            st_pages[""].append(account_page)
        if settings_page:
            st_pages[""].append(settings_page)
        if logout_page:
            st_pages[""].append(logout_page)
        if login_page:
            st_pages[""].append(login_page)

    if default_page is None:
        raise ValueError("You must provide a default page")

    menu_pages, home_definition, menu_account_pages, pages_map = build_menu_from_st_pages(
        *organized_pages,
        home_page=default_page,  # Default page is the home page
        login_page=login_page, account_page=account_page, settings_page=settings_page,
        logout_page=logout_page,
    )

    st.session_state[f"{NAVIGATION_KEY_PREFIX}_menu_pages"] = menu_pages
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_menu_account_pages"] = menu_account_pages
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_default_page_id"] = default_page._script_hash

    logout_page_id, login_page_id = None, None
    if login_page:
        login_page_id = login_page._script_hash
        st.session_state[f"{NAVIGATION_KEY_PREFIX}_login_page_id"] = login_page_id

    if logout_page:
        logout_page_id = logout_page._script_hash
        st.session_state[f"{NAVIGATION_KEY_PREFIX}_logout_page_id"] = logout_page_id

    if account_page:
        account_page_id = account_page._script_hash
        st.session_state[f"{NAVIGATION_KEY_PREFIX}_account_page_id"] = account_page_id

    if settings_page:
        settings_page_id = settings_page._script_hash
        st.session_state[f"{NAVIGATION_KEY_PREFIX}_settings_page_id"] = settings_page_id


    st.session_state[f"{NAVIGATION_KEY_PREFIX}_page_map"] = pages_map


    if st.session_state[page_id_key] is None:
        st.session_state[page_id_key] = st.session_state[f"{NAVIGATION_KEY_PREFIX}_default_page_id"]

    next_page_id = st_navbar(
        menu_definition=menu_pages,  # if st.session_state.logged_in else [],
        home_definition=home_definition,
        login_definition=menu_account_pages,
        hide_streamlit_markers=False,
        default_page_selected_id=st.session_state[page_id_key] or st.session_state[f"{NAVIGATION_KEY_PREFIX}_default_page_id"],
        override_page_selected_id=st.session_state[force_page_id_key],
        position_mode=position_mode,
        sticky_nav=sticky_nav,
        input_styles=input_styles,
        themes_data=themes_data,
        theme_changer=theme_changer,
        prefix_url=prefix_url,
        # url_navigation=native_way,  # and url_navigation,
        key=NAVIGATION_COMPONENT_KEY,
        hide_skeleton=True,
    )
    st.session_state[force_page_id_key] = None
    prev_page_id = st.session_state[page_id_key]
    st.session_state[page_id_key] = next_page_id  # Added to fix login/logout issue
    # print("CUSTOM COMPONENT", pages_map[next_page_id].title)
    if native_way:
        # Si la url es el path igual al que devuelve el `next_page_id` quiere decir que la navegacion es por url
        # En este punto el navigation de streamlit siempre devolvera la pagina actual
        #  ya que no se usara su navegacion frontal para seleccionar una pagina
        # if url_navigation:
        #     url_page_id = get_page_id_by_url_path(
        #         pages_map, st.context.url, prefix_url=prefix_url
        #     )
        #     # print("URL PAGE", pages_map[url_page_id].title)
        #     if url_page_id != st.session_state[f"{NAVIGATION_KEY_PREFIX}_prev_url_page_id"]:
        #         # Navegacion por url
        #         # Give enough time to the custom component to update
        #         time.sleep(0.1)
        #         st.session_state[f"{NAVIGATION_KEY_PREFIX}_prev_url_page_id"] = url_page_id
        #         next_page_id = url_page_id

        page = st.navigation(
            st_pages,
            position="hidden"
        )
        # print("ST PAGE", page.title)
        prev_page_id = page._script_hash
    else:
        page = pages_map.get(next_page_id, default_page)

    # print("PAGE", pages_map[next_page_id].title)

    # Solo si se cambia de pagina
    if prev_page_id != next_page_id:
        st.session_state[page_id_key] = next_page_id
        if prev_page_id not in [logout_page_id, login_page_id]:
            st.session_state[prev_page_id_key] = prev_page_id
        st_switch_page(next_page_id, native_way=native_way)

    page._can_be_called = True
    add_page_to_history(page._script_hash)
    return page

def add_page_to_history(page_id: str):
    history_key = f"{NAVIGATION_KEY_PREFIX}_history"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    if len(st.session_state[history_key]) > 0:
        last_page_id, runs = st.session_state[history_key][-1].split("::")
        if page_id == last_page_id:
            st.session_state[history_key][-1] = f"{page_id}::{int(runs) + 1}"
            return

    st.session_state[history_key].append(f"{page_id}::1")

def has_changed_page() -> bool:
    history = st.session_state.get(f"{NAVIGATION_KEY_PREFIX}_history", [])
    if not history or len(history) < 2:
        return False

    # print("HISTORY", history[-2:])
    # Verifica si la última página se ejecutó 2 o menos veces y es diferente de la anterior,
    # o si hay una página antes que es diferente
    try:
        actual_page_id, last_runs = history[-1].split("::")
        prev_page_id, _ = history[-2].split("::")
        return actual_page_id != prev_page_id and int(last_runs) <= 2
    except Exception:
        return False

def set_default_page(page_id: str):
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_default_page_id"] = page_id

def init_navigation_transition(prev_page_id: str, page_id: str):
    prev_page_key = f"{NAVIGATION_KEY_PREFIX}_prev_page_id"
    page_key = f"{NAVIGATION_KEY_PREFIX}_page_id"
    if prev_page_key not in st.session_state:
        st.session_state[prev_page_key] = prev_page_id
    if page_key not in st.session_state:
        st.session_state[page_key] = page_id

def set_navigation_transition(prev_page_id: str, page_id: str):
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_prev_page_id"] = prev_page_id
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_page_id"] = page_id

def set_force_next_page(page_id: str):
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_force_page_id"] = page_id

def get_navigation_transition() -> tuple[str, str]:
    return (
        st.session_state[f"{NAVIGATION_KEY_PREFIX}_prev_page_id"],
        st.session_state[f"{NAVIGATION_KEY_PREFIX}_page_id"],
    )

def st_switch_home(native_way: bool = False):
    st_switch_page(st.session_state[f"{NAVIGATION_KEY_PREFIX}_default_page_id"], native_way=native_way)

def st_switch_page(page_id: str, native_way: bool = False):
    pages = st.session_state[f"{NAVIGATION_KEY_PREFIX}_page_map"]
    page = pages.get(page_id, None)
    if page is None:
        raise ValueError(f"Page with id {page_id} not found")

    # add_page_to_history(page_id)
    st.session_state[f"{NAVIGATION_KEY_PREFIX}_force_page_id"] = page_id
    if native_way:
        st.switch_page(page, query_params=dict(st.query_params))
    else:
        st.rerun()
        # ctx = get_script_run_ctx()
        # if ctx is not None:
        #     if page_id != ctx.page_script_hash:
        #         ctx.pages_manager.set_current_page_script_hash(page_id)
        #         rerun_data = RerunData(
        #             query_string=ctx.query_string,
        #             page_script_hash=page_id,
        #         )
        #         raise RerunException(rerun_data)

def get_pages_info() -> tuple[dict[str, str], str, list[dict], list[dict], str | None, str | None, str | None, str | None]:
    pages = st.session_state[f"{NAVIGATION_KEY_PREFIX}_page_map"]

    default_page = next(filter(lambda p: p._default, pages.values()), None)
    if default_page is None:
        raise ValueError("You must provide a default page")

    default_page_id = default_page._script_hash
    
    login_page_id = st.session_state.get(f"{NAVIGATION_KEY_PREFIX}_login_page_id", None)
    logout_page_id = st.session_state.get(f"{NAVIGATION_KEY_PREFIX}_logout_page_id", None)
    account_page_id = st.session_state.get(f"{NAVIGATION_KEY_PREFIX}_account_page_id", None)
    settings_page_id = st.session_state.get(f"{NAVIGATION_KEY_PREFIX}_settings_page_id", None)

    menu_pages = st.session_state[f"{NAVIGATION_KEY_PREFIX}_menu_pages"]
    menu_account_pages = st.session_state[f"{NAVIGATION_KEY_PREFIX}_menu_account_pages"]

    return pages, default_page_id, menu_pages, menu_account_pages, login_page_id, logout_page_id, account_page_id, settings_page_id
