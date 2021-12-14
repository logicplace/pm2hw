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
		return f"""\
			Device not supported:
			Manufacturer code: {self.manufacturer:02X}
			Device code: {self.device:02X}
			Extended code: {self.extended:02X}
		""".replace("\t", "")

	def __repr__(self):
		name = type(self).__name__
		args = ", ".join(
			f"{x}=0x{getattr(self, x):02x}"
			for x in ["manufacturer", "device", "extended"]
		)
		return f"{name}({args})"

@contextmanager
def clarify(error_msg):
	try:
		yield
	except ftd2xx.DeviceError as err:
		raise DeviceError(f"{error_msg}: {err}") from None
	except DeviceError:
		raise DeviceError(error_msg) from None
