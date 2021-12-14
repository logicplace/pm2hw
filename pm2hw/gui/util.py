from threading import Thread

from .i18n import _

filetypes_min = (
	(_("Pokemon mini ROMs"), "*.min"),
	(_("All files"), "*"),
)

# https://gist.github.com/awesomebytes/0483e65e0884f05fb95e314c4f2b3db8
def threaded(fn):
    """ To use as decorator to make a function call threaded. """
    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper
