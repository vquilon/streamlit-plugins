import os
import sys
from pathlib import Path

from streamlit.web import bootstrap
from streamlit import config as _config

if __name__ == '__main__':
    # Se agregan los componentes y modulos nuevos
    sys.path.append(str(Path(__file__).resolve().parents[4]))
    real_script = "app.py"
    os.environ['RELEASE'] = 'DEV'
    _config.set_option("browser.gatherUsageStats", False)
    _config.set_option("server.headless", True)
    # _config.set_option("server.port", 8502)
    args = []

    bootstrap.run(real_script, False, args, flag_options={})
