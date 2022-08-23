# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import List
import ftd2xx

from .base import BaseFlashable
from .carts import BaseCard
from .linkers import BaseLinker, linkers
from .locales import _
from .exceptions import *

__version__ = "0.0.7"

def get_connected_linkers():
	# Get D2xx linkers
	num_devices = ftd2xx.createDeviceInfoList()
	devices: List[BaseLinker] = []
	for i in range(num_devices):
		# getDeviceInfoDetail returns null data for PokeCard
		with clarify(_("exception.device.open.failed")):
			dev = ftd2xx.open(i)
		linker_cls = linkers.get(dev.description)
		if linker_cls:
			devices.append(linker_cls(dev))
		else:
			dev.close()

	return devices
