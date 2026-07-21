from pathlib import Path


if __name__ == '__main__':
    from streamlit.web import bootstrap
    import streamlit.config as _config

    _config.set_option("browser.gatherUsageStats", False)
    _config.set_option("server.headless", True)
    _config.set_option("server.address", "0.0.0.0")

    base_path = Path(__file__).parent
    demo_app = base_path / "app.py"
    # demo_app = base_path / "examples_basic.py"
    # demo_app = base_path / "example_dashboard.py"
    demo_app = base_path / "example_streaming.py"
    bootstrap.run(str(demo_app), False, [], flag_options={})
