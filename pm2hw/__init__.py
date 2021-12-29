from typing import List
import ftd2xx

from .base import BaseFlashable
from .carts import BaseCard
from .linkers import BaseLinker, linkers
from .locales import _
from .exceptions import *

def get_connected_linkers(**kwargs):
	# Get D2xx linkers
	num_devices = ftd2xx.createDeviceInfoList()
	devices: List[BaseLinker] = []
	for i in range(num_devices):
		# getDeviceInfoDetail returns null data for PokeCard
		with clarify(_("exception.device.open.failed")):
			dev = ftd2xx.open(i)
		linker_cls = linkers.get(dev.description)
		if linker_cls:
			devices.append(linker_cls(dev, **kwargs))
		else:
			dev.close()

	return devices
