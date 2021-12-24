# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from time import sleep, time
from typing import Callable, ClassVar, Sequence, Tuple

from .base import dummy_progress, BaseCard
from ..base import chunked
from ..logger import progress
from ..locales import _

class BaseSstCard(BaseCard):
	packet_size = 4
	erased = (0, 0)

	# method, size (bytes), speed (seconds)
	# Order by shortest size first
	erase_modes: Sequence[Tuple[Callable, int, float]]

	# Software Data Protection
	buffer_sdp: bytes = b""

	def erase_data(self, addr: int = 0, size: int = 0, *, prog: progress = dummy_progress):
		if not size:
			size = self.memory

		if addr == 0 and size == self.memory:
			# Do a full chip erase.
			self.sst_chip_erase()
			self._wait_for_erased(0, 20)
			prog.update(size)
		elif addr % 0x04000 == 0 and size % 0x04000 == 0:
			# Sector erase
			for a in range(addr, addr + size, 0x04000):
				prog.update(a - addr)
				self.sst_sector_erase(a)
				self._wait_for_erased(a, 5)
			prog.update(a - addr)
		else:
			# Overwrite memory manually
			# onset .. sectors .. coda
			shortest = self.erase_modes[0][1]
			onset = addr % shortest
			if onset:
				onset = shortest - onset
			coda = (addr + size) % shortest

			# Erase parts which are valid sectors
			sectors_start = addr + onset
			sectors_end = addr + size - coda
			for a in range(sectors_start, sectors_end, 0x04000):
				prog.update(a - addr - onset)
				self.sst_sector_erase(a)
				self._wait_for_erased(a, 5)
			prog.update(a - addr - onset)

			# Overwrite onset and coda (the bookends)
			self.write_data(addr, b"\xff" * onset)
			prog.add(onset)
			self.write_data(sectors_end, b"\xff" * coda)
			prog.add(coda)
		self.erased = (addr, addr + size)

	def _wait_for_erased(self, addr: int, secs: int):
		start = time()
		while self.read_all_data(addr, 1)[0] != 0xff and time() - start < 5:
			sleep(0.050)

	def write_data(self, addr: int, data: bytes, *, prog: progress = dummy_progress):
		for (start, bsize), block in zip(
			self.blocks(addr, len(data)),
			chunked(self.block_size, data)
		):
			self.linker.start_buffering()
			for a, d in zip(range(start, start + bsize), block):
				self.sst_byte_program(a, d)
			self.linker.end_buffering()
			prog.add(bsize)

	def prepare_sdp_prefixed(self, data: int, addr: int):
		return self.buffer_sdp + self.prepare_write_packet(addr, data)

	@staticmethod
	def prepare_write_packet(addr: int, data: int):
		raise NotImplementedError

	@staticmethod
	def prepare_read_packet(addr: int):
		raise NotImplementedError

	# Chip commands
	T_BP: ClassVar[float]
	T_IDA: ClassVar[float]
	T_SCE: ClassVar[float]

	def sst_byte_program(self, addr: int, data: int, **kwargs):
		# Byte-Program op completes in 14~20 μs on SST39VF040
		# and 10 μs on SST39VF1681
		if data == 0xff and self.erased[0] < addr < self.erased[1]:
			return  # Nothing to do
		self.linker.send(
			self.prepare_sdp_prefixed(0xa0)
			+ self.prepare_write_packet(addr, data),
			wait=self.T_BP,
			**kwargs
		)

	def sst_chip_erase(self):
		self.linker.send(
			self.prepare_sdp_prefixed(0x80)
			+ self.prepare_sdp_prefixed(0x10),
			wait=self.T_SCE
		)

	def sst_software_id_entry(self):
		self.linker.send(
			self.prepare_sdp_prefixed(0x90),
			wait=self.T_IDA
		)

	def sst_exit(self):
		""" Exit query modes, back to read mode """
		self.linker.send(
			self.prepare_sdp_prefixed(0xf0),
			wait=self.T_IDA
		)
