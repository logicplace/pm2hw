import weakref
from threading import Thread

@property
def filetypes_min():
	from .i18n import _
	return (
		(_("misc.filetypes.min"), "*.min"),
		(_("misc.filetypes.all"), "*"),
	)

# https://gist.github.com/awesomebytes/0483e65e0884f05fb95e314c4f2b3db8
def threaded(fn):
    """ To use as decorator to make a function call threaded. """
    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper


class WeakMethod(weakref.WeakMethod):
	def __call__(self, *args, **kw):
		fun = super().__call__()
		if fun is not None:
			return fun(*args, **kw)
