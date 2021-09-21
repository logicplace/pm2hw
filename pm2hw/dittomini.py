import struct
from typing import NamedTuple, Optional

from .base import BaseFtdiFlasher, BaseLinker, BaseReader, BaseSstCard, BytesOrTransformer, Transform, linkers
from .logger import verbose
from .exceptions import DeviceNotSupportedError

DEV_DESC = b"Dual RS232 A"
# DEV_DESC = b"USB SerialConverter A"
# DEV_DESC = b"FT2232H MiniModule A"

class CFIBlockRegion(NamedTuple):
	n_blocks: int
	block_size: int

	@classmethod
	def decode(cls, raw):
		return cls(*struct.unpack("<HH", raw))

	@staticmethod
	def size():
		return 4

	def get_size(self):
		return self.block_size << 8

class CFIQueryStruct(NamedTuple):
	magic_qry: bytes                           # "QRY"
	control_interface_id: int                  # (See JEP137)
	primary_algorithm_extended_table: int      # 0 = No extended table
	alternative_control_interface_id: int      # 0 = No Alt. Control Id
	alternative_algorithm_extended_table: int  # 0 = No Alt. extended table

	vcc_min: int              # BCD Volts: BCD 100mv
	vcc_max: int              # BCD Volts: BCD 100mv
	vpp_min: int              # Volts: BCD 100mv
	vpp_max: int              # Volts: BCD 100mv
	typical_timeouts: bytes  # (See JESD68-01)

	device_size: int                         # 2^n bytes
	interface_code_description: int          # (See JEP137)
	maximum_bytes_in_multibyte_program: int  # 2^n bytes
	number_of_erase_block_regions: int

	@classmethod
	def decode(cls, raw):
		res = cls(*struct.unpack("<3s4H4B8sBHHB", raw))
		assert res.magic_qry.decode() == "QRY"
		return res

	@staticmethod
	def size():
		return 29

	def get_size(self):
		return 1 << self.device_size

class DittoFlash(BaseFtdiFlasher):
	name = "DittoFlash"
	clock_divisor = 1

	PWR = BaseFtdiFlasher.GPIOL0
	PWR_READ = BaseFtdiFlasher.GPIOL3

	ftdi_port_state = BaseFtdiFlasher.TMS_CS
	ftdi_port_direction = PWR | BaseFtdiFlasher.ftdi_port_direction

	def init(self):
		super().init()

		# Set CS to low, start programming operation
		self.port_state(0)

	def cleanup(self):
		self.port_state(on=self.PWR)

	def detect_card(self):
		""" Detect which card is connected """
		self.card = card = DittoMiniRev3(self)
		card.get_device_info()
		return card

	# def read(self, data: BytesOrSequence, size: int, *, wait: int = 0, transform: Optional[Transform] = None):
	# 	""" Write commands to the card and read the response """
	# 	self.write(data, wait=wait)
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
		if secs == DittoMiniRev3.T_BP:
			cmd = bytes([0x80, self.ftdi_port_state, self.ftdi_port_direction])
			return cmd * 4
		return b""

# There is no Rev 1 or 2, though
class DittoMiniRev3(BaseSstCard):
	def __init__(self, linker: BaseLinker):
		super().__init__(linker)
		self.buffer_sdp = (
			self.prepare_write_packet(0xAAA, 0xaa)
			+ self.prepare_write_packet(0x555, 0x55)
		)

	def get_device_info(self):
		self.sst_software_id_entry()
		manuf, devc, _, devcex = self.read_info(0, 4)
		self.sst_exit()

		if (manuf, devc) == (0xbf, 0xc8):
			# http://ww1.microchip.com/downloads/en/devicedoc/25040a.pdf
			# TODO: does devcex indicate SST39VF1681 vs SST39VF1682?
			self.chip = "SST39VF1681"
			# wait time for byte_program: <=10 μs
			self.read_cfi_query_struct()

			self.erase_modes = (
				(self.sst_sector_erase, 4 * 1024, 0.025),
				(self.sst_block_erase, 64 * 1024, 0.025),
				(self.sst_chip_erase, self.memory, 0.050)
			)
		else:
			raise DeviceNotSupportedError(manuf, devc, devcex)

		return manuf, devc, devcex

	def read_cfi_query_struct(self):
		# Retrieve information
		self.sst_cfi_query_entry()
		cfiqs_size = CFIQueryStruct.size()
		cfiqs = CFIQueryStruct.decode(self.read_info(0x10, cfiqs_size))
		assert cfiqs.number_of_erase_block_regions > 0
		block_size = CFIBlockRegion.size()
		raw_size = block_size * cfiqs.number_of_erase_block_regions
		raw = self.read_info(0x10 + cfiqs_size, raw_size)
		self.sst_exit()
		block_regions = tuple(
			CFIBlockRegion.decode(raw[start:end])
			for start, end in zip(
				range(0, raw_size, block_size),
				range(block_size, raw_size + block_size, block_size)
			)
		)

		self.memory = size_bytes = cfiqs.get_size()
		self.block_size = max(block_regions, key=lambda x: x.block_size).get_size()

		self.cfiqs = cfiqs
		self.block_regions = block_regions

		# TODO: Dump the rest of the fields
		verbose("Flash CFI Magic Header: {}", cfiqs.magic_qry.decode())
		verbose("Flash CFI Reported device size: {:d} bytes ({:d} MiB)", size_bytes, size_bytes // 1024 ** 2)
		verbose("Number of block regions: {:d}", cfiqs.number_of_erase_block_regions)
		for i, block_region in enumerate(block_regions):
			verbose("  Block region #{:d}", i+1)
			verbose("    Block size: {:d} bytes", block_region.get_size())
			verbose("    Blocks in region: {:d}", block_region.n_blocks + 1)
		verbose("Using block size: {:d} bytes", self.block_size)

	def prepare_sdp_prefixed(self, data: int, addr: int = 0xAAA):
		return super().prepare_sdp_prefixed(data, addr)

	def deconstruct_packet(self, packet: bytes):
		# Layout:
		#    2 1111 1111 1100 000000000   0000 0000
		#    0 9876 5432 1098 7654 3210   7654 3210
		# CxxA AAAA AAAA AAAA AAAA AAAA | DDDD DDDD
		x = int.from_bytes(packet[:4], "big", signed=False)
		return (x & 0x1fffff00) >> 8, (x & 0xff)

	@staticmethod
	def prepare_write_packet(addr: int, data: int):
		return (
			# Layout: CxxA AAAA AAAA AAAA AAAA AAAA DDDD DDDD
			0x80000000  # Write indicator
			| ((addr & 0x1fffff) << 8)
			| (data & 0xff)
		).to_bytes(4, "big")

	@staticmethod
	def prepare_read_packet(addr: int):
		return (
			((addr & 0x1fffff) << 8)
		).to_bytes(4, "big")

	def read_info(self, addr: int, size: int):
		reader: BaseReader = self.linker.read(
			b"".join(
				self.prepare_read_packet(a)
				for a in range(addr, addr + size)
			),
			size,
		)
		return reader.read()

	def read_data(self, addr: int, size: int):
		assert size <= self.block_size
		read_size = 512
		end = addr + size
		return b"".join(
			self.linker.read(
				b"".join(
					self.prepare_read_packet(a)
					for a in range(a, a + s)
				),
				s,
				transform=self.linker.lsb_first
			).read()
			for a, s in zip(
				range(addr, end, read_size),
				[read_size] * (size // read_size) + [size % read_size or read_size]
			)
		)

	# def write_data(self, addr: int, data: bytes):
	# 	size = len(data)
	# 	assert size <= self.block_size
	# 	return self.linker.write(
	# 		(
	# 			lambda tr: self.prepare_write_packet(a, tr(d))
	# 			for a, d in zip(range(addr, addr + size), data)
	# 		),
	# 		transform=self.linker.lsb_first
	# 	)

	# Chip commands
	T_BP = 10e-6  # μs
	T_IDA = 160e-9  # ns
	T_SCE = 0.050  # ms

	def sst_byte_program(self, addr: int, data: int):
		super().sst_byte_program(addr, self.linker.lsb_first(data))

	def sst_sector_erase(self, addr: int):
		self.linker.write(
			self.prepare_sdp_prefixed(0x80),
			+ self.prepare_sdp_prefixed(0x50, addr),
			wait=0.025  # ms
		)

	def sst_block_erase(self, addr: int):
		self.linker.write(
			self.prepare_sdp_prefixed(0x80),
			+ self.prepare_sdp_prefixed(0x30, addr),
			wait=0.025  # ms
		)

	def sst_erase_suspend(self):
		self.linker.write(
			self.prepare_write_packet(0, 0xb0),
			wait=20e-6  # μs
		)

	def sst_erase_resume(self):
		self.linker.write(
			self.prepare_write_packet(0, 0x30)
		)

	def sst_query_sec_id(self):
		self.linker.write(
			self.prepare_sdp_prefixed(0x88),
			wait=self.T_IDA
		)

	def sst_user_security_id_byte_program(self, addr: int, data: int):
		assert 0x00 <= addr <= 0x0f or 0x20 <= addr <= 0x2f
		self.linker.write(
			self.prepare_sdp_prefixed(0xa5),
			self.prepare_write_packet(addr, data),
			wait=self.T_BP
		)

	def sst_user_security_id_program_lock_out(self):
		""" Warning: this is PERMANENT (probably?) """
		self.linker.write(
			self.prepare_sdp_prefixed(0x85),
			self.prepare_write_packet(0, 0),
			wait=self.T_BP
		)

	def sst_cfi_query_entry(self):
		self.linker.write(
			self.prepare_sdp_prefixed(0x98),
			wait=self.T_IDA
		)
	
linkers[DEV_DESC] = DittoFlash
