import logging
import traceback
from typing import Any, Callable, Dict, Literal, Optional, Tuple

import streamlit
import streamlit as st

try:
    from streamlit.web.server.routes import _DEFAULT_ALLOWED_MESSAGE_ORIGINS
except ImportError as e:
    _DEFAULT_ALLOWED_MESSAGE_ORIGINS = None

from streamlit.commands.page_config import Layout, InitialSideBarState
from streamlit.navigation.page import StreamlitPage
from streamlit.runtime.scriptrunner import RerunException, StopException, get_script_run_ctx

try:
    from streamlit.runtime.scriptrunner.script_requests import ScriptRequestType, RerunData
except ModuleNotFoundError:
    from streamlit.runtime.scriptrunner_utils.script_requests import ScriptRequestType, RerunData

from streamlit_plugins.components.loader import BaseLoader, LoaderType, LoadersLib, DefaultLoader
from streamlit_plugins.components.navbar import (
    DEFAULT_THEMES,
    HEADER_HEIGHT,
    NavbarPositionType,
    init_navigation_transition, get_navigation_transition,
    set_default_page, set_force_next_page, set_navigation_transition,
    st_navigation, st_switch_page, has_changed_page,
    NAVIGATION_COMPONENT_KEY, NAVIGATION_KEY_PREFIX, NAVBAR_KEY_PREFIX
)
from .app_wrapper import STPageWrapper
from .loading_engine import LoadingEngine

logger = logging.getLogger(__name__)

major, minnor, bug = st.__version__.split('.')
major, minnor, bug = int(major), int(minnor), int(bug)
# minnor == 36, 37
DEFAULT_NAVBAR_PARENT_SELECTOR_FRAGMENT = """[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""
DEFAULT_NAVBAR_PARENT_SELECTOR = """[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""
if major == 1:
    if minnor == 36:
        st.fragment = st.experimental_fragment
    if 36 <= minnor <= 37:
        ...
    if minnor == 38:
        DEFAULT_NAVBAR_PARENT_SELECTOR = """[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""
        DEFAULT_NAVBAR_PARENT_SELECTOR_FRAGMENT = """[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""

    if minnor >= 39:
        DEFAULT_NAVBAR_PARENT_SELECTOR = """[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""
        DEFAULT_NAVBAR_PARENT_SELECTOR_FRAGMENT = """[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""

    if minnor >= 43:
        DEFAULT_NAVBAR_PARENT_SELECTOR = f"""[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"].st-key-{NAVIGATION_COMPONENT_KEY} > div > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""
        DEFAULT_NAVBAR_PARENT_SELECTOR_FRAGMENT = f"""[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"].st-key-{NAVIGATION_COMPONENT_KEY} > div > iframe[title="streamlit_plugins.components.navbar.nav_bar"])"""


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


class FNStreamlitPage(StreamlitPage):
    # def __init__(
    #     self,
    #     page: Callable[[], None],
    #     *,
    #     title: str | None = None,
    #     icon: str | None = None,
    #     url_path: str | None = None,
    #     default: bool = False,
    # ):
    #     # Must appear before the return so all pages, even if running in bare Python,
    #     # have a _default property. This way we can always tell which script needs to run.
    #     self._default: bool = default
    #
    #     inferred_name = "Uknown"
    #     inferred_icon = ":material/uknown:"
    #     if hasattr(page, "__name__"):
    #         inferred_name = str(page.__name__)
    #
    #     self._page: Callable[[], None] = page
    #     self._title: str = title or inferred_name.replace("_", " ")
    #     self._icon: str = icon or inferred_icon
    #
    #     if self._title.strip() == "":
    #         raise ValueError(
    #             "The title of the page cannot be empty or consist of underscores/spaces only"
    #         )
    #
    #     self._url_path: str = inferred_name
    #     if url_path is not None:
    #         if url_path.strip() == "" and not default:
    #             raise ValueError(
    #                 "The URL path cannot be an empty string unless the page is the default page."
    #             )
    #
    #         self._url_path = url_path.strip("/")
    #
    #     self._can_be_called: bool = True

    def run(self):
        self._page()


class SectionWithStatement:
    def __init__(self, name, exit_fn):
        self.name = name
        self.exit_fn = exit_fn

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_fn()


NAVIGATION_MULTILIT_KEY = "multilit_navigation_container"
LOADER_MULTILIT_KEY = "multilit_loader_container"


class Multilit:
    """
    Class to create a host application for combining multiple streamlit applications.
    """

    def get_page_id(self, page: StreamlitPage) -> str:
        return page._script_hash

    # def _encode_hyauth(self):
    #     user_access_level, username = self.check_access()
    #     payload = {"exp": datetime.now(timezone.utc) + timedelta(days=1), "userid": username,"user_level":user_access_level}
    #     return jwt.encode(payload, self._multilit_url_hash, algorithm="HS256")

    # def _decode_hyauth(self,token):
    #     return jwt.decode(token, self._multilit_url_hash, algorithms=["HS256"])

    def __init__(
            self,
            title='Multilit Apps',
            nav_container=None,
            layout: Layout = "wide",
            favicon="🤹‍♀️",
            use_st_navigation_navbar=None,
            use_st_navigation=None,
            navbar_theme=None,
            navbar_sticky=True,
            navbar_mode: NavbarPositionType = 'under',
            sidebar_state: InitialSideBarState = 'auto',
            hide_streamlit_markers=False,
            clear_cross_page_sessions=False,
            session_params=None,
            verbose=False,
            within_fragment=False,
            login_info_session_key="logged_in",
            navigation_theme_changer=True,
            allowed_origins=None,
            use_loader=False,
            loader_lib: LoadersLib | Callable[..., Tuple[str, str, str],] | None = None,
            only_loading_between_pages: bool = True,
            loader: Optional[BaseLoader] = None, default_loader_params: Dict[str, Any] = None,
            **kwargs
    ):
        """
        Initializes a Multi-page Streamlit application that allows combining several pages into a single interface, managing navigation, global state, and authentication.

        Parameters
        ----------
        title : str, optional (default 'Multilit Pages')
            Title of the main application (appears in the browser tab).
        nav_container : streamlit.container, optional
            Container where the navigation bar is rendered. If None, a default one is created.
        layout : Layout, optional (default "wide")
            Layout of the main Streamlit page.
        favicon : str, optional (default "🤹‍♀️")
            Emoji or image path for the application favicon.
        use_st_navigation_navbar : bool, optional
            **Deprecated**. Use `use_st_navigation` instead.
        use_st_navigation : bool, optional
            If True, uses Streamlit's native navigation.
        navbar_theme : dict, optional
            Dictionary to customize the navigation bar theme.
        navbar_sticky : bool, optional (default True)
            If True, the navigation bar remains fixed at the top.
        navbar_mode : NavbarPositionType, optional (default 'under')
            Position of the navigation bar: 'top', 'under', 'side', etc.
        sidebar_state : InitialSideBarState, optional (default 'auto')
            Initial state of the Streamlit sidebar.
        hide_streamlit_markers : bool, optional (default False)
            Hides the Streamlit menu and watermark.
        clear_cross_page_sessions : bool, optional (default False)
            If True, clears session state when changing pages.
        session_params : dict, optional
            Dictionary of additional parameters for the global session state.
        verbose : bool, optional (default False)
            If True, shows detailed error messages in the interface.
        within_fragment : bool, optional (default False)
            If True, the navigation bar is rendered within an experimental fragment.
        login_info_session_key : str, optional (default "logged_in")
            Session state key to identify if the user is authenticated.
        navigation_theme_changer : bool, optional (default True)
            Allows changing the navigation theme from the interface.
        allowed_origins : list, optional
            List of allowed origins for messages between components.
        use_loader : bool, optional (default True)
            If True, shows a loader/spinner when changing pages.
        loader_lib : LoadersLib or Callable, optional
            Library or custom function for loaders.
        only_loading_between_pages: bool, optional (default True)
            If True, shows the loader when navigating between pages. If False, show loader on every page run.
        loader : LoaderType, optional
            Custom loader for the application.
        **kwargs : dict
            Other additional parameters.

        The instance manages the shared global state between all pages, navigation, authentication, and visual customization.
        """

        if allowed_origins is None:
            allowed_origins = []

        for origin in allowed_origins:
            add_trusted_url(origin)

        self._active_section = None
        self._active_section_icon = None
        self._verbose = verbose

        self._within_fragment = within_fragment
        if within_fragment:
            logger.warning(
                "The 'within_fragment' parameter is experimental and may not work as expected in all Streamlit versions.\n"
                "The known issues is that the navigation only change to other page if it finish loading the current one."
            )

        self._pages: dict[str, STPageWrapper] = {}
        self.pages_map: dict[str, StreamlitPage] = {}
        self._navbar_pointers = {}
        self._login_page: STPageWrapper | None = None
        self._login_id = 'page_login'
        self._home_page: STPageWrapper | None = None
        self._home_label = ["Home", ":material/home:"]
        self._home_id = 'page_home'
        self._settings_page: STPageWrapper | None = None
        self._settings_label = ["Settings", ":material/settings:"]
        self._settings_id = 'page_settings'
        self._account_page: STPageWrapper | None = None
        self._account_label = ["Account", ":material/account_circle:"]
        self._account_id = 'page_account'
        self._logout_label = ["Logout", ":material/logout:"]
        self._logout_id = 'logic_page_logout'
        self._check_login_callback = self.default_check_login
        self._do_login = self.login_callback(lambda: None)
        self._do_logout = self.logout_callback(lambda: None)

        self._complex_nav: dict[str, dict | StreamlitPage] = dict()
        self._navbar_mode: NavbarPositionType = navbar_mode
        self._navbar_active_index = 0
        # self._allow_url_nav = allow_url_nav
        self._navbar_sticky = navbar_sticky
        self._nav_item_count = 0

        if use_st_navigation_navbar is not None:
            logger.warning(
                "The use_st_navigation_navbar parameter is deprecated, please use use_st_navigation instead.")

            if use_st_navigation is None:
                use_st_navigation = use_st_navigation_navbar
            else:
                logger.warning(
                    "Both use_st_navigation_navbar and use_st_navigation parameters are set, using use_st_navigation value.")

        self._use_st_navigation = use_st_navigation
        self._navigation_theme_changer = navigation_theme_changer
        self._hide_streamlit_markers = hide_streamlit_markers
        self._navbar_theme = navbar_theme or DEFAULT_THEMES

        self._session_attrs = {}

        # self._guest_name = 'guest'
        # self._guest_access = 1
        self._no_access_level = -1

        self._user_session_params = session_params

        if within_fragment:
            self._st_navbar_parent_selector = DEFAULT_NAVBAR_PARENT_SELECTOR_FRAGMENT
        else:
            self._st_navbar_parent_selector = DEFAULT_NAVBAR_PARENT_SELECTOR

        try:
            st.set_page_config(
                page_title=title, page_icon=favicon,
                layout=layout, initial_sidebar_state=sidebar_state
            )
        except Exception as e:
            pass

        self._nav_container = nav_container
        self._page_view = None

        self._user_loader = use_loader
        self._only_loading_between_pages = only_loading_between_pages
        if self._user_loader:
            if loader is None:
                default_loader: DefaultLoader = LoadingEngine.get_default_loader(
                    LOADER_MULTILIT_KEY,
                    loader_params=default_loader_params or {},
                    loader_lib=loader_lib
                )
            else:
                default_loader: BaseLoader = loader

            self._loading_engine = LoadingEngine(default_loader)

        self.cross_session_clear = clear_cross_page_sessions

        if clear_cross_page_sessions:
            preserve_state = False
        else:
            preserve_state = True

        self.login_info_session_key = login_info_session_key
        self._session_attrs = {
            'multilit_transition_state': None,
            'multilit_preserve_state': preserve_state, 'multilit_allow_access': self._no_access_level,
            login_info_session_key: None, 'multilit_access_hash': None, 'multilit_uncaught_error': None
        }

        if isinstance(self._user_session_params, dict):
            self._session_attrs |= self._user_session_params

        for key, item in self._session_attrs.items():
            if not hasattr(st.session_state, key):
                st.session_state[key] = item

    def change_page(self, page: StreamlitPage, scope: Literal["app", "fragment"] = "app"):
        page_id = self.get_page_id(page)
        if page_id not in self._pages and page_id != self._home_id:
            raise ValueError(f"Page id {page_id} not found in the list of pages")

        st_switch_page(page_id, native_way=self._use_st_navigation)

    def change_page_button(self, page: StreamlitPage, label: str):
        if st.button(label):
            self.change_page(page)

    def add_page(
            self,
            page: StreamlitPage, title=None, icon: str | None = None,
            page_type: Literal["normal", "home", "login", "settings", "account"] = "normal",
            access_level: int | None = None,
            with_loader: Optional[bool] = None,
            page_loader: BaseLoader | None = None,
            page_loader_kwargs: dict = None,
    ):
        """
        Adds a new page to this MultiApp.

        Parameters
        ----------
        page : StreamlitPage
            The page instance to add.
        title : str, optional
            The title to display in the navigation menu for this page.
        icon : str, optional
            The icon to use in the navigation menu for this page.
        page_type : Literal["normal", "home", "login", "settings", "account"], default "normal"
            The type of page, which determines its behavior in the MultiApp.
        access_level : int, optional
            The access level required to view this page.
        with_loader : bool, optional
            Whether to use a loading animation when switching to this page.
        page_loader : BaseLoader, optional
            Custom loader to use for this page.
        page_loader_kwargs : dict, optional
            Additional keyword arguments for the page loader.
        """

        title = title or page.title
        # page_id = f"page_{page_id or len(self._pages) + 1}"
        page_id = page._script_hash

        if with_loader is None:
            with_loader = self._user_loader

        if page_loader or self._user_loader:
            page_loader: BaseLoader
            self._loading_engine.register_page_loader(
                page_id, page_loader or self._loading_engine.selected_loader, run_loader_kwargs=page_loader_kwargs
            )

        app_wrapper = STPageWrapper(page, with_loader=with_loader)
        app_wrapper.access_level = access_level
        app_wrapper.id = page_id
        app_wrapper.title = title
        if page_type == "normal":
            # section_id = self._active_section or page_id
            # self._complex_nav[section_id].append(page_id)
            if self._active_section:
                self._complex_nav[self._active_section]["subpages"].append(page)
            else:
                self._complex_nav[page_id] = page

            self._navbar_pointers[page_id] = [title, icon]

        elif page_type == "login":
            self._login_page = app_wrapper
            # self._logout_label = [title or self._logout_label[0], icon or self._logout_label[1]]
            self._login_id = page_id

        elif page_type == "home":
            self._home_page = app_wrapper
            self._home_label = [title or self._home_label[0], icon or self._home_label[1]]
            self._home_id = page_id
            page._default = True
            set_default_page(page_id)
            init_navigation_transition(page_id, page_id)

        elif page_type == "settings":
            self._settings_page = app_wrapper
            self._settings_label = [title or self._settings_label[0], icon or self._settings_label[1]]
            self._settings_id = page_id

        elif page_type == "account":
            self._account_page = app_wrapper
            self._account_label = [title or self._account_label[0], icon or self._account_label[1]]
            self._account_id = page_id

        self._pages[page_id] = app_wrapper

        # Posiblemente esto sobre de aqui
        self._nav_item_count = int(self._login_page is not None) + len(self._pages.keys())
        # app.assign_session(st.session_state, self)

    def page(self, title=None, icon=None,
             page_type: Literal["normal", "home", "login", "settings", "account"] = "normal",
             with_loader: Optional[bool] = None, page_loader: Optional[BaseLoader] = None):
        """
        This is a decorator to quickly add a function as a child app in a style like a Flask route.
        You can do everything you can normally do when adding a class based MultiApp to the parent, except you can not add a login or unsecure app using this method, as
        those types of apps require functions provided from inheriting from MultiAppTemplate.
        Parameters
        ----------
        title: str
            The title of the app. This is the name that will appear on the menu item for this app.
        icon: str
            The icon to use on the navigation button, this will be appended to the title to be used on the navigation control.
        page_type: str, 'normal'
            The type of app, this will determine the behaviour of the app within the MultiApp.
        with_loader: bool, None
            A flag to indicate if to use the loading engine when loading this app.
        page_loader: BaseLoader | None, None
            A custom loader to use when loading this app.
        Returns
        -------
        decorator: callable
            A decorator that will add the function as a child app to this MultiApp.
        """

        def decorator(func):
            app_icon = icon
            page_title = title
            is_default = False
            if page_type == "home":
                page_title = page_title or title
                app_icon = app_icon or ":material/home:"
                is_default = True

            wrapped_app = st.Page(func, title=page_title, icon=app_icon, default=is_default)
            self.add_page(title=page_title, page=wrapped_app, icon=app_icon, page_type=page_type,
                          with_loader=with_loader, page_loader=page_loader)

            return func

        return decorator

    def new_section(self, title, icon=None):
        def _exit_fn():
            self._active_section = None
            self._active_section_icon = None

        section_id = f"sect_{title}"
        self._navbar_pointers[section_id] = [title, icon]
        self._active_section = section_id
        self._active_section_icon = icon

        self._complex_nav[self._active_section] = {
            "name": title, "subpages": [], "icon": icon, "ttip": title
        }

        return SectionWithStatement(title, _exit_fn)

    def _build_run_nav_menu(self) -> StreamlitPage:
        home_page = self._home_page.st_page if self._home_page is not None else None
        login_page = self._login_page.st_page if self._login_page is not None else None
        account_page = self._account_page.st_page if self._account_page is not None else None
        settings_page = self._settings_page.st_page if self._settings_page is not None else None
        logout_page = None
        if self._login_page is not None:
            logout_page = FNStreamlitPage(self._do_logout, title="Logout", icon=":material/logout:")
            self._logout_id = self.get_page_id(logout_page)
            self._pages[self._logout_id] = STPageWrapper(logout_page)

        natives_page_data = self.build_native_pages_data_from(
            home_page,
        )

        with self._nav_container:
            page = self._run_navbar(natives_page_data, login_page, account_page, settings_page, logout_page)

        return page

    def build_native_pages_data_from(self, home_page, login_page=None, account_page=None, settings_page=None,
                                     logout_page=None):
        native_pages_data = {}
        if home_page is not None:
            native_pages_data[""] = [home_page]

        for sect, data in self._complex_nav.items():
            if sect.startswith("sect_"):
                data_section: dict = data
                pages: list[StreamlitPage] = data_section.get("subpages", [])
                native_pages_data[sect[len("sect_"):]] = pages
            else:
                data_page: StreamlitPage = data
                if "" not in native_pages_data:
                    native_pages_data[""] = []
                native_pages_data[""].append(data_page)

        if any([login_page, account_page, settings_page]):
            native_pages_data["Account"] = []
            for page in [account_page, settings_page, logout_page]:
                if page is not None:
                    native_pages_data["Account"].append(page)

        return native_pages_data

    @st.fragment
    def _fragment_navbar(self, natives_page_data, login_page, account_page, settings_page, logout_page,
                         styles: str | None = None):
        new_page_id = self._standalone_navbar(natives_page_data, login_page, account_page, settings_page, logout_page,
                                              styles=styles)

        return new_page_id

    def _standalone_navbar(self, natives_page_data, login_page, account_page, settings_page, logout_page,
                           styles: str | None = None) -> StreamlitPage:
        page = st_navigation(
            natives_page_data,
            section_info={
                "Reports": {"icon": ":material/assessment:"},
                "Tools": {"icon": ":material/extension:"}
            },
            position_mode=self._navbar_mode if self._check_login_callback() else "hidden",
            sticky_nav=self._navbar_sticky,
            login_page=login_page, logout_page=logout_page,
            account_page=account_page,
            settings_page=settings_page,
            native_way=self._use_st_navigation,
            # url_navigation=self._allow_url_nav,
            input_styles=styles,
            themes_data=self._navbar_theme,
            theme_changer=self._navigation_theme_changer
        )

        return page

    def _run_navbar(self, natives_page_data, login_page, account_page, settings_page, logout_page) -> StreamlitPage:
        # TODO: Agregar estilos para cada modo de navbar
        base_styles = f"""
        div:has(> .st-key-{NAVIGATION_MULTILIT_KEY}) {{
            height: 0;
            position: absolute;
        }}
        """
        styles = ""
        if self._st_navbar_parent_selector:
            if self._navbar_mode == "top" and self._navbar_sticky:
                styles = f"""
                {self._st_navbar_parent_selector} {{
                    position: sticky;
                    top: 0;
                    z-index: 999990;
                }}
                """
            if self._navbar_mode == "top" and not self._navbar_sticky:
                styles = f"""
                .stMainBlockContainer {{
                    padding-top: 0rem !important;
                }}
                {self._st_navbar_parent_selector} {{
                    position: sticky;
                    top: 0;
                    z-index: 999990;
                }}
                """
            if self._navbar_mode == "under" and self._navbar_sticky:
                styles = f"""
                {self._st_navbar_parent_selector} {{
                    position: sticky;
                    top: calc({HEADER_HEIGHT}rem + 1rem);
                    z-index: 10;
                }}
                """
            if self._navbar_mode == "under" and not self._navbar_sticky:
                styles = f"""
                .stMainBlockContainer {{
                    padding-top: 1rem !important;
                }}
                {self._st_navbar_parent_selector} {{
                    position: sticky;
                    top: calc({HEADER_HEIGHT}rem - 5px);
                    z-index: 10;
                    margin-bottom: 1rem;
                }}
                """
            if self._navbar_mode == "side":
                styles = f"""
                {self._st_navbar_parent_selector} {{
                    position: absolute;
                    top: 0;
                    z-index: 9999999;
                    /* height: 2rem; */
                }}
                """

        styles = base_styles + styles
        if self._within_fragment:
            page = self._fragment_navbar(natives_page_data, login_page, account_page, settings_page, logout_page,
                                         styles=styles)
        else:
            page = self._standalone_navbar(natives_page_data, login_page, account_page, settings_page, logout_page,
                                           styles=styles)

            # TODO: Send COI message to the component to update properly if willUmounted
            # set_page_id_visual("mainMultilitNavbar", new_app_id)

            # Hack to force a rerun and component update correctly
            # ctx = get_script_run_ctx()
            # if ctx is not None:
            #     page_script_hash = ctx.active_script_hash
            #     rerun_data = RerunData(
            #         query_string=ctx.query_string,
            #         page_script_hash=page_script_hash,
            #     )
            #     raise RerunException(rerun_data)

        return page

    def _raise_base_exception(self, e, app_label):
        if isinstance(e, RerunException):
            raise e

        if isinstance(e, StopException):
            while isinstance(e, StopException):
                if e.__context__ is None:
                    break
                e = e.__context__

        trace_err = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        # trace_err = traceback.format_exc()

        if isinstance(e, StopException):
            raise e

        logger.error(trace_err)

        # TODO: Averiguar como parar un stop y poder enviar el error a la interfaz de streamlit
        run_ctx = get_script_run_ctx()
        if run_ctx is not None:
            script_requests = run_ctx.script_requests
            if script_requests is not None:
                with script_requests._lock:
                    script_requests._state = ScriptRequestType.CONTINUE

        st.session_state["multilit_uncaught_error"] = trace_err

        if self._verbose:
            st.error(
                f'😭 Error triggered from page: **{app_label}**\n\n'
                f'Details:\n'
                f'```{trace_err}```',
                icon="🚨"
            )
        raise e

    def _run_selected(self, page: STPageWrapper, need_trigger_loading=False):
        page_label = page.title
        try:
            if self._verbose and st.session_state["multilit_uncaught_error"]:
                st.error(
                    f'😭 Error triggered from page: **{page_label}**\n\n'
                    f'Details:\n'
                    f'```{st.session_state["multilit_uncaught_error"]}```',
                    icon="🚨"
                )

            if page.has_loading() and need_trigger_loading:
                with self._loading_engine.loading(page.id, label=page_label):
                    with self._page_view:
                        page.run()
            else:
                with self._page_view:
                    page.run()

            st.session_state["multilit_uncaught_error"] = None
        except Exception as e:
            self._raise_base_exception(e, page_label)

    def _clear_session_values(self):
        for key in st.session_state:
            if (
                not key.startswith("multilit_") and
                key != self.login_info_session_key and
                not key.startswith(NAVIGATION_KEY_PREFIX) and
                not key.startswith(NAVBAR_KEY_PREFIX)
            ):
                del st.session_state[key]

    def set_guest(self, guest_name):
        """
        Set the name to be used for guest access.
        Parameters
        -----------
        guest_name: str
            The value to use when allowing guest logins.
        """

        if guest_name is not None:
            self._guest_name = guest_name

    def set_noaccess_level(self, no_access_level: int):
        """
        Set the access level integer value to be used to indicate no access, default is zero.
        Parameters
        -----------
        no_access_level: int
            The value to use to block access, all other values will have some level of access
        """

        if no_access_level is not None:
            self._no_access_level = int(no_access_level)

    def set_access(self, allow_access=0, access_user=''):
        """
        Set the access permission and the assigned username for that access during the current session.
        Parameters
        -----------
        allow_access: int, 0
            Value indicating if access has been granted, can be used to create levels of permission.
        access_user: str, None
            The username the access has been granted to for this session.
        """

        # Set the global access flag
        st.session_state["multilit_allow_access"] = allow_access

        # Also, who are we letting in..
        st.session_state["multilit_current_user"] = access_user

    def check_access(self):
        """
        Check the access permission and the assigned user for the running session.
        Returns
        ---------
        tuple: access_level, username
        """
        username = None

        if hasattr(st.session_state, 'multilit_current_user'):
            username = str(st.session_state["multilit_current_user"])

        return int(st.session_state["multilit_allow_access"]), username

    def enable_guest_access(self, guest_access_level=1, guest_username='guest'):
        """
        This method will auto login a guest user when the page is secured with a login page, this will allow fora guest user to by-pass the login page and gain access to the other apps that the assigned access level will allow.
        ------------
        guest_access_level: int, 1
            Set the access level to assign to an auto logged in guest user.
        guest_username: str, guest
            Set the username to assign to an auto logged in guest user.
        """

        user_access_level, username = self.check_access()
        if user_access_level == 0 and username is None:
            self.set_access(guest_access_level, guest_username)

    def _main(self):
        page = self._build_run_nav_menu()
        page_id = self.get_page_id(page)
        # Verifico la autenticacion (self.login_info_session_key) y la autorizacion (allow_access)
        if not self._check_login_callback() and page_id != self._login_id:
            # Se pasa a la pagina de login
            st.session_state["multilit_current_user"] = None
            st.session_state["multilit_access_hash"] = None
            # No hay acceso, se redirige a login
            st_switch_page(self._login_id, native_way=self._use_st_navigation)

        prev_page_id, actual_page_id = get_navigation_transition()
        if self._check_login_callback() and actual_page_id == self._login_id:
            self._do_login()

        if self._nav_item_count == 0:
            self._default()
        else:
            page_id = self.get_page_id(page)
            if page_id == self._logout_id:
                ctx = get_script_run_ctx()
                # Se evita recargas innecesarias o paradas si esta pendiente cambiar al logout
                if ctx.script_requests._state == ScriptRequestType.CONTINUE:
                    ctx.script_requests._state = ScriptRequestType.CONTINUE

            page_wrapper = self._pages.get(page_id)
            if page_wrapper is None:
                raise ValueError(f"App id {page_id} not found in the list of apps")

            # Llegado a este punto, se ejecuta la pagina seleccionada
            page_changed = has_changed_page()
            if page_changed:
                if self.cross_session_clear and not st.session_state["multilit_preserve_state"]:
                    self._clear_session_values()

            has_loading = (page_changed and self._only_loading_between_pages) or not self._only_loading_between_pages
            self._run_selected(page_wrapper, need_trigger_loading=has_loading)

    def run(self):
        """
        This method is the entry point for the MultiApp, just like a single Streamlit page, you simply setup the additional apps and then call this method to begin.
        """
        if self._nav_container is None:
            self._nav_container = st.container(key=NAVIGATION_MULTILIT_KEY)

        self._page_view = st.container()

        self._main()

    def default_home_dashboard(self):
        def default_home_wrapper():
            app_valids_map = {
                app_id: app
                for app_id, app in self._pages.items()
                if app_id not in [self._login_id, self._logout_id, self._home_id]
            }
            # Se contruye un grid de elementos para cambiar de apps
            col1, col2 = st.columns(2)
            # Calculo el total de aplicaciones y se asignan a cada columna y fila

            total_apps = len(app_valids_map)
            apps_per_col = total_apps // 2
            # Se recorren las aplicaciones y se asignan a cada columna
            for i, (page_id, page) in enumerate(app_valids_map.items()):
                if i < apps_per_col:
                    col = col1
                else:
                    col = col2

                with col:
                    with st.container(border=True):
                        st.markdown(f"### {page.title}")
                        self.change_page_button(page.st_page, page.title)

        return st.Page(default_home_wrapper, title="Dashboard", icon=":material/dashboard:")

    def _default(self):
        st.header('Welcome to Multilit')
        st.write(
            'Thank you for your enthusiasum and looking to run the MultiApp as quickly as possible, for maximum effect, please add a child page by one of the methods below.')

        st.write('Method 1 (easiest)')

        st.code("""
#when we import multilit, we automatically get all of Streamlit
import multilit
multi_app = multilit.MultiApp(title='Simple Multi-Page App')
@multi_app.addapp()
def my_cool_function():
    hy.info('Hello from page 1')
        """
                )

        st.write('Method 2 (more fun)')

        st.code("""
    from multilit import MultiHeadApp
    import streamlit as st
    #create a child page wrapped in a class with all your code inside the run() method.
    class CoolApp(MultiHeadApp):
        def run(self):
            st.info('Hello from cool page 1')
    #when we import multilit, we automatically get all of Streamlit
    import multilit
    multi_app = multilit.MultiApp(title='Simple Multi-Page App')
    multi_app.add_page("My Cool App", icon="📚", app=CoolApp(title="Cool App"))
            """
                )

        st.write(
            'Once we have added atleast one child application, we just run the parent page!')

        st.code("""
    multi_app.run()
            """)

        st.write(
            'For example you get can going super quick with a couple of functions and a call to Multilit App run().')

        st.code("""
        #when we import multilit, we automatically get all of Streamlit
        import multilit
        multi_app = multilit.MultiApp(title='Simple Multi-Page App')
        @app.addapp(is_home=True)
        def my_home():
        hy.info('Hello from Home!')
        @app.addapp()
        def app2():
        hy.info('Hello from app 2')
        @app.addapp(title='The Best', icon="🥰")
        def app3():
        hy.info('Hello from app 3, A.K.A, The Best 🥰')
        #Run the whole lot, we get navbar, state management and app isolation, all with this tiny amount of work.
        app.run()
            """)

    def login_callback(self, func):
        """
        This is a decorate to add a function to be run when a user is first logged in.
        """

        def wrapper(*args, **kwargs):
            prev_page_id, page_id = get_navigation_transition()

            func(*args, **kwargs)

            # Una vez logueado, se redirige a la pagina anterior o a la home
            if prev_page_id is None or prev_page_id == self._login_id:
                prev_page_id = self._home_id

            # Actualizo la informacion de transicion, solo hay 2 estados la anterior y la actual
            #  al hacer el login la actual es la misma que la anterior y la anterior se perdio porque no se tiene
            #  solo ya que no se concibe como anterior la de login
            set_navigation_transition(prev_page_id, prev_page_id)

            st_switch_page(prev_page_id, native_way=self._use_st_navigation)

        self._do_login = wrapper
        return wrapper

    def default_check_login(self) -> Any:
        """
        Check if the user is logged in.

        :return: True if the user is logged in, False otherwise.
        """
        if self._login_page is None:
            # No hay login
            return True

        if self.login_info_session_key in st.session_state:
            return st.session_state[self.login_info_session_key]

        return False

    def logout_callback(self, func):
        """
        This is a decorate to add a function to be run when a user is logged out.
        """

        def logout_wrapper(*args, **kwargs):
            st.session_state[self.login_info_session_key] = None
            st.session_state['multilit_allow_access'] = self._no_access_level

            prev_page_id, actual_page_id = get_navigation_transition()
            set_navigation_transition(prev_page_id, self._login_id)
            func(*args, **kwargs)

            st_switch_page(self._login_id, native_way=self._use_st_navigation)

        self._do_logout = logout_wrapper
        return logout_wrapper
