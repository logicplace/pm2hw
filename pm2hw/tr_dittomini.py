import struct
from time import sleep, time
from typing import BinaryIO, NamedTuple

import ftd2xx
from ftd2xx.defines import OPEN_BY_DESCRIPTION

from .base import BaseOriginal
from .logger import protocol_data, verbose
from .exceptions import clarify, DeviceError, DeviceNotSupportedError

DEV_DESC = b"Dual RS232 A"
# DEV_DESC = b"USB SerialConverter A"
# DEV_DESC = b"FT2232H MiniModule A"

BLOCKSIZE = (64*1024)  # We read/write chunks of 64kb to the cart
N_WAIT_CYCLES = 2  # How many wait cycles for byte programming / needed check !!! / ?

FTDI_PORT_DIRECTION = 0x1b
POWER_OFF_MASK = 0x10
POWER_ON_MASK = ~POWER_OFF_MASK & 0xff
PROG_OFF_MASK = 0x08
PROG_ON_MASK = ~PROG_OFF_MASK & 0xff

def bit_reverse(x):
	# return int(bin(x)[:1:-1], 2)
	x = ((x >> 1) & 0x55) | ((x << 1) & 0xaa)
	x = ((x >> 2) & 0x33) | ((x << 2) & 0xcc)
	x = ((x >> 4) & 0x0f) | ((x << 4) & 0xf0)
	return x

class CFIBlockRegion(NamedTuple):
	n_blocks: int
	block_size: int

	@classmethod
	def decode(cls, raw):
		return cls(*struct.unpack("<HH", raw))

	@staticmethod
	def size():
		return 4

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

class DittoMini(BaseOriginal):
	clock_divisor = 1
	ftdi_port_state = 0x18
	block_size = 999999999999999

	def __init__(self, clock_divisor: int = 1):
		assert 1 <= clock_divisor <= 100
		self.clock_divisor = clock_divisor

		self._open()

		manuf, devc, devcex = self.flash_getdevice()
		self.manuf = manuf
		self.devc = devc
		self.devcex = devcex

		if manuf != 0xbf or devc != 0xc8:
			self.power_off()
			raise DeviceNotSupportedError(manuf, devc, devcex)

		self.read_cfi_query_struct()
		verbose("Flash chip ready")

		self.chip = "SST39VF1681"
		self.memory = (1 << self.cfiqs.device_size)

	def _open(self):
		with clarify("Failed opening the device!"):
			# TODO: this is Windows-only, fix
			self.handle = handle = ftd2xx.openEx(DEV_DESC, OPEN_BY_DESCRIPTION)

		handle.setTimeouts(10000, 10000)

		with clarify("Unable to reset device"):
			handle.resetDevice()

		with clarify("Unable to reset event/error chars"):
			handle.setChars(0, 0, 0, 0)

		# Setup latency
		with clarify("Set USB Device Latency Timer failed!"):
			handle.setLatencyTimer(255)

		# Reset controller
		with clarify("Device reset failed!"):
			handle.setBitMode(0x0, 0x0)

		# Set the port to MPSSE mode
		with clarify("Set to MPSSE mode failed!"):
			handle.setBitMode(0x0, 0x2)

		# Check sync...
		with clarify("Unable to synchronise the MPSSE write/read cycle!"):
			self.sync_to_mpsse()

		# Device Pins Setup
		#  Bit 0 = CLK          (Out)
		#  Bit 1 = DO           (Out)
		#  Bit 2 = DI           (In)
		#  Bit 3 = CS           (Out)
		#    GPIO...
		#  Bit 4 = POWER_CTRL   (Out) <- Active low
		#  Bit 5 = none         (In)
		#  Bit 6 = none         (In)
		#  Bit 7 = IS_POWER_ON  (In)
		
		# initialise the port direction

		# ADBUS0 TCK/SK  output  1
		# ADBUS1 TDI/DO  output  1
		# ADBUS2 TDO/DI  input   0
		# ADBUS3 TMS/CS  output  1
		# ADBUS4 POWER   output  1
		# ADBUS5 GPIOL1  input   0
		# ADBUS6 GPIOL2  input   0
		# ADBUS7 ISPOWER input   0

		self.power_on()
		sleep(0.010)
		assert handle.getQueueStatus() == 0

	def program(self, stream: BinaryIO, size: int):
		for base in range(0, size, BLOCKSIZE):
			read = stream.read(BLOCKSIZE)
			buf = b"".join(
				self.flash_writebyte(base + i, b)
				for i, b in enumerate(read)
			)
			self.write_out(buf)

	def erase(self, size: int):
		if size > 0x40000:
			# File is >256kb - do chip erase
			start = time()
			self.flash_chiperase()
			while self.read_cart(0, 1) != b'\xff' and time() - start < 20:
				pass
		else:
			# File is <256kb - erase each sector to save time
			self._sec_erase(size, 0x00000)  # Erase lower 16kb - boot block
			self._sec_erase(size, 0x04000)  # Erase parameter block 1
			self._sec_erase(size, 0x06000)  # Erase parameter block 2
			self._sec_erase(size, 0x08000)  # Erase memory block 1
			self._sec_erase(size, 0x10000)  # Erase memory block 2
			self._sec_erase(size, 0x20000)  # Erase memory block 3
			self._sec_erase(size, 0x30000)  # Erase memory block 4

	def _sec_erase(self, size: int, addr: int):
		if size > addr:
			start = time()
			self.flash_secerase(addr)
			while self.read_cart(addr, 1) != 0xff and time() - start < 5:
				pass

	def write(self, data: bytes):
		protocol_data(">", data)
		self.handle.write(data)

	def read_in(self, addr: int, size: int):
		# Wait time... why? don't know.
		self.cs_high()
		sleep(0.25)
		self.cs_low()
		return self.read_cart(addr, size, reverse=True)#, b"\x2c")

	def __del__(self):
		# Cleanup & End
		if hasattr(self, "handle"):
			sleep(0.2)
			self.cs_high()
			sleep(0.2)

			self.power_off()
			sleep(0.2)
			self.handle.close()

	def set_speed(self, speed):
		# NOTE: Same as pokecard
		assert 0 <= speed <= 0xff
		self.write(bytes([
			0x86,  # set clock divider command to 1MHz
			speed,  # low byte    60MHz / ((value+1)*2)
			0x00  # high byte
		]))

	def impart_state(self):
		# 0x80,  Set Byte to ADBUS
		# 0xValue,
		# 0xDirection  1 - OUTPUT !!!! 0 - INPUT
		self.write(bytes([
			0x80,
			self.ftdi_port_state,
			FTDI_PORT_DIRECTION
		]))

	def cs_low(self):
		self.ftdi_port_state &= PROG_ON_MASK
		self.impart_state()

	def cs_high(self):
		self.ftdi_port_state |= PROG_OFF_MASK
		self.impart_state()

	def power_on(self):
		if self.ftdi_port_state & POWER_OFF_MASK:
			self.ftdi_port_state |= PROG_OFF_MASK
			self.ftdi_port_state &= POWER_ON_MASK
			self.impart_state()
			self.impart_state()
			self.cs_low()

	def power_off(self):
		if not (self.ftdi_port_state & POWER_OFF_MASK):
			self.ftdi_port_state |= POWER_OFF_MASK
			self.impart_state()

	def sync_to_mpsse(self):
		handle = self.handle

		# uses &HAA and &HAB commands which are invalid so that the MPSSE processor should
		# echo these back to use preceded with &HFA

		# clear anything in the input buffer
		num_bytes = handle.getQueueStatus()
		while num_bytes:
			# read chunks of 'input buffer size'
			tmp = handle.read(BLOCKSIZE)
			protocol_data("<", tmp)
			num_bytes -= len(tmp)

		# Sync with MPSSE
		#
		# If a bad command is detected, the MPSSE returns the value 0xFA, followed by
		# the byte that caused the bad command.Use of the bad command detection is
		# the recommended method of determining whether the MPSSE is in sync with the
		# application program.  By sending a bad command on purpose and looking for
		# 0xFA, the application can determine whether communication with the MPSSE is
		# possible.
		#

		# Enable loopback
		self.write(b"\x84")
		assert handle.getQueueStatus() == 0

		# put a bad command to the command processor
		# Send 0xAA
		self.write(b"\xab")

		# wait for a response
		self.wait_for(2)

		# read the input queue
		dat_buffer = handle.read(2)
		protocol_data("<", dat_buffer)

		if dat_buffer != b"\xfa\xab":
			raise DeviceError("MPSSE Sync Failed")

		# Disable loopback
		self.write(b"\x85")
		assert handle.getQueueStatus() == 0

		# My FTDI device doesn't support the following commands
		# TODO: Try doing a version/feature check and enable them conditionally

		# self.write(
		# 	b"\x8a",  # Use 60MHz master clock (disable divide by 5)
		# 	b"\x97",  # Turn off adaptive clocking
		# 	b"\x8d",  # Disable three phase clocking
		# )
		# assert handle.getQueueStatus() == 0

		# Set TCK/SK Clock divisor
		# TODO: This is different if divide by 5 was disabled (60Mhz)
		# TCK/SK period = 12MHz  /  (( 1 +[ (0xValueH * 256) OR 0xValueL] ) * 2)
		# For 3MHz: 0x0000
		self.write(bytes([
			0x86,  # Command
			self.clock_divisor,  # ValueL
			0x00  # ValueH
		]))
		# PoMi wrote 0x85, 0x8a too
		assert handle.getQueueStatus() == 0

		sleep(0.010)

	def read_cfi_query_struct(self):
		cfiqs, block_regions = self.flash_cfiquerymode()
		assert cfiqs.number_of_erase_block_regions > 0

		for block_region in block_regions:
			current_size = block_region.block_size << 8;
			if current_size < self.block_size:
				self.block_size = current_size

		self.cfiqs = cfiqs
		self.block_regions = block_regions

		# TODO: Debug logging
		# TODO: Dump the rest of the fields
		size_bytes = 1 << cfiqs.device_size
		verbose("Flash CFI Magic Header: {}", cfiqs.magic_qry.decode())
		verbose("Flash CFI Reported device size: {:d} bytes ({:d} MiB)", size_bytes, size_bytes // 1024 ** 2)
		verbose("Number of block regions: {:d}", cfiqs.number_of_erase_block_regions)
		for i, block_region in enumerate(block_regions):
			verbose("  Block region #{:d}", i+1)
			verbose("    Block size: {:d} bytes", block_region.block_size << 8)
			verbose("    Blocks in region: {:d}", block_region.n_blocks + 1)
		verbose("Using block size: {:d} bytes", self.block_size)

	def flash_reset(self):
		# NOTE: Same command as pokecard except no conv
		self.write_aa55xx(0xf0)

	def flash_getdevice(self):
		# NOTE: Same command as pokecard except no conv or wait
		buf = self.prep_aa55xx(0x90)
		tmp = self.read_cart(0x0, 4, pfx=buf)
		self.flash_reset()
		# Manufacturer, Device ID, Device Code EX
		return tmp[0], tmp[1], tmp[3]

	def flash_writebyte(self, addr: int, data: int):
		if data == 0xff: return b""
		buf = self.prep_aa55xx(0xa0)
		buf += self.prepare_cart(addr, bit_reverse(data))
		buf += self.prepare_wait(N_WAIT_CYCLES)
		return buf

	def flash_chiperase(self):
		# NOTE: Same command as pokecard except no conv
		buf = self.prep_aa55xx(0x80)
		self.write_aa55xx(0x10, pfx=buf)

	def flash_secerase(self, addr: int):
		# NOTE: Same command as pokecard except no conv
		buf = self.prep_aa55xx(0x80)
		self.write_aa55xx(0x30, addr=addr, pfx=buf)

	def flash_blockerase(self, addr: int):
		buf = self.prep_aa55xx(0x80)
		self.write_aa55xx(0x50, addr=addr, pfx=buf)

	def flash_cfiquerymode(self):
		buf = self.prep_aa55xx(0x98)
		cfiqs = CFIQueryStruct.decode(self.read_cart(0x10, CFIQueryStruct.size(), pfx=buf))
		block_size = CFIBlockRegion.size()
		raw_size = block_size * cfiqs.number_of_erase_block_regions
		raw = self.read_cart(0x2d, raw_size)
		self.flash_reset()
		block_regions = tuple(
			CFIBlockRegion.decode(raw[start:end])
			for start, end in zip(
				range(0, raw_size, block_size),
				range(block_size, raw_size + block_size, block_size)
			)
		)
		return cfiqs, block_regions

	@staticmethod
	def prepare_cart(addr: int, dat: int):
		assert 0 <= dat <= 0xff
		return bytes([
			# Send 4 Bytes
			0x11, 0x03, 0x00,

			# Layout:
			#    2 1111 1111 1100 000000000   0000 0000
			#    0 9876 5432 1098 7654 3210   7654 3210
			# CxxA AAAA AAAA AAAA AAAA AAAA | DDDD DDDD
			((addr >> 16) & 0x1f) | 0x80,
			(addr >> 8) & 0xff,
			(addr & 0xff),
			dat
		])

	PREP_AA = prepare_cart.__func__(0xAAA, 0xaa)
	PREP_55 = prepare_cart.__func__(0x555, 0x55)

	BUFF_AA55 = PREP_AA + PREP_55

	def prepare_wait(self, waitcycles: int):
		# CS high  
		#   cmdBuffer = b"\x80\x08\x0b"

		# wait
		#   cmdBuffer = bytes([0x8f, waitcycles, 0x00])

		# CS low setzen
		return b''
		assert 0 <= waitcycles <= 0xff
		self.ftdi_port_state &= PROG_ON_MASK
		return bytes([
			0x80,
			self.ftdi_port_state,
			FTDI_PORT_DIRECTION
		]) * 4

	def prep_aa55xx(self, dat: int, waitcycles: int = 0, *, addr: int = 0xAAA):
		prep_dat = self.prepare_cart(addr, dat)
		if waitcycles:
			wb = self.prepare_wait(waitcycles)
			return self.PREP_AA + wb + self.PREP_55 + wb + prep_dat + wb
		return self.BUFF_AA55 + prep_dat

	def read_queued(self):
		# NOTE: Same as pokecard but was not used for pokecard
		size = self.handle.getQueueStatus()
		ret = self.handle.read(size)
		protocol_data("<", ret)
		return ret

	def write_out(self, buffer: bytes):
		# NOTE: Same as pokecard
		self.write(buffer + b"\x87")

	def write_aa55xx(self, dat: int, waitcycles: int = 0, *, addr: int = 0xAAA, pfx: bytes = b""):
		# NOTE: Same as pokecard
		self.write_out(pfx + self.prep_aa55xx(dat, waitcycles, addr=addr))

	def read_cart(self, addr: int, n_bytes: int, *, pfx: bytes = b"", reverse = False):
		# Read bytes from the cart
		if n_bytes <= 0: return b""

		self.cs_low()
		sleep(0.001)  # TODO: clock divisor?
		self.read_queued()

		buffer = bytearray(
			# Clock Data Bytes Out on -ve clock edge MSB first  (no read)
			b"\x11\x02\x00"
			# Placeholder for address
			b"\0\0\0"
			# Clock Data Bytes In on -ve clock edge MSB first (no write)
			b"\x24\x00\x00"
		)
		size_per_req = len(buffer)
		buffer *= n_bytes

		for pos in range(3, len(buffer), size_per_req):
			# Layout:
			#    2 1111 1111 1100 000000000   0000 0000
			#    0 9876 5432 1098 7654 3210   7654 3210
			# CxxA AAAA AAAA AAAA AAAA AAAA | DDDD DDDD
	
			buffer[pos:pos + 3] = (addr & 0x1fffff).to_bytes(3, "big")
			addr += 1

		# It seems that until I read from the device, the buffer keeps filling
		# and when it's full, the write fails.
		# The buffer is quite small so read requests need to be splitted

		read_size = 256
		read_request_size = read_size * size_per_req

		dat_buffer = b""
		buffer = pfx + buffer
		for start, size, end in zip(
			range(0, len(buffer), read_request_size),
			(read_size,) * (n_bytes // read_size) + (n_bytes % read_size,),
			range(read_request_size, len(buffer) + read_request_size, read_request_size)
		):
			# Send all bytes
			self.write_out(buffer[start:end])

			# wait for data to become available
			self.wait_for(size)

			# read the input queue
			tmp = self.handle.read(size)
			protocol_data("<", tmp)
			if reverse:
				dat_buffer += bytes(bit_reverse(x) for x in tmp)
			else:
				dat_buffer += tmp

		return dat_buffer

	def wait_for(self, want_bytes: int, secs: float = 20):
		handle = self.handle
		start = time()
		while handle.getQueueStatus() < want_bytes and time() - start < secs:
			pass
		queued = handle.getQueueStatus()
		if queued > want_bytes:
			raise DeviceError(
				"Device queued an unexpected amount of data."
				" Wanted {} but queued {}".format(want_bytes, queued))
		if queued != want_bytes:
			raise DeviceError(
				"Device took too long to queue data."
				" Wanted {} but queued {}".format(want_bytes, queued))
