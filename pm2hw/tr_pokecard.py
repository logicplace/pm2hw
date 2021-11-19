from time import sleep, time
from typing import BinaryIO
from itertools import islice
from contextlib import contextmanager

import ftd2xx
from ftd2xx.defines import OPEN_BY_DESCRIPTION

from .base import BaseCard, BaseOriginal
from .exceptions import DeviceError, DeviceNotSupportedError

DEV_DESC = b"Dual RS232-HS B"  # "FT2232H MiniModule A"

@contextmanager
def clarify(error_msg):
	try:
		yield
	except ftd2xx.DeviceError as err:
		raise DeviceError("{}: {}".format(error_msg, str(err))) from None
	except DeviceError:
		raise DeviceError(error_msg) from None

# listDevices is broken for whatever reason
# def num_devices():
# 	n = ftd2xx._ft.DWORD()
# 	ftd2xx.call_ft(
# 		ftd2xx._ft.FT_ListDevices,
# 		ftd2xx.c.byref(n),
# 		None,
# 		ftd2xx._ft.DWORD(ftd2xx.LIST_NUMBER_ONLY)
# 	)
# 	return n.value

class PokeCard(BaseOriginal):
	# Wait-states inserted after byte-programming
	# AT49BV040A - 30 to 50 us byte prog time               wait_cycles=26 (27,773us)
	# AM29LV040B - 9 us typical (300us max worst case)      wait_cycles=24 (25,6us)
	# SST39VF040 - 14 to 20 us byte prog time               wait_cycles=20 (21,333us)
	# Wait time is: wait_cycles*4*8*(1/30MHz) ~= wait_cycles*1us
	# But actual wait time is a bit more (maybe because of time for next shift operation?)
	wait_cycles = 32  # Default value

	# default clock divider (15 MHz)
	# programming with 30 MHz increases speed just a little, but with 15 MHz it should be more stable
	clock_divider = 1

	block_size = 8 * 1024

	def __init__(self, clock_divider: int = 1):
		assert 1 <= clock_divider <= 64
		self.clock_divider = clock_divider

		self._open()
		sleep(0.050)

		# Check the flash type
		self.write_out(prep_aa55xx(CONV_90))
		self.manuf = manuf = conv_byt_back(self.read_cart(0x0, 1)[0]);
		self.devc = devc = conv_byt_back(self.read_cart(0x1, 1)[0]);
		self.devcex = devcex = conv_byt_back(self.read_cart(0x3, 1)[0]);
		self.write_out(prep_aa55xx(CONV_F0))

		if (manuf, devc, devcex) == (0x1f, 0x13, 0x0f):
			self.chip = "Atmel AT49BV040A"
			self.memory = 512 * 1024
		elif (manuf, devc) == (0x01, 0x4f):
			self.chip = "AMD AM29LV040B"
			self.memory = 512 * 1024
		elif (manuf, devc) == (0xbf, 0xd7):
			self.chip = "SST39VF040"
			self.memory = 512 * 1024
		else:
			raise DeviceNotSupportedError(manuf, devc, devcex)

	def _open(self):
		with clarify("Failed opening the device!"):
			self.handle = handle = ftd2xx.openEx(DEV_DESC, OPEN_BY_DESCRIPTION)

		# Setup latency
		with clarify("Set USB Device Latency Timer failed!"):
			handle.setLatencyTimer(16)

		# Reset controller
		with clarify("Device reset failed!"):
			handle.setBitMode(0x0, 0x0)

		# Set the port to MPSSE mode
		with clarify("Set to MPSSE mode failed!"):
			handle.setBitMode(0x0, 0x2)

		# Check sync...
		with clarify("Unable to synchronise the MPSSE write/read cycle!"):
			self.sync_to_mpsse()

		# Config stuff
		#  Bit 0 = CLK
		#  Bit 1 = DO
		#  Bit 2 = DI
		#  Bit 3 = CS
		#  Bit 5 = PWR
		#  Bit 7 = PWR read
		
		# initialise the port
		cmd_buffer = bytes([
			# set the low byte
			0x80,  # Set data bits low byte command
			0x28,  # set CS=high, DI=low, DO=low, SK=low, PWR=high
			0x2b,  # CS=input, DI=input, DO=output, SK=output, PWR=output,

			# set the clock divider
			0x86,
			self.clock_divider,
			0x00,
			0x85,  # turn off loopback
			0x8a,  # turn off divider by 5
		])
		self.write_to(cmd_buffer)

		# now check if the cart is already powered (inside PM)
		self.write_to(b"\x81")

		# wait for data to become available
		self.wait_for(1)

		# read the input queue
		dat_buffer = self.read_from(1)

		if dat_buffer[0] & 0x80:
			raise DeviceError("Cart seems to be powered (VCC is on) - please turn off your PM!")

		# Set CS high and power on cart
		self.cs_high()
		sleep(0.010)
		# Set CS to low, start programming operation
		self.cs_low()

	def program(self, stream: BinaryIO, size: int):
		self.flash_unlockbyp()
		for base in range(0, size, self.block_size):
			read = stream.read(self.block_size)
			buf = b"".join(
				self.flash_writebyte(base + i, b)
				for i, b in enumerate(read)
			)
			self.write_out(buf)
		self.flash_resetbyp()

	def erase(self, size: int):
		# Chip erase or sector erase
		#self.cs_low()
		if (size > 0x40000 or (self.manuf, self.devc) == (0xbf, 0xd7)):
			# File is >256kb - do chip erase
			self.flash_chiperase()
			start = time()
			while self.read_cart(0, 1) != 0xff and time() - start < 20:
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
			self.flash_secerase(addr)
			start = time()
			while self.read_cart(addr, 1) != 0xff and time() - start < 5:
				pass

	def read_from(self, size: int) -> bytes:
		ret = self.handle.read(size)
		# print("<", *("{:02x}".format(b) for b in ret))
		return ret

	def write_to(self, data: bytes):
		# print(">", *("{:02x}".format(b) for b in data))
		self.handle.write(data)

	def read_in(self, addr: int, size: int) -> bytes:
		return self.read_cart(addr, size)

	def set_speed(self, speed):
		assert 0 <= speed <= 0xff
		self.write_to(bytes([
			0x86,  # set clock divider command to 1MHz
			speed,  # low byte    60MHz / ((value+1)*2)
			0x00  # high byte
		]))

	def cs_low(self):
		self.write_to(b"\x80\x00\x2b")

	def cs_high(self):
		self.write_to(b"\x80\x08\x2b")

	def power_off(self):
		self.write_to(b"\x80\x20\x2b")

	def sync_to_mpsse(self):
		handle = self.handle

		# uses &HAA and &HAB commands which are invalid so that the MPSSE processor should
		# echo these back to use preceded with &HFA

		# clear anything in the input buffer
		num_bytes = handle.getQueueStatus()
		while num_bytes:
			# read chunks of 'input buffer size'
			num_bytes -= len(self.read_from(self.block_size))

		# put a bad command to the command processor
		# Send 0xAA
		self.write_to(b"\xaa")

		# wait for a response
		self.wait_for(2)

		# read the input queue
		dat_buffer = self.read_from(2)

		if dat_buffer != b"\xfa\xaa":
			raise DeviceError

	def can_bypass(self):
		return self.manuf == 0x01 and self.devc == 0x4f

	def flash_unlockbyp(self):
		if self.can_bypass():
			self.write_aa55xx(CONV_20)

	def flash_resetbyp(self):
		if self.can_bypass():
			self.write_aa55xx(CONV_90, addr=0) + prepare_cart(0, 0)
		return b""

	def flash_reset(self):
		self.write_aa55xx(CONV_F0)

	def flash_manufacturer(self):
		buf = prep_aa55xx(CONV_90, 10)
		tmp = self.read_cart(0x0, 1, pfx=buf)
		self.write_aa55xx(CONV_F0, 10)
		return conv_byt(tmp[0])

	def flash_devicecode(self):
		buf = prep_aa55xx(CONV_90)
		tmp = self.read_cart(0x1, 1, pfx=buf)
		self.write_aa55xx(CONV_F0)
		return conv_byt(tmp[0])

	def flash_devicecodeex(self):
		buf = prep_aa55xx(CONV_90)
		tmp = self.read_cart(0x3, 1, pfx=buf)
		self.write_aa55xx(CONV_F0)
		return conv_byt(tmp[0])

	def flash_writebyte(self, addr: int, data: int):
		if data == 0xff: return b""
		# Full sequence only needed for devices without bypass
		if self.can_bypass():
			buf = prepare_cart(0x5555, CONV_A0)
		else:
			buf = prep_aa55xx(CONV_A0)
		buf += prepare_cart(addr, data)
		buf += prepare_wait(self.wait_cycles // (self.clock_divider + 1))
		return buf

	def flash_chiperase(self):
		buf = prep_aa55xx(CONV_80)
		self.write_aa55xx(CONV_10, pfx=buf)

	def flash_secerase(self, addr: int):
		buf = prep_aa55xx(CONV_80)
		self.write_aa55xx(CONV_30, addr=addr, pfx=buf)

	def write_out(self, buffer: bytes):
		self.write_to(buffer + b"\x87")

	def write_aa55xx(self, dat: int, waitcycles: int = 0, *, addr: int = 0x5555, pfx: bytes = b""):
		self.write_out(pfx + prep_aa55xx(dat, waitcycles, addr=addr))

	def read_cart(self, addr: int, n_bytes: int, *, pfx: bytes = b""):
		# Read bytes from the cart
		if n_bytes <= 0: return b""

		# Prepare the address
		addr <<= 4

		buffer = bytearray(
			b"\x35"  # Command
			b"\3"  # Anz. Bytes
			b"\0"
			# Placeholder for address
			b"\0\0\0\0"
		)
		size_per_req = len(buffer)
		buffer *= n_bytes
		for pos in range(3, len(buffer), size_per_req):
			# Layout:
			# xAAA AAAA AAAA AAAA AAAA xCxD DDDD DDDx
			buffer[pos:pos + 3] = addr.to_bytes(3, "big")
			addr += 0x10

		# Send all bytes
		self.write_out(pfx + buffer)

		# wait for data to become available
		want_bytes = n_bytes * 4
		self.wait_for(want_bytes)

		# read the input queue
		dat_buffer = self.read_from(want_bytes)

		# Post processing of data
		return bytes(
			((x & 1) << 7) | (y >> 1)
			for x, y in zip(
				islice(dat_buffer, 2, None, 4),
				islice(dat_buffer, 3, None, 4)
			)
		)
	
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

def prepare_cart(addr: int, dat: int):
	assert 0 <= dat <= 0xff
	return bytes([
		# Send 4 Bytes
		0x11, 0x03, 0x00,

		# Layout:
		# xAAA AAAA AAAA AAAA AAAA xCxD DDDD DDDx
		(addr >> 12) & 0xff,
		(addr >> 4) & 0xff,
		((addr << 4) & 0xf0) | 0x4 | (dat >> 7),
		(dat << 1) & 0xfe,
	])

def prepare_wait(waitcycles: int):
	# Make sure CS and other lines are low (dont leave programming mode)
	assert 0 <= waitcycles <= 0xff
	return bytes([
		0x80, 0x00, 0x2b,

		0x8f,
		4 * waitcycles - 1,
		0x00
	])

def prep_aa55xx(dat: int, waitcycles: int = 0, *, addr: int = 0x5555):
	prep_dat = prepare_cart(addr, dat)
	if waitcycles:
		if waitcycles == 10:
			return BUFF_AA55_10 + prep_dat + WAIT_10
		wb = prepare_wait(waitcycles)
		return PREP_AA + wb + PREP_55 + wb + prep_dat + wb
	return BUFF_AA55_0 + prep_dat

ON_0 = 1 << 0
ON_1 = 1 << 1
ON_2 = 1 << 2
ON_3 = 1 << 3
ON_4 = 1 << 4
ON_5 = 1 << 5
ON_6 = 1 << 6
ON_7 = 1 << 7

def conv_byt(byt):
	bret = 0
	if byt & ON_0: bret |= ON_7
	if byt & ON_1: bret |= ON_5
	if byt & ON_2: bret |= ON_3
	if byt & ON_3: bret |= ON_1
	if byt & ON_4: bret |= ON_0
	if byt & ON_5: bret |= ON_2
	if byt & ON_6: bret |= ON_4
	if byt & ON_7: bret |= ON_6
	return bret

def conv_byt_back(byt):
	bret = 0
	if byt & ON_7: bret |= ON_0
	if byt & ON_5: bret |= ON_1
	if byt & ON_3: bret |= ON_2
	if byt & ON_1: bret |= ON_3
	if byt & ON_0: bret |= ON_4
	if byt & ON_2: bret |= ON_5
	if byt & ON_4: bret |= ON_6
	if byt & ON_6: bret |= ON_7
	return bret

# Pre-compute typical commands to write_cart
CONV_10 = conv_byt(0x10)
CONV_20 = conv_byt(0x20)
CONV_30 = conv_byt(0x30)
CONV_55 = conv_byt(0x55)
CONV_80 = conv_byt(0x80)
CONV_90 = conv_byt(0x90)
CONV_A0 = conv_byt(0xa0)
CONV_AA = conv_byt(0xaa)
CONV_F0 = conv_byt(0xf0)

WAIT_10 = prepare_wait(10)
PREP_AA = prepare_cart(0x5555, CONV_AA)
PREP_55 = prepare_cart(0x2AAA, CONV_55)

BUFF_AA55_0 = PREP_AA + PREP_55
BUFF_AA55_10 = PREP_AA + WAIT_10 + PREP_55 + WAIT_10
