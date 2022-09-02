# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from time import sleep, time
from typing import ClassVar, Optional, cast

from ftd2xx import FTD2XX

from pm2hw.base import chunked, Transform, BytesOrSequence, BaseReader
from pm2hw.config import config
from pm2hw.logger import protocol
from pm2hw.locales import delayed_gettext as _
from pm2hw.linkers.base import BaseLinker
from pm2hw.exceptions import clarify, DeviceError

class BaseFtdiLinker(BaseLinker):
	handle: FTD2XX

	clock_divisor: int

	TSK_SK = 1 << 0
	TDI_DO = 1 << 1
	TDO_DI = 1 << 2
	TMS_CS = 1 << 3
	GPIOL0 = 1 << 4
	GPIOL1 = 1 << 5
	GPIOL2 = 1 << 6
	GPIOL3 = 1 << 7
	# GPIOH0~GPIOH7 would go here if supported

	# Note this currently only supports the low byte
	ftdi_port_state: int
	ftdi_port_direction: ClassVar[int] = TSK_SK | TDI_DO | TMS_CS

	def __init__(self, handle: FTD2XX):
		super().__init__(handle)
		self.serial = handle.getDeviceInfo()["serial"]

	def init(self):
		self.reload_config()

		handle = self.handle
		protocol(_("log.ftdi.title"))

		with clarify(_("exception.ftdi.reset.failed")):
			handle.resetDevice()
			protocol(_("log.ftdi.reset"))

		# Clear the input buffer
		self.read_all()

		# Disable event and error characters
		with clarify(_("exception.ftdi.characters.disable.failed")):
			handle.setChars(0, 0, 0, 0)
			protocol(_("log.ftdi.characters.disable"))

		# Set USB request transfer size to 64KiB
		with clarify(_("exception.ftdi.transfer.size.set.failed")):
			handle.setUSBParameters(65536, 65536)
			protocol(_("log.ftdi.transfer.size.set"), **{"in": 65536, "out": 65536})

		# Sets the read and write timeouts in 10 sec
		handle.setTimeouts(10000, 10000)
		protocol(_("log.ftdi.transfer.timeout.set"), read=10000, write=10000)

		# Setup latency
		with clarify(_("exception.ftdi.latency.set.failed")):
			handle.setLatencyTimer(255)
			protocol(_("log.ftdi.latency.set"), ms=255)

		# Reset controller
		with clarify(_("exception.ftdi.controller.reset.failed")):
			handle.setBitMode(0x0, 0x0)
			protocol(_("log.ftdi.controller.reset"))

		# Set the port to MPSSE mode
		with clarify(_("exception.ftdi.mpsse.enable.failed")):
			handle.setBitMode(0x0, 0x2)
			protocol(_("log.ftdi.mpsse.enable"))

		sleep(0.050)

		# Check sync...
		with clarify(_("exception.ftdi.mpsse.sync.failed")):
			self.sync_to_mpsse()

		with clarify(_("exception.ftdi.mpsse.spi.failed")):
			self.configure_mpsse_for_spi()

	def reload_config(self):
		self.clock_divisor = config.getint(
			type(self).__name__,
			"clock-divisor",
			fallback=self.configuration["clock-divisor"][3],
		)

	def sync_to_mpsse(self):
		# https://www.ftdichip.com/Support/Documents/AppNotes/AN_108_Command_Processor_for_MPSSE_and_MCU_Host_Bus_Emulation_Modes.pdf
		handle = self.handle

		# Clear input buffer
		self.read_all()

		# Enable loopback (TODO: pokecard test)
		self.write_out(b"\x84")
		assert handle.getQueueStatus() == 0

		# Put a bad command to the command processor (AA or AB)
		self.write_out(b"\xaa")

		# Wait for a response and confirm MPSSE says it's a bad command
		if self.wait_read(2) != b"\xfa\xaa":
			raise DeviceError(_("exception.ftdi.mpsse.sync.failed-check"))

	def configure_mpsse_for_spi(self):
		handle = self.handle

		# Ditto mini does not support these but the example suggests them
		# The example: https://www.ftdichip.com/Support/Documents/AppNotes/AN_114_FTDI_Hi_Speed_USB_To_SPI_Example.pdf
		# Only PokeCard supports 8A and Ditto mini doesn't even have adaptive clocking
		self.write_out(
			b"\x8a"  # Use 60MHz master clock (disable divide by 5)
			b"\x97"  # Turn off adaptive clocking
		# 	b"\x8d"  # Disable three phase clocking
			b"\x87"
		)
		sleep(0.010)

		# Check if the features were compatible with this chip
		tmp = self.read_all()
		slow_clock = tmp and b"\xfa\x8a" in tmp

		self.write_out(bytes([
			# Command to set directions of lower 8 pins and force value on bits set as output
			0x80,  # Command
			self.ftdi_port_state,
			self.ftdi_port_direction,
			# Set SK Clock divisor
			# TCK/SK period = master_clock  /  (( 1 + clock_divisor ) * 2)
			# master_clock is 12MHz normally, or 60MHz with "divide by 5" disabled
			# The FT2232D (Ditto mini flasher) is stuck with 12MHz
			# The FT2232H (PokeCard flasher) can disable divide by 5 and use 60MHz
			0x86,  # Command
			*self.clock_divisor.to_bytes(2, "little")
		]))
		self.clock_speed = (12 if slow_clock else 60) / (( 1 + self.clock_divisor) * 2)  # MHz

		# Disable loopback
		self.write_out(b"\x85")
		assert handle.getQueueStatus() == 0

	def port_state(self, set: int = -1, *, on: int = 0, off: int = 0):
		if set >= 0:
			new_state = set
		else:
			new_state = (self.ftdi_port_state & ~off) | on
		if new_state != self.ftdi_port_state:
			self.write_out(bytes([
				0x80,  # Command
				new_state,
				self.ftdi_port_direction
			]))
			self.ftdi_port_state = new_state

	def read_in(self, size: int) -> bytes:
		packet_size = self.card.packet_size
		data = self.wait_read(packet_size * size, exact=False)
		protocol("<", data)
		return bytes(
			self.card.deconstruct_packet(p)[1]
			for p in chunked(packet_size, data)
		)

	def write_out(self, data: bytes):
		return super().write_out(data + b"\x87")

	def read_data(self, data: BytesOrSequence, size: int, *, wait: int = 0, transform: Optional[Transform] = None) -> BaseReader:
		""" Write commands to the card and read the response """
		if not data:
			return self.reader(self, 0)

		if not wait:
			if not isinstance(data, bytes):
				data = b"".join(data)
			buffer = b"\x35" + (len(data) - 1).to_bytes(2, "little") + data + b"\x87"
			self._write_out_or_buffer(buffer)
		else:
			# Add waits between each read
			write_and_wait = self._get_wait(wait)
			if isinstance(data, bytes):
				buffer = b"\x35" + (len(data) - 1).to_bytes(2, "little") + data + b"\x87"
				write_and_wait(buffer)
			else:
				for d in data:
					buffer = b"\x35" + (len(d) - 1).to_bytes(2, "little") + d
					write_and_wait(buffer)
				self._write_out_or_buffer(b"\x87")
		return self.reader(self, size, transform)

	def read_all(self):
		""" Read the entire input buffer """
		size = self.handle.getQueueStatus()
		if size:
			ret = cast(bytes, self.handle.read(size))
			protocol("<", ret)
			return ret
		return b""

	def wait_read(self, size: int, secs: float = 20, exact: bool = True):
		handle = self.handle
		start = time()
		while handle.getQueueStatus() < size and time() - start < secs:
			pass
		queued = handle.getQueueStatus()
		if exact and queued > size:
			raise DeviceError(
				_("exception.read.wait.too-large").format(
					size=size, queued=queued))
		if queued < size:
			raise DeviceError(
				_("exception.read.wait.timeout").format(
					size=size, queued=queued))
		
		if queued:
			ret = cast(bytes, handle.read(size))
			protocol("<", ret)
			return ret
		return b""

	@property
	def vendor_id(self):
		return self.handle.id >> 16

	@property
	def product_id(self):
		return self.handle.id & 0xffff

