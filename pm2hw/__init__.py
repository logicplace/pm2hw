from typing import List

import usb
import ftd2xx

from . import pokecard, dittomini
from .base import BaseLinker, BaseCard, linkers, UsbDevice
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

	# Get other linkers
	for dev in usb.core.find(find_all=True):
		linker_id = (dev.idVendor, dev.idProduct)
		if linker_id in linkers:
			linker_cls = linkers[linker_id]
			try:
				linker = linker_cls.from_usb(UsbDevice(dev), **kwargs)
			except DeviceError:
				# TODO: store error for later, in case nothing is found
				continue
			devices.append(linker)

	return devices
