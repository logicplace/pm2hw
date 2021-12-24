# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from os import SEEK_SET, SEEK_CUR, SEEK_END
from typing import TYPE_CHECKING, BinaryIO, ClassVar, Iterator, Optional, Tuple

from ..logger import error, log, progress, verbose, warn
from ..locales import _, natural_size
from ..exceptions import DeviceError
from ..base import BaseFlashable

if TYPE_CHECKING:
	from ..linkers.base import BaseLinker

class DummyProgress(progress):
	for x in progress.__dict__.keys():
		locals()[x] = staticmethod(lambda *a,**kw: None)

dummy_progress = DummyProgress("", 0)

class BaseCard(BaseFlashable):
	chip: str
	memory: int  # Size available in bytes
	block_size: int
	packet_size: ClassVar[int]
	_cursor = 0

	def __init__(self, linker: "BaseLinker"):
		self.linker = linker

	# Top level methods
	def blocks(self, start: int = 0, size: int = 0):
		memory = self.memory
		block_size = self.block_size

		if not size:
			end = memory
		elif start + size > memory:
			warn(_("log.blocks.over"))
			end = memory
		else:
			end = start + size

		for addr in range(start, end, block_size):
			yield addr, min(end - addr, block_size)

	def flash(self, stream: BinaryIO, *, erase: bool = True):
		""" Flash a ROM to the card """
		# Get file size
		stream.seek(0, SEEK_END)
		size = stream.tell()
		if (size > self.memory):
			raise DeviceError(_("exception.flash.too-large").format(size=natural_size(self.memory)))
		stream.seek(0, SEEK_SET)

		# Chip erase or sector erase
		if erase:
			self.erase_data(0, size)

		prog = progress(
			progress.config.get_message("flash"),
			size,
			card=self,
			fn=stream.name
		)

		# Programming
		self.write_data(0, stream.read(size), prog=prog)

	def verify(self, stream: BinaryIO) -> bool:
		""" Verify the ROM on the card is correct """
		stream.seek(0, SEEK_END)
		size = stream.tell()
		prog = progress(
			progress.config.get_message("verify"),
			size,
			card=self
		)
		stream.seek(0, SEEK_SET)

		block_size = self.block_size
		read = block_size
		bads = []
		for dump in self.read_data(0, size):
			dumped = len(dump)
			orig = stream.read(read)
			read = len(orig)
			if orig != (dump if dumped == read else dump[:read]):
				count = len([i for i, (o, d) in enumerate(zip(orig, dump)) if o != d])
				bads.append(count)
			prog.add(read)
			if read < dumped:
				# I don't think this should happen tho
				break 
		prog.done()

		if any(bads):
			error(_("log.verify.failed"))
			verbose(_("log.verify-failed.report.title"))
			for i, c in enumerate(bads):
				verbose(_("log.verify-failed.report.entry"), block=i, count=c)
			return False
		else:
			log(_("log.verify.success"))
		return True

	def dump(self, stream: BinaryIO, *, offset: int = 0, size: int = 0):
		""" Dump a ROM from the card """
		prog = progress(
			progress.config.get_message("dump"),
			size or self.memory,
			card=self,
			fn=getattr(stream, "name", _("RAM"))
		)
		for data in self.read_data(offset, size, prog=prog):
			stream.write(data)

	def erase(self, *, offset: int = 0, size: int = 0):
		prog = progress(
			progress.config.get_message("erase"),
			size,
			card=self
		)
		self.erase_data(offset, size or self.memory, prog=prog)

	# Methods you must implement
	def get_device_info(self) -> Tuple[int, int, Optional[int]]:
		""" Return the device manufacture, code, and possibly extended code """
		raise NotImplementedError

	def deconstruct_packet(self, packet: bytes) -> Tuple[int, int]:
		""" Return the addr, data from a raw packet """
		raise NotImplementedError

	def write_data(self, addr: int, data: bytes, *, prog: progress = dummy_progress):
		""" Prepare the write command(s) for some data """
		raise NotImplementedError

	def read_data(self, addr: int, size: int, *, prog: progress = dummy_progress) -> Iterator[bytes]:
		""" Prepare the read command(s) for some data """
		raise NotImplementedError

	def read_all_data(self, addr: int, size: int) -> bytes:
		return b"".join(self.read_data(addr, size))

	def erase_data(self, addr: int, size: int, *, prog: progress = dummy_progress):
		""" Prepare erase command(s) for some section """
		raise NotImplementedError

	def read(self, size: int):
		addr = self._cursor
		data = self.read_all_data(addr, size)
		self._cursor += len(data)
		return data

	def write(self, data: bytes):
		addr = self._cursor
		self.write_data(addr, data)
		size = len(data)
		self._cursor += size
		return size

	def seek(self, offset: int, whence: int = SEEK_SET):
		if whence == SEEK_SET:
			self._cursor = offset
		elif whence == SEEK_CUR:
			self._cursor += offset
		elif whence == SEEK_END:
			self._cursor = self.memory + offset
		else:
			raise ValueError("whence must be one of: SEEK_SET, SEEK_CUR, or SEEK_END")
		if self._cursor < 0:
			self._cursor = 0
		elif self._cursor > self.memory:
			self._cursor = self.memory
