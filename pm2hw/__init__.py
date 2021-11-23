from typing import List
import ftd2xx

from . import pokecard, dittomini
from .base import BaseLinker, BaseCard, linkers
from .exceptions import *

def get_connected_linkers(**kwargs):
	# Get D2xx linkers
	num_devices = ftd2xx.createDeviceInfoList()
	devices: List[BaseLinker] = []
	for i in range(num_devices):
		# getDeviceInfoDetail returns null data for PokeCard
		with clarify("Failed opening the device!"):
			dev = ftd2xx.open(i)
		linker_cls = linkers.get(dev.description)
		if linker_cls:
			devices.append(linker_cls(dev, **kwargs))
		else:
			dev.close()

	return devices
