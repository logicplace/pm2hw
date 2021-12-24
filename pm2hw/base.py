# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BufferedIOBase, BytesIO
from os import SEEK_SET
from typing import TYPE_CHECKING, Any, BinaryIO, Callable, ClassVar, Iterable, Optional, Protocol, Union

if TYPE_CHECKING:
	from .linkers.base import BaseLinker

Transform = Callable[[int], int]

BytesOrSequence = Union[
	bytes,
	Iterable[bytes]
]

BytesOrTransformer = Union[
	bytes,
	Callable[[Transform], bytes]
]

BytesishOrSequence = Union[
	BytesOrTransformer,
	Iterable[BytesOrTransformer]
]

def chunked(size, source):
    for i in range(0, len(source), size):
        yield source[i:i+size]

class Handle(Protocol):
	def read(self, size: int) -> bytes:
		...

	def write(self, data: bytes) -> Any:
		...

	def close(self):
		...

class BaseReader(BufferedIOBase):
	def __init__(self, linker: "BaseLinker", size: int, transform: Optional[Transform] = None) -> None:
		self.linker = linker
		self._size = size
		self.transform = transform
		self._position = 0

	def __len__(self):
		return self._size

	def read(self, size: Optional[int] = None) -> bytes:
		tr = self.transform
		if size is None:
			size = self._size

		read_size = self._position
		ret = b""
		while read_size < size:
			res = self.linker.read_in(size)
			read_size += len(res)
			if tr:
				ret += bytes(tr(r) for r in res)
			else:
				ret += res

		self._position = read_size
		return ret

	def clear(self):
		if self._position < self.size:
			self.linker.read_in(self.size - self._position)


class BaseFlashable:
	can_flash = True
	can_erase = True
	name: ClassVar[str]

	def flash(self, stream: BinaryIO, *, erase: bool = True):
		""" Flash a ROM to the card """
		raise NotImplementedError

	def verify(self, stream: BinaryIO) -> bool:
		""" Verify the ROM on the card is correct """
		stream.seek(0, SEEK_SET)
		buff1 = stream.read()
		buff2 = BytesIO()
		self.dump(buff2)
		return buff1 == buff2.read()

	def dump(self, stream: BinaryIO, *, offset: int = 0, size: int = 0):
		""" Dump a ROM from the card """
		raise NotImplementedError

	def erase(self, *, offset: int = 0, size: int = 0):
		""" Erase the contents of the card """
		raise NotImplementedError

	def read(self, size: int) -> bytes:
		""" Read from the cursor location """
		raise NotImplementedError

	def write(self, data: bytes):
		""" Write to the cursor location """
		raise NotImplementedError

	def seek(self, offset: int, whence: int = SEEK_SET) -> int:
		""" Adjust cursor position """
		raise NotImplementedError
