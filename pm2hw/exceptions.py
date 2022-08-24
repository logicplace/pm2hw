# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import contextmanager
from typing import ClassVar

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
		return str(_("exception.device.unsupported.details").format(
			err=self.args[0],
			manufacturer=self.manufacturer,
			device=self.device,
			extended=self.extended,
		))

	def __repr__(self):
		name = type(self).__name__
		args = ", ".join(
			f"{x}=0x{getattr(self, x):02x}"
			for x in ["manufacturer", "device", "extended"]
		)
		return f"{name}({args})"

class DeviceTestError(DeviceError):
	pass

class DeviceTestReadingError(DeviceTestError):
	def __init__(self, 
		device_size: int,
		completely_wrong: int,
		partially_wrong: int,
		consistently_wrong: int,
	):
		super().__init__(
			_("exception.device.test.read.failed"),
			device_size,
			completely_wrong,
			partially_wrong,
			consistently_wrong,
		)
		self.errors = completely_wrong + partially_wrong + consistently_wrong
		self.percent = self.errors * 100 / device_size
		self.completely_wrong = completely_wrong
		self.partially_wrong = partially_wrong
		self.consistently_wrong = consistently_wrong

	def __str__(self):
		return str(_("exception.device.test.read.failed.details").format(
			errors=self.errors,
			percent=self.percent,
			completely_wrong=self.completely_wrong,
			partially_wrong=self.partially_wrong,
			consistently_wrong=self.consistently_wrong,
		))

	def __repr__(self):
		name = type(self).__name__
		args = ", ".join(map(str, self.args))
		return f"{name}({args})"

class DeviceTestWritingError(DeviceTestError):
	def __init__(self, 
		device_size: int,
		errors: int,
	):
		super().__init__(
			_("exception.device.test.write.failed"),
			device_size,
			errors,
		)
		self.errors = errors
		self.percent = errors * 100 / device_size

	def __str__(self):
		return str(_("exception.device.test.write.failed.details").format(
			errors=self.errors,
			percent=self.percent,
		))

	def __repr__(self):
		name = type(self).__name__
		args = ", ".join(map(str, self.args))
		return f"{name}({args})"


@contextmanager
def clarify(error_msg):
	try:
		yield
	except ftd2xx.DeviceError as err:
		raise DeviceError(f"{error_msg}: {err}") from None
	except DeviceError:
		raise DeviceError(error_msg) from None
