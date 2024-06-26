import streamlit as st
from streamlit_plugins.framework.multilit import MultiApp, MultiHeadApp

def run():
    multi_app = MultiApp(
        title="Demo", nav_container=None, nav_horizontal=True, layout='wide', favicon="📚",
        use_navbar=True, navbar_sticky=True, navbar_mode="pinned",
        use_cookie_cache=True, sidebar_state='auto',
        navbar_animation=True, allow_url_nav=True, hide_streamlit_markers=False, use_banner_images=None,
        banner_spacing=None, clear_cross_app_sessions=True, session_params=None,
    )

    class DemoApp(MultiHeadApp):
        def run(self):
            st.title("Demo")
            st.write("This is a demo app.")

    demo_app = DemoApp()

    @multi_app.addapp(title="Home", is_home=True)
    def my_home():
        st.info('HOME')
        # st.markdown('<a target="_self" href="?selected=app_1">Demo Page</a>', unsafe_allow_html=True)
        multi_app.change_app_button(demo_app.get_id(), "Demo")

    multi_app.add_app(title="Demo", app=demo_app, icon=None)

    multi_app.get_nav_transition()

    multi_app.run()


if __name__ == '__main__':
    try:
        import sys

        if "_pydevd_frame_eval.pydevd_frame_eval_cython_wrapper" not in sys.modules:
            import _pydevd_frame_eval.pydevd_frame_eval_cython_wrapper
    except ImportError:
        pass

    run()

