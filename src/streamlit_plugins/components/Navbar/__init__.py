import os
import streamlit as st
import math
import streamlit.components.v1 as components

# _RELEASE = os.getenv("RELEASE", "").upper() != "DEV"
_RELEASE = True

if _RELEASE:
    absolute_path = os.path.dirname(os.path.abspath(__file__))
    build_path = os.path.join(absolute_path, "frontend", "build")
    _component_func = components.declare_component("nav_bar", path=build_path)
else:
    _component_func = components.declare_component("nav_bar", url="http://localhost:3000")


PINNED_NAV_STYLE = f"""
                    <style>
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
                        border-bottom: 1px solid #9e9e9e;
                    }}
                    iframe[title="{_component_func.name}"] {{
                        position: fixed;
                        z-index: 1000;
                        box-sizing: content-box;
                        top: calc(2.875rem - 0.5rem);
                        border: 2px solid #ff4b56;
                        border: 1px solid #9e9e9e;
                        border-radius: 5px;
                    }}
                    </style>
                """

STICKY_NAV_STYLE = f"""
                    <style>
                    div[data-stale="false"] > iframe[title="{_component_func.name}"] {{
                        position: fixed;
                        z-index: 99;
                        box-sizing: border-box;
                        top: 0;
                    }}
                    </style>
                """

HIDE_ST_STYLE = """
                    <style>
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

                    </style>
                """

def nav_bar(menu_definition, first_select=0, key="NavBarComponent", home_name=None, login_name=None,
            override_theme=None, sticky_nav=True, force_value=None, use_animation=True,
            hide_streamlit_markers=True, sticky_mode='pinned', option_menu=False):
    first_select = math.floor(first_select / 10)

    if type(home_name) is str:
        home_data = {'id': "app_home", 'label': home_name, 'icon': "fa fa-home", 'ttip': home_name}
    else:
        home_data = home_name
        if home_name is not None:
            if home_name.get('icon', None) is None:
                home_data['icon'] = "fa fa-home"

    if type(login_name) is str:
        login_data = {'id': "app_login", 'label': login_name, 'icon': "fa fa-user-circle", 'ttip': login_name}
    else:
        login_data = login_name
        if login_name is not None:
            if login_name.get('icon', None) is None:
                login_data['icon'] = "fa fa-user-circle"

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
                menu_definition[i]['submenu'][_i]['label'] = menu_definition[i]['submenu'][_i].get('label', f'{i}_Label_{_i}')
                menu_definition[i]['submenu'][_i]['id'] = menu_definition[i]['submenu'][_i].get('id', f"app_{menu_definition[i]['submenu'][_i]['label']}")

    component_value = _component_func(
        menu_definition=menu_definition, first_select=first_select, key=key, home=home_data, fvalue=force_value,
        login=login_data, override_theme=override_theme, use_animation=use_animation
    )

    if sticky_nav:
        if sticky_mode == 'pinned':
            st.markdown(PINNED_NAV_STYLE, unsafe_allow_html=True)
        else:
            st.markdown(STICKY_NAV_STYLE, unsafe_allow_html=True)

    if hide_streamlit_markers:
        st.markdown(HIDE_ST_STYLE, unsafe_allow_html=True)

    if component_value is None:
        if first_select > len(menu_definition):
            if login_name is not None:
                return login_name
            else:
                menu_item = menu_definition[-1]

        elif home_name is None:
            menu_item = menu_definition[first_select]

        else:
            if first_select == 0:
                return home_data.get('id')
            else:
                menu_item = menu_definition[(first_select - 1)]

        if 'id' in menu_item:
            return menu_item.get('id')
        else:
            return menu_item.get('label')
    else:
        return component_value
