from cognitionlit.plugins.multilit.app_template import MultiHeadApp


class Templateapp(MultiHeadApp):

    def __init__(self, mtitle=None, run_method=None, **kwargs):
        self.__dict__.update(kwargs)
        self.title = mtitle

        if callable(run_method):
            self._run = run_method

            if self.title is None:
                self.title = str(run_method.__name__)
        else:
            raise TypeError(
                'Must provide a callable method when creating a child application using the decorator method.')

    def run(self):
        self._run()
