from contextlib import contextmanager

import ftd2xx

class DeviceError(Exception): pass

class DeviceNotSupportedError(DeviceError):
	def __init__(self, manufacturer: int, device: int, extended: int):
		super().__init__("Device not supported", manufacturer, device, extended)
		self.manufacturer = manufacturer
		self.device = device
		self.extended = extended

	def __str__(self):
		return """\
			Device not supported:
			Manufacturer code: {:02X}
			Device code: {:02X}
			Extended code: {:02X}
		""".format(
			self.manufacturer,
			self.device,
			self.extended
		).replace("\t", "")

	def __repr__(self):
		name = type(self).__name__
		args = ", ".join(
			"{}=0x{:02x}".format(x, getattr(self, x))
			for x in ["manufacturer", "device", "extended"]
		)
		return "{}({})".format(name, args)

@contextmanager
def clarify(error_msg):
	try:
		yield
	except ftd2xx.DeviceError as err:
		raise DeviceError("{}: {}".format(error_msg, str(err))) from None
	except DeviceError:
		raise DeviceError(error_msg) from None
