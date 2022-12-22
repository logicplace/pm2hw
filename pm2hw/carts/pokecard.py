# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This code has been adapted from PokeFlash which is
# Copyright (C) 2008-2013 Lupin

from typing import TYPE_CHECKING, Tuple
from functools import lru_cache

from pm2hw.carts.base import dummy_progress
from pm2hw.carts.base_sst import BaseSstCard
from pm2hw.logger import progress
from pm2hw.exceptions import DeviceNotSupportedError

if TYPE_CHECKING:
	from pm2hw.linkers.base import BaseLinker

# TODO: implement separate Rev 1 and Rev 2.0
class PokeCard512(BaseSstCard):
	memory = 512 * 1024
	block_size = 8 * 1024

	def __init__(self, linker: "BaseLinker"):
		super().__init__(linker)
		self.buffer_sdp = (
			self.prepare_write_packet(0x5555, convert_byte(0xaa))
			+ self.prepare_write_packet(0x2aaa, convert_byte(0x55))
		)
		self.erase_modes = (
			(self.sst_sector_erase, 4 * 1024, 0.025),
			(self.sst_chip_erase, self.memory, 0.100)
		)

	def cleanup(self):
		self.port_state(on=self.PWR)

	def get_device_info(self):
		self.sst_software_id_entry()
		data = self.read_all_data(0, 4)
		self.sst_exit()
		manuf = revert_byte(data[0])
		devc = revert_byte(data[1])
		devcex = revert_byte(data[3])

		# TODO: super doubt these are all wired the same way
		if (manuf, devc, devcex) == (0x1f, 0x13, 0x0f):
			self.chip = "Atmel AT49BV040A"
			self.memory = 512 * 1024
			# wait time for byte_program: 30~50 μs
		elif (manuf, devc) == (0x01, 0x4f):
			# http://instrumentation.obs.carnegiescience.edu/ccd/parts/AM29LV040B.pdf
			self.chip = "AMD AM29LV040B"
			self.memory = 512 * 1024
			# wait time for byte_program: ~9 μs
		elif (manuf, devc) == (0xbf, 0xd7):
			# https://ww1.microchip.com/downloads/en/DeviceDoc/20005023B.pdf
			self.chip = "SST39VF040"
			self.memory = 512 * 1024
			self.name = "PokeCard512 (Rev 2.1)"
			# wait time for byte_program: 14~20 μs
		else:
			raise DeviceNotSupportedError(manuf, devc, devcex)
		return manuf, devc, devcex

	def prepare_sdp_prefixed(self, data: int, addr: int = 0x5555):
		return super().prepare_sdp_prefixed(convert_byte(data), addr)

	def deconstruct_packet(self, packet: bytes) -> Tuple[int, int]:
		# Layout:
		# xAAA AAAA AAAA AAAA AAAA xCxD DDDD DDDx
		x = int.from_bytes(packet[:4], "big", signed=False)
		return (x & 0x7ffff000) >> 12, (x & 0x1fe) >> 1

	@staticmethod
	def prepare_write_packet(addr: int, data: int):
		return (
			# Layout: xAAA AAAA AAAA AAAA AAAA xCxD DDDD DDDx
			((addr & 0x07ffff) << 12)
			| 0x400  # Write indicator
			| ((data & 0xff) << 1)
		).to_bytes(4, "big")

	@staticmethod
	def prepare_read_packet(addr: int):
		return (
			# Layout: xAAA AAAA AAAA AAAA AAAA xCxD DDDD DDDx
			((addr & 0x07ffff) << 12)
		).to_bytes(4, "big")

	def read_data(self, addr: int, size: int, *, prog: progress = dummy_progress):
		for start, bsize in self.blocks(addr, size):
			ret = self.linker.read_data(
				b"".join(
					self.prepare_read_packet(a)
					for a in range(start, start + bsize)
				),
				bsize
			).read()
			prog.add(bsize)
			yield ret

	# Chip commands
	T_BP = 23.46e-6  # μs
	T_IDA = 150e-9  # ns
	T_SCE = 0.100  # ms

	def sst_sector_erase(self, addr: int):
		self.linker.send(
			self.prepare_sdp_prefixed(0x80)
			+ self.prepare_sdp_prefixed(0x30, addr),
			wait=0.025
		)

ON_0 = 1 << 0
ON_1 = 1 << 1
ON_2 = 1 << 2
ON_3 = 1 << 3
ON_4 = 1 << 4
ON_5 = 1 << 5
ON_6 = 1 << 6
ON_7 = 1 << 7

@lru_cache(maxsize=10)
def convert_byte(byte: int):
	bret = 0
	if byte & ON_0: bret |= ON_7
	if byte & ON_1: bret |= ON_5
	if byte & ON_2: bret |= ON_3
	if byte & ON_3: bret |= ON_1
	if byte & ON_4: bret |= ON_0
	if byte & ON_5: bret |= ON_2
	if byte & ON_6: bret |= ON_4
	if byte & ON_7: bret |= ON_6
	return bret

def revert_byte(byte: int):
	bret = 0
	if byte & ON_7: bret |= ON_0
	if byte & ON_5: bret |= ON_1
	if byte & ON_3: bret |= ON_2
	if byte & ON_1: bret |= ON_3
	if byte & ON_0: bret |= ON_4
	if byte & ON_2: bret |= ON_5
	if byte & ON_4: bret |= ON_6
	if byte & ON_6: bret |= ON_7
	return bret

