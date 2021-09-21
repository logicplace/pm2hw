from math import ceil
from time import sleep, time
from typing import Optional, Tuple
from functools import lru_cache

from .base import BaseFtdiFlasher, BaseLinker, BaseSstCard, BytesOrSequence, BytesOrTransformer, Transform, linkers
from .logger import protocol_data
from .exceptions import DeviceError, DeviceNotSupportedError

DEV_DESC = b"Dual RS232-HS B"  # "FT2232H MiniModule A"

class PokeFlash(BaseFtdiFlasher):
	name = "PokeFlash"
	clock_divisor = 0

	PWR = BaseFtdiFlasher.GPIOL1
	PWR_READ = BaseFtdiFlasher.GPIOL3

	ftdi_port_state = PWR | BaseFtdiFlasher.TMS_CS
	ftdi_port_direction = PWR | BaseFtdiFlasher.ftdi_port_direction

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

	def detect_card(self):
		""" Detect which card is connected """
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

# TODO: Would be good to separate v1 and v2 ?
class PokeCard512(BaseSstCard):
	memory = 512 * 1024
	block_size = 8 * 1024

	def __init__(self, linker: BaseLinker):
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
		data = self.read_data(0, 4)
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

	def read_data(self, addr: int, size: int):
		assert size <= self.block_size
		return self.linker.read(
			b"".join(
				self.prepare_read_packet(a)
				for a in range(addr, addr + size)
			),
			size
		).read()

	# Chip commands
	T_BP = 23.46e-6  # μs
	T_IDA = 150e-9  # ns
	T_SCE = 0.100  # ms

	def sst_sector_erase(self, addr: int):
		self.linker.write(
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

linkers[DEV_DESC] = PokeFlash
