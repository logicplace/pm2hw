# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
import weakref
from threading import Thread

def filetypes_min():
	from .i18n import __ as _
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


AN = r"[\da-z-]+(?:\.[\da-z-]+)*"
SEMVER = re.compile(rf"^(\d+(?:\.\d+)*)(?:-({AN}))?(?:\+({AN}))?$", re.I)
class Semver:
	def __init__(self, x: str):
		mo = SEMVER.match(x.strip())
		if not mo:
			raise ValueError(f"bad semantic version {x}")
		self.ver, self.prerelease, self.build = mo.groups()

	def __eq__(self, other):
		if not isinstance(other, Semver):
			return NotImplemented

		return (
			self.ver == other.ver
			and self.prerelease == other.prerelease
			and self.build == other.build
		)

	def __lt__(self, other):
		if not isinstance(other, Semver):
			return NotImplemented

		if self.ver < other.ver:
			return True
		
		if self.ver == other.ver:
			if self.prerelease:
				if not other.prerelease:
					# Pre-releases sort before releases
					return True

				for a, b in zip(self.prerelease, other.prerelease):
					try:
						a = int(a)
					except ValueError:
						a_int = False
					else:
						a_int = True

					try:
						b = int(b)
					except ValueError:
						if a_int:
							# Pure numerics sort before alphanumerics
							return True

					if a != b:
						return a < b

				# Shorter (in terms of parts) pre-release is earlier
				return len(a) < len(b)

		return False		
		