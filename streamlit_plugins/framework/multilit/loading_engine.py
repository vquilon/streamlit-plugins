import logging
import traceback
from typing import Callable, Tuple, Optional, Generic

from streamlit.runtime.scriptrunner import StopException

from streamlit_plugins.components.loader import LoadersLib, DefaultLoader, LoaderType, BaseLoader

logger = logging.getLogger(__name__)


class LoadingWithStatement:
    def __init__(
        self, loader: BaseLoader,
        **run_loader_kwargs
    ):
        self.loader = loader
        self.run_loader_kwargs = run_loader_kwargs
    
    def __enter__(self):
        try:
            self.loader.run_loader(
                **self.run_loader_kwargs
            )
        # except RerunException as e:
        #     st.rerun()
        except StopException as e:
            ...
        except Exception as e:
            # st.error(f"Error details: {e}")
            logger.error(traceback.format_exc())
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.loader.stop_loader()


class LoadingEngine:
    default_loader_lib: LoadersLib = LoadersLib.book_loader

    def __init__(self, default_loader: BaseLoader):
        self.selected_loader = default_loader
        self.loaders = {}
        self.loaders_params = {}

    @classmethod
    def get_default_loader(cls, loader_container_key: str, loader_params: Optional[dict] = None, loader_lib: LoadersLib | Callable[..., Tuple[str, str ,str], ] = None) -> DefaultLoader:
        loader_params = loader_params or {}

        loader_lib = loader_lib or cls.default_loader_lib
        return DefaultLoader(
            loader_container_key=loader_container_key,
            **loader_params,
            loader_lib=loader_lib
        )

    def register_page_loader(self, page_id: str | int, loader: BaseLoader, run_loader_kwargs: Optional[dict] = None):
        self.loaders[page_id] = loader
        self.loaders_params[page_id] = run_loader_kwargs or {}

    def loading(self, page_id: str | int, **run_loader_kwargs):
        selected_loader = self.loaders.get(page_id, self.selected_loader) or self.selected_loader
        run_loader_kwargs = {**self.loaders_params.get(page_id, run_loader_kwargs), **run_loader_kwargs}
        return LoadingWithStatement(
            selected_loader,
            # Any argument that can be changed dinamically
            **run_loader_kwargs
            # label=label, height=height,
            # primary_color=primary_color,
            # background_color=background_color
        )