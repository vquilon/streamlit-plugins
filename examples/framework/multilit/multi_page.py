import streamlit as st

from streamlit_plugins.components.navbar import st_navbar
from streamlit_plugins.framework.multilit import Multilit, NavbarPositionType

USER = "admin"
PASSWORD = "admin"
LOGGING_SESSION_KEY = "logged_in"

if LOGGING_SESSION_KEY not in st.session_state:
    is_logged = st.context.cookies.get("user") == USER
    st.session_state[LOGGING_SESSION_KEY] = is_logged

st.set_page_config(layout="wide")


def sidebar():
    with st.sidebar:
        st.write("Logged in:", st.session_state[LOGGING_SESSION_KEY])

        st.divider()

        nav_position_modes: list[NavbarPositionType] = ["top", "under", "side", "hidden", "static"]
        position_mode = st.radio(
            "Navbar position mode",
            nav_position_modes,
            index=nav_position_modes.index(st.session_state.get("position_mode", "top")),
        )
        sticky_nav = st.checkbox(
            "Sticky navbar", value=st.session_state.get("sticky_nav", True)
        )
        within_fragment = st.checkbox(
            "Use within fragment", value=st.session_state.get("within_fragment", False)
        )
        native_way = st.checkbox(
            "Use native way", value=st.session_state.get("native_way", True)
        )
        use_loader = st.checkbox(
            "Use loader", value=st.session_state.get("use_loader", False)
        )

        st.session_state["position_mode"] = position_mode
        st.session_state["sticky_nav"] = sticky_nav
        st.session_state["within_fragment"] = within_fragment
        st.session_state["native_way"] = native_way
        st.session_state["use_loader"] = use_loader

    return native_way, sticky_nav, position_mode, within_fragment, use_loader

def run():
    (
        native_way,
        sticky_nav,
        position_mode,
        within_fragment,
        use_loader
    ) = sidebar()

    multilit = Multilit(
        title="Demo", layout='wide', favicon="📚",
        use_st_navigation=native_way,
        navbar_sticky=sticky_nav, navbar_mode=position_mode,
        sidebar_state='auto',
        clear_cross_page_sessions=False,
        hide_streamlit_markers=False,
        session_params=None,
        use_loader=use_loader, within_fragment=within_fragment,
        login_info_session_key=LOGGING_SESSION_KEY,
        navigation_theme_changer=True,
    )

    @multilit.page(title="Log in", icon=":material/login:", page_type="login")
    def login():
        _, col, _ = st.columns([2, 6, 2])
        with col:
            with st.form(key="login_form"):
                user = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Submit")

            with st.expander("Psst! Here's the login info"):
                st.write(f"Username and Password is:")
                st.markdown(f"""
                ```bash
                {USER}
                ```
                """)

        if submitted:
            if user == USER and password == PASSWORD:
                st.session_state[LOGGING_SESSION_KEY] = True
                st.rerun()
            else:
                st.toast("Invalid username or password", icon="❌")

    @multilit.page(title="Account", icon=":material/account_circle:", page_type="account")
    def account():
        st.write("Account page")
        st.caption("This is a protected page. Only logged in users can view this.")

    @multilit.page(title="Settings", icon=":material/settings:", page_type="settings", with_loader=False)
    def settings():
        menu_definition = [
            {
                "id": "account",
                "label": "Account",
                "icon": "material/account_circle",
                "ttip": "Account",
            },
            {
                "id": "preferences",
                "label": "Preferences",
                "icon": "material/settings",
                "ttip": "Preferences",
            }
        ]
        # default_definition = menu_definition.pop(0)
        selected_tab = st_navbar(
            menu_definition,
            sticky_nav=False,
            theme_changer=False,
            # home_definition=default_definition
        )

        if selected_tab == "account":
            st.subheader("Account settings")
            st.text_input("Email", value="", placeholder="Email")
            st.text_input("Username", value="", placeholder="Username")
            st.text_input("Full name", value="", placeholder="Full name")
        elif selected_tab == "preferences":
            st.subheader("Preferences")
            st.checkbox("Enable notifications", value=True)
            st.checkbox("Dark mode", value=False)

    @multilit.logout_callback
    def logout():
        st.session_state[LOGGING_SESSION_KEY] = False

    st.logo(
        image="https://streamlit.io/images/brand/streamlit-logo-primary-colormark-darktext.svg",
        icon_image="https://streamlit.io/images/brand/streamlit-mark-color.png"
    )

    # dashboard = st.Page("dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True)
    # login_page = st.Page(login, title="Log in", icon=":material/login:")
    # account_page = st.Page(account, title="Account", icon=":material/account_circle:")
    # settings_page = st.Page(settings, title="Settings", icon=":material/settings:")
    bugs = st.Page("reports/bugs.py", title="Bug reports", icon=":material/bug_report:")
    alerts = st.Page("reports/alerts.py", title="System alerts", icon=":material/notification_important:")
    search = st.Page("tools/search.py", title="Search", icon=":material/search:")
    history = st.Page("tools/history.py", title="History", icon=":material/history:")

    # logout_page = st.Page(logout, title="Log out", icon=":material/logout:")

    @multilit.page(title="Single")
    def no_sectioned_page():
        st.header('Single')
        sel_page = st_navbar(
            menu_definition=[
                {
                    'id': "Example 1".lower().replace(" ", "_"),
                    'label': "Example 1",
                    # 'submenu': submenu,
                    'icon': ":material/home:",
                    'ttip': "Example 1",
                },
                {
                    'id': "Example 2".lower().replace(" ", "_"),
                    'label': "Example 2",
                    # 'submenu': submenu,
                    'icon': ":material/settings:",
                    'ttip': "Example 2",
                },
            ],
            default_page_selected_id="Example 1".lower().replace(" ", "_"),
            theme_changer=False,
            position_mode="static",
        )
        multilit.change_page_button(bugs, 'Bugs')
        multilit.change_page_button(alerts, 'Alerts')

    multilit.add_page(page=multilit.default_home_dashboard(), page_type="home")
    with multilit.new_section(title="Reports"):
        multilit.add_page(bugs)
        multilit.add_page(alerts, with_loader=False)

    with multilit.new_section(title="Tools"):
        multilit.add_page(search)
        multilit.add_page(history)

    multilit.run()


if __name__ == '__main__':
    try:
        import sys

        if "_pydevd_frame_eval.pydevd_frame_eval_cython_wrapper" not in sys.modules:
            import _pydevd_frame_eval.pydevd_frame_eval_cython_wrapper
    except ImportError:
        pass

    run()
