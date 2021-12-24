# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This code has been adapted from PokeFlash which is
# Copyright (C) 2008-2013 Lupin

from math import ceil
from time import sleep
from typing import Optional

from .base import linkers
from .base_ftdi import BaseFtdiLinker
from ..base import BytesOrTransformer, Transform
from ..exceptions import DeviceError

DEV_DESC = b"Dual RS232-HS B"  # "FT2232H MiniModule A"

# TODO: separate Rev 2.0 linker
class PokeFlash(BaseFtdiLinker):
	name = "PokeFlash"
	clock_divisor = 0

	PWR = BaseFtdiLinker.GPIOL1
	PWR_READ = BaseFtdiLinker.GPIOL3

	ftdi_port_state = PWR | BaseFtdiLinker.TMS_CS
	ftdi_port_direction = PWR | BaseFtdiLinker.ftdi_port_direction

	def init(self):
		super().init()

		# now check if the cart is already powered (inside PM)
		self.write_out(b"\x81")
		dat_buffer = self.wait_read(1)

		if dat_buffer[0] & 0x80:
			raise DeviceError("Cart seems to be powered (VCC is on) - please turn off your PM!")

		# Set CS high and power on cart
		self.port_state(self.TMS_CS)
		sleep(0.010)
		# Set CS to low, start programming operation
		self.port_state(0)

		return self.detect_card()

	def detect_card(self):
		""" Detect which card is connected """
		from ..carts.pokecard import PokeCard512
		self.card = card = PokeCard512(self)
		card.get_device_info()
		return card

	def prepare_write(self, data: BytesOrTransformer, transform: Optional[Transform] = None):
		if callable(data):
			data = data(transform or self.noop)
		return b"\x11" + (len(data) - 1).to_bytes(2, "little") + data

	def prepare_wait(self, secs: int) -> bytes:
		# TODO: currently assuming a clock period based on some math
		# in the original source... Also TODO: use clock_speed ?
		# SST39VF040 - 14 to 20 us byte prog time     wait_cycles=20 (21,333us)
		# Original math: wait_cycles*4*8*(1/30MHz) ~= wait_cycles*1us
		# The 8 here is due to the 0x8f command pulsing the clock 8 times
		res = secs * self.clock_speed * 1e6 / 8
		if res < 1:
			return b""
		wait_cycles = ceil(res) - 1
		# The 2b here is ftdi_port_direction
		return b"\x80\x00\x2b\x8f" + wait_cycles.to_bytes(2, "little")

linkers[DEV_DESC] = PokeFlash
