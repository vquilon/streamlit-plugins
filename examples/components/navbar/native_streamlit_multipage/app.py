import sys

import streamlit as st
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

try:
    if "_pydevd_frame_eval.pydevd_frame_eval_cython_wrapper" not in sys.modules:
        import _pydevd_frame_eval.pydevd_frame_eval_cython_wrapper
except ImportError:
    pass

st.set_page_config(layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = True

USER = "admin"
PASSWORD = "admin"

positions = ["top", "under", "side"]  # "hidden", "static"]

def my_sidebar():
    if "position_mode" not in st.session_state:
        st.session_state["position_mode"] = "side"
    if "sticky_nav" not in st.session_state:
        st.session_state["sticky_nav"] = False
    if "native_way" not in st.session_state:
        st.session_state["native_way"] = True

    with st.sidebar:
        st.write("Logged in:", st.session_state.logged_in)
        position_mode = st.radio(
            "Navbar position mode",
            positions,
            index=positions.index(st.session_state["position_mode"]),
            key="position_mode_input",
            # key="position_mode",
        )
        sticky_nav = st.checkbox(
            "Sticky navbar",
            value=st.session_state["sticky_nav"],
            key="sticky_nav_input"
            # key="sticky_nav"
        )
        native_way = st.checkbox(
            "Use native way",
            value=st.session_state["native_way"],
            # key="native_way"
            key="native_way_input"
        )
        st.session_state["position_mode"] = position_mode
        st.session_state["sticky_nav"] = sticky_nav
        st.session_state["native_way"] = native_way


def my_heading():
    st.title("Streamlit Multi-Page App")
    st.subheader("This is a multi-page app with a native Streamlit navbar.")
    st.markdown("> But only vizualize well with navbar on `top` position")


def login():
    _, col, _ = st.columns([2, 6, 2])
    with col:
        st.title("Login page")
        with st.form(key="login_form"):
            user = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted_user_pas_login = st.form_submit_button("Submit")
        with st.expander("Psst! Here's the login info"):
            st.write(f"Username and Password is:")
            st.code(USER)

        if st.button("Oauth Login (demo)", type="primary"):
            st.login()

    if submitted_user_pas_login:
        if user == USER and password == PASSWORD:
            st.session_state.logged_in = True
            ctx = get_script_run_ctx()
            ctx.user_info['is_logged_in'] = True
            st_switch_home()
        else:
            st.toast("Invalid username or password", icon="❌")


def account():
    st.write("Account page")
    st.caption("This is a protected page. Only logged in users can view this.")


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


def logout():
    st.session_state.logged_in = False
    st.session_state.app_id = None
    st.session_state.active_app_id = None
    st.logout()
    st.rerun()

st.logo(
    image="https://streamlit.io/images/brand/streamlit-logo-primary-colormark-darktext.svg",
    icon_image="https://streamlit.io/images/brand/streamlit-mark-color.png"
)

dashboard = st.Page("dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True, url_path="dashboard")
login_page = st.Page(login, title="Log in", icon=":material/login:", url_path="login")
account_page = st.Page(account, title="Account", icon=":material/account_circle:", url_path="account")
settings_page = st.Page(settings, title="Settings", icon=":material/settings:", url_path="settings")
bugs = st.Page("reports/bugs.py", title="Bug reports", icon=":material/bug_report:", url_path="bugs")
bugs2 = st.Page("reports/bugs.py", title="Bug reports2", icon=":material/bug_report:", url_path="bugs2")
bugs3 = st.Page("reports/bugs.py", title="Bug reports3", icon=":material/bug_report:", url_path="bugs3")
alerts = st.Page("reports/alerts.py", title="System alerts", icon=":material/notification_important:", url_path="alerts")
search = st.Page("tools/search.py", title="Search", icon=":material/search:", url_path="search")
history = st.Page("tools/history.py", title="History", icon=":material/history:", url_path="history")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:", url_path="logout")

# HERE IS THE CHANGE
from streamlit_plugins.components.navbar import NavbarPositionType, st_navigation, st_switch_home, st_navbar, \
    set_force_next_page, st_switch_page

my_sidebar()

position_mode: NavbarPositionType = st.session_state["position_mode"]
sticky_nav = st.session_state["sticky_nav"]
native_way = st.session_state["native_way"]


if st.session_state.logged_in:
    if position_mode == "top":
        my_heading()

page = st_navigation(
    {
        "": [dashboard],
        "Reports": [alerts],
        "Tools": [search, history, bugs, bugs2, bugs3]
    },
    section_info={
        "Reports": {"icon": ":material/assessment:"},
        "Tools": {"icon": ":material/extension:"}
    },
    position_mode=position_mode if st.session_state.logged_in else "hidden", sticky_nav=sticky_nav,
    login_page=login_page, logout_page=logout_page,
    account_page=account_page,
    settings_page=settings_page,
    native_way=native_way,
    # url_navigation=url_navigation
)
print(f"{page.title=}, {native_way=}, {sticky_nav=}, {position_mode=}, query_params={st.query_params}")
print()

if not st.session_state.logged_in and page._script_hash != login_page._script_hash:
    st_switch_page(login_page._script_hash, native_way=True)

page.run()
