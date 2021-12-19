import struct
from typing import TYPE_CHECKING, NamedTuple

from .base import dummy_progress
from .base_sst import BaseSstCard
from ..base import BaseReader
from ..logger import progress, verbose
from ..locales import natural_size
from ..exceptions import DeviceNotSupportedError

if TYPE_CHECKING:
	from ..linkers.base import BaseLinker

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
	typical_timeouts: bytes   # (See JESD68-01)

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

# There is no Rev 1 or 2, though
class DittoMiniRev3(BaseSstCard):
	name = "DITTO mini"

	def __init__(self, linker: "BaseLinker"):
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

		# TODO: make this configurable?
		self.block_size = min(block_regions, key=lambda x: x.block_size).get_size()

		self.cfiqs = cfiqs
		self.block_regions = block_regions

		# TODO: Dump the rest of the fields
		verbose("Flash CFI Magic Header: {header}", header=cfiqs.magic_qry.decode())
		verbose(
			"Flash CFI Reported device size: {bytes:d} bytes ({size})",
			bytes=size_bytes, size=natural_size(size_bytes))
		verbose("Number of block regions: {br:d}", br=cfiqs.number_of_erase_block_regions)
		for i, block_region in enumerate(block_regions):
			verbose("  Block region #{i:d}", i=i+1)
			verbose("    Block size: {bytes:d} bytes", bytes=block_region.get_size())
			verbose("    Blocks in region: {blocks:d}", blocks=block_region.n_blocks + 1)
		verbose("Using block size: {bytes:d} bytes", bytes=self.block_size)

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
		reader: BaseReader = self.linker.read_data(
			b"".join(
				self.prepare_read_packet(a)
				for a in range(addr, addr + size)
			),
			size,
		)
		return reader.read()

	def read_data(self, addr: int, size: int, *, prog: progress = dummy_progress):
		for start, bsize in self.blocks(addr, size):
			read_size = 512
			end = start + bsize
			ret = b"".join(
				self.linker.read_data(
					b"".join(
						self.prepare_read_packet(a)
						for a in range(a, a + s)
					),
					s,
					transform=self.linker.lsb_first
				).read()
				for a, s in zip(
					range(start, end, read_size),
					[read_size] * (bsize // read_size) + [bsize % read_size or read_size]
				)
			)
			prog.add(bsize)
			yield ret

	# def write_data(self, addr: int, data: bytes, *, prog: progress = dummy_progress):
	# 	for (start, bsize), block in zip(
	# 		self.blocks(addr, len(data)),
	# 		chunked(self.block_size, data)
	# 	):
	# 		ret = self.linker.send(
	# 			(
	# 				lambda tr: self.prepare_write_packet(a, tr(d))
	# 				for a, d in zip(range(start, start + bsize), block)
	# 			),
	# 			transform=self.linker.lsb_first
	# 		)
	# 		prog.add(bsize)
	# 		yield ret

	# Chip commands
	T_BP = 10e-6  # μs
	T_IDA = 160e-9  # ns
	T_SCE = 0.050  # ms

	def sst_byte_program(self, addr: int, data: int):
		super().sst_byte_program(addr, self.linker.lsb_first(data))

	def sst_sector_erase(self, addr: int):
		self.linker.send(
			self.prepare_sdp_prefixed(0x80)
			+ self.prepare_sdp_prefixed(0x50, addr),
			wait=0.025  # ms
		)

	def sst_block_erase(self, addr: int):
		self.linker.send(
			self.prepare_sdp_prefixed(0x80)
			+ self.prepare_sdp_prefixed(0x30, addr),
			wait=0.025  # ms
		)

	def sst_erase_suspend(self):
		self.linker.send(
			self.prepare_write_packet(0, 0xb0),
			wait=20e-6  # μs
		)

	def sst_erase_resume(self):
		self.linker.send(
			self.prepare_write_packet(0, 0x30)
		)

	def sst_query_sec_id(self):
		self.linker.send(
			self.prepare_sdp_prefixed(0x88),
			wait=self.T_IDA
		)

	def sst_user_security_id_byte_program(self, addr: int, data: int):
		assert 0x00 <= addr <= 0x0f or 0x20 <= addr <= 0x2f
		self.linker.send(
			self.prepare_sdp_prefixed(0xa5),
			self.prepare_write_packet(addr, data),
			wait=self.T_BP
		)

	def sst_user_security_id_program_lock_out(self):
		""" Warning: this is PERMANENT (probably?) """
		self.linker.send(
			self.prepare_sdp_prefixed(0x85),
			self.prepare_write_packet(0, 0),
			wait=self.T_BP
		)

	def sst_cfi_query_entry(self):
		self.linker.send(
			self.prepare_sdp_prefixed(0x98),
			wait=self.T_IDA
		)
	