# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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


class WeakMethod:
	def __init__(self, o):
		self._m = weakref.WeakMethod(o)

	def __call__(self, *args, **kw):
		fun = self._m()
		if fun is not None:
			return fun(*args, **kw)
