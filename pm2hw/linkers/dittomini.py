# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This code has been adapted from hm05 which is licensed under MIT License and
# Copyright (c) 2021 Miguel Ángel Pérez Martínez

from typing import Optional

from .base import linkers
from .base_ftdi import BaseFtdiLinker
from ..base import BytesOrTransformer, Transform

DEV_DESC = b"Dual RS232 A"
# DEV_DESC = b"USB SerialConverter A"
# DEV_DESC = b"FT2232H MiniModule A"

class DittoFlash(BaseFtdiLinker):
	name = "DITTO mini Flasher"
	clock_divisor = 1

	PWR = BaseFtdiLinker.GPIOL0
	PWR_READ = BaseFtdiLinker.GPIOL3

	ftdi_port_state = BaseFtdiLinker.TMS_CS
	ftdi_port_direction = PWR | BaseFtdiLinker.ftdi_port_direction

	def init(self):
		super().init()

		# Set CS to low, start programming operation
		self.port_state(0)

		return self.detect_card()

	def cleanup(self):
		self.port_state(on=self.PWR)

	def detect_card(self):
		""" Detect which card is connected """
		from ..carts.dittomini import DittoMiniRev3
		self.card = card = DittoMiniRev3(self)
		card.get_device_info()
		return card

	# def read_data(self, data: BytesOrSequence, size: int, *, wait: int = 0, transform: Optional[Transform] = None):
	# 	""" Write commands to the card and read the response """
	# 	self.send(data, wait=wait)
	# 	buf, do_transform = self.prepare_read(size, transform)
	# 	if self._buffering:
	# 		self._buffer += buf
	# 	else:
	# 		self.write_out(buf)
	# 	return self.reader(self.handle, size, transform if do_transform else None)

	# def prepare_read(self, size: int, transform: Optional[Transform] = None):
	# 	size_bytes = (size - 1).to_bytes(2, "little")
	# 	if transform == self.lsb_first:
	# 		return b"\x2c" + size_bytes, False
	# 	return b"\x24" + size_bytes, True

	def prepare_write(self, data: BytesOrTransformer, transform: Optional[Transform] = None):
		if callable(data):
			data = data(transform or self.noop)
		return b"\x11" + (len(data) - 1).to_bytes(2, "little") + data

	def prepare_wait(self, secs: int) -> bytes:
		# No idea how long it takes but the other code writes
		# four 0x80 commands for a program byte command.
		# TODO: Make this acceptable
		from ..carts.dittomini import DittoMiniRev3
		if secs == DittoMiniRev3.T_BP:
			cmd = bytes([0x80, self.ftdi_port_state, self.ftdi_port_direction])
			return cmd * 4
		return b""

linkers[DEV_DESC] = DittoFlash
