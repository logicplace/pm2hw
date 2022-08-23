# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .base import BaseLinker, linkers
from .pokecard import PokeFlash
from .dittomini import DittoFlash

extra_options = {
	x.__name__: x.configuration
	for x in linkers.values()
}

linkers_by_classname = {
	x.__name__: x
	for x in linkers.values()
}


from ..config import config
from configparser import DuplicateSectionError

for x in linkers.values():
	try:
		config.add_section(x.__name__)
	except DuplicateSectionError:
		pass
