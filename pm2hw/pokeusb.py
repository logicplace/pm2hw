import sys
from os import SEEK_SET, SEEK_CUR, SEEK_END
from time import sleep
from typing import BinaryIO

from usb.util import CTRL_TYPE_VENDOR, CTRL_RECIPIENT_DEVICE, CTRL_IN, CTRL_OUT

from .base import BaseLinker, linkers, UsbDevice
from .logger import debug, log, warn
from .exceptions import DeviceError

DEV_ID = (0x1337, 0x12AB)
DEV_MANUFACTURER = "lupin.shizzle.it"
DEV_PRODUCT = "PokeUSB"


# TODO: test any of this


REQ_TYPE_IN = CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_IN
REQ_TYPE_OUT = CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT


class PokeUSB(BaseLinker):
	name = "PokeUSB"
	handle: UsbDevice
	_cursor = 0

	@classmethod
	def from_usb(cls, device: UsbDevice) -> "BaseLinker":
		device.setup()
		if device.manufacturer == DEV_MANUFACTURER:
			if device.product == DEV_PRODUCT:
				return cls(device)

	def init(self):
		self.cmd_abort()
		return self

	def cleanup(self):
		self.cmd_abort()

	def flash(self, stream: BinaryIO):
		self.cmd_init_process("flash")

		wrote = 0
		while True:
			data = stream.read(220)
			if not len(data):
				break
			self.cmd_flashdata(data)
			wrote += len(data)

		log("Write finished.. wrote {size} bytes", size=wrote)
		self.cmd_finish_process("flash")

	def dump(self, stream: BinaryIO, size: int = 512 * 1024):
		self.cmd_init_process("dump")

		for c in range(0, size, 220):
			data = self.cmd_read_block(min(220, size - c))
			stream.write(data)
		
		log("Cart dump finished!")
		self.cmd_finish_process("dump")
	
	def erase(self):
		log("Erasing cart... (10 seconds)")
		self.cmd_erase()
		sleep(10)
		self.cmd_finish_process("erase")
		log("Erasing finished!")

	def read(self, size: int):
		addr = self._cursor
		self._cursor += size
		return bytes(self.cmd_readbyte(a) for a in range(addr, addr + size))

	# Arbitrary write not possible

	def seek(self, offset: int, whence: int = SEEK_SET):
		if whence == SEEK_SET:
			self._cursor = offset
		elif whence == SEEK_CUR:
			self._cursor += offset
		elif whence == SEEK_END:
			raise NotImplementedError("SEEK_END")
		else:
			raise ValueError("whence must be one of: SEEK_SET, SEEK_CUR, or SEEK_END")

	def get_cart_info(self):
		self.seek(0x02100)
		mn = self.read(2)
		self.seek(0x021A4)
		nintendo = self.read_from(8)
		cid = self.read_from(4)
		name = self.read_from(12)

		if mn == "MN":
			debug("Cart appears to contain a valid ROM.")
		else:
			warn("Cart might not contain a valid ROM.")

		log(
			"ROM name: {name}"
			"\nManufacturer ID {id}"
			"\nNintendo identifier: {nintendo}",
			name=name,
			id=cid,
			nintendo=nintendo
		)

		return cid, name

	# Commands
	def cmd_init_process(self, process: str):
		res = self.handle.ctrl_transfer(REQ_TYPE_IN, 0, 0, 0, 1, 500)
		if res[0] != 0x1a:
			raise DeviceError("failed starting {} process - Cart removed?".format(process))

	def cmd_finish_process(self, process: str):
		res = self.handle.ctrl_transfer(REQ_TYPE_IN, 1, 0, 0, 1, 500)
		if res[0] != 0x1a:
			raise DeviceError("failed finishing {} process - Cart removed?".format(process))
	
	def cmd_erase(self):
		res = self.handle.ctrl_transfer(REQ_TYPE_IN, 2, 0, 0, 1, 500)
		if res[0] != 0x1a:
			raise DeviceError("failed starting erasing process - Cart removed?")
	
	def cmd_flashdata(self, data: bytes):
		self.handle.ctrl_transfer(REQ_TYPE_OUT, 3, 0, 0, data, 5000)

	def cmd_read_block(self, size: int):
		return self.handle.ctrl_transfer(REQ_TYPE_IN, 4, 0, 0, size, 5000)

	def cmd_manufacturer(self):
		# TODO: unimplemented in pmusb, only bRequest known
		return self.handle.ctrl_transfer(REQ_TYPE_IN, 5, 0, 0, 1, 500)

	def cmd_devicecode(self):
		# TODO: unimplemented in pmusb, only bRequest known
		return self.handle.ctrl_transfer(REQ_TYPE_IN, 6, 0, 0, 1, 500)

	def cmd_readbyte(self, addr: int):
		return self.handle.ctrl_transfer(REQ_TYPE_IN, 7, (addr>>16), (addr&0xFFFF), 1, 750)

	def cmd_ping(self):
		# TODO: unimplemented in pmusb, only bRequest known
		return self.handle.ctrl_transfer(REQ_TYPE_IN, 8, 0, 0, 1, 500)

	def cmd_abort(self):
		self.handle.ctrl_transfer(REQ_TYPE_IN, 128)

linkers[DEV_ID] = PokeUSB
