# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from time import sleep
from typing import TYPE_CHECKING, ClassVar, Dict, Optional, Tuple, Type, Union

from ..base import (
	Transform, BytesOrSequence, BytesOrTransformer, BytesishOrSequence,
	BaseFlashable, BaseReader, Handle,
)
from ..logger import protocol, warn
from ..locales import _

if TYPE_CHECKING:
	from ..carts.base import BaseCard


LinkerID = Union[str, Tuple[int, int]]
linkers: Dict[LinkerID, type] = {}


class BaseLinker(BaseFlashable):
	name: ClassVar[str]
	serial: str
	card: Optional["BaseCard"] = None
	clock_speed: int  # MHz

	reader: ClassVar[Type[BaseReader]] = BaseReader

	_buffering = False

	def __init__(self, handle: Handle, **kwargs):
		self.handle = handle

	def __del__(self):
		""" Clean up and close """
		self.cleanup()
		self.handle.close()

	def init(self) -> BaseFlashable:
		""" Inititalize the connection to the linker """
		raise NotImplementedError

	def cleanup(self):
		""" Run any cleanup """
		pass

	def read_in(self, size: int) -> bytes:
		""" Read bytes from the queue """
		ret = self.handle.read(size)
		protocol("<", ret)
		return ret

	def write_out(self, data: bytes):
		""" Write bytes over the wire """
		protocol(">", data)
		self.handle.write(data)

	def start_buffering(self):
		self._buffering = True
		self._buffer = b""

	def end_buffering(self):
		self._buffering = False
		if self._buffer:
			self.write_out(self._buffer)
		del self._buffer

	def _write_out_or_buffer(self, data: bytes):
		if self._buffering:
			self._buffer += data
		else:
			self.write_out(data)

	_warned = False
	def _get_wait(self, wait: int):
		prepare_wait = getattr(self, "prepare_wait", None)
		if wait and (not prepare_wait or wait >= 0.001 and not self._buffering):
			# Cannot buffer if there's no prepare_wait
			if not prepare_wait and not self._warned:
				warn(_("log.wait.cannot.buffer"))
				self._warned = True
			def write_and_wait(buf: bytes):
				self.write_out(buf)
				sleep(wait)
		elif wait and prepare_wait:
			prepared_wait = prepare_wait(wait)

			def write_and_wait(buf: bytes):
				self._write_out_or_buffer(buf + prepared_wait)
		else:
			write_and_wait = self.write_out

		return write_and_wait

	def read_data(self, data: BytesOrSequence, size: int, *, wait: int = 0, transform: Optional[Transform] = None) -> BaseReader:
		raise NotImplementedError

	def send(self, data: BytesishOrSequence, *, wait: int = 0, transform: Optional[Transform] = None):
		""" Write commands to the card """
		write_and_wait = self._get_wait(wait)
		if isinstance(data, bytes) or callable(data):
			buf = self.prepare_write(data, transform)
			write_and_wait(buf)
		else:
			for d in data:
				buf = self.prepare_write(d, transform)
				write_and_wait(buf)

	def prepare_write(self, data: BytesOrTransformer, transform: Optional[Transform] = None) -> bytes:
		""" Prepare a "write to flash" message for the linker """
		raise NotImplementedError

	# Default transformers
	@staticmethod
	def noop(x: int) -> int:
		return x

	@staticmethod
	def lsb_first(x: int) -> int:
		return (x * 0x0202020202 & 0x010884422010) % 1023
