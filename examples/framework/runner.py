from pathlib import Path


if __name__ == '__main__':
    from streamlit.web import bootstrap
    import streamlit.config as _config

    _config.set_option("browser.gatherUsageStats", False)
    _config.set_option("server.headless", True)

    bootstrap.run(str(Path(__file__).parent / "multi_page.py"), False, [], flag_options={})
