from contextlib import contextmanager

import ftd2xx

from .locales import _

class DeviceError(Exception): pass

class DeviceNotSupportedError(DeviceError):
	def __init__(self, manufacturer: int, device: int, extended: int):
		super().__init__(_("exception.device.unsupported"), manufacturer, device, extended)
		self.manufacturer = manufacturer
		self.device = device
		self.extended = extended

	def __str__(self):
		return _().format(
			self.args[0],
			manufacturer=self.manufacturer,
			device=self.device,
			extended=self.extended,
		)

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
