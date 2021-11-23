from io import BufferedIOBase, BytesIO
from os import SEEK_SET, SEEK_END
import sys
from time import sleep, time
from typing import Any, BinaryIO, Callable, ClassVar, Dict, Iterable, Optional, Protocol, Sequence, Tuple, Type, Union, cast

import usb
from ftd2xx import FTD2XX

from .logger import verbose, warn, protocol, protocol_data
from .exceptions import clarify, DeviceError

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

class Handle(Protocol):
	def read(self, size: int) -> bytes:
		...

	def write(self, data: bytes) -> Any:
		...

	def close(self):
		...

class UsbDevice:
	def __init__(self, device: usb.core.Device):
		self.device = device

	def setup(self, *, configuration=None, interface=None, endpoint=None):
		try:
			self.device.set_configuration(configuration)
		except usb.core.USBError as err:
			if err.errno == 2:
				how = " with Zadig" if sys.platform.startswith("win") else ""
				raise DeviceError(
					"Could not connect to device, you may need"
					f" to install the libusbK driver{how}."
				)
			raise DeviceError(str(err))

		config = cast(usb.core.Configuration, self.device.get_active_configuration())

		if interface is not None:
			intf = config[interface]
			if endpoint is not None:
				self.endpoint = intf[endpoint]
			else:
				# Pick only endpoint
				eps = intf.endpoints()
				if len(eps) == 1:
					self.endpoint = eps[0]
				else:
					raise DeviceError("More than one endpoint found, must specify")
		else:
			for intf in config:
				ep = usb.util.find_descriptor(intf, bEndpointAddress=self.endpoint)
				if ep is not None:
					self.endpoint = cast(usb.core.Endpoint, ep)
				else:
					raise DeviceError("Endpoint address not found")

	def read(self, size: int):
		return self.endpoint.read(size)

	def write(self, data: bytes):
		return self.endpoint.write(data)

	def close(self):
		self.device.finalize()

	# Pass-throughs
	@property
	def manufacturer(self):
		return self.device.manufacturer

	@property
	def product(self):
		return self.device.product

LinkerID = Union[str, Tuple[int, int]]
linkers: Dict[LinkerID, type] = {}


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


def chunked(size, source):
    for i in range(0, len(source), size):
        yield source[i:i+size]


class BaseFlashable:
	def flash(self, stream: BinaryIO):
		""" Flash a ROM to the card """
		raise NotImplementedError

	def verify(self, stream: BinaryIO) -> bool:
		""" Verify the ROM on the card is correct """
		stream.seek(0, SEEK_SET)
		buff1 = stream.read()
		buff2 = BytesIO("\x00" * len(buff1))
		self.dump(buff2)
		return buff1 == buff2

	def dump(self, stream: BinaryIO, size: int = 0):
		""" Dump a ROM from the card """
		raise NotImplementedError

	def read(self, size: int) -> bytes:
		""" Read from the cursor location """
		raise NotImplementedError

	def write(self, data: bytes):
		""" Write to the cursor location """
		raise NotImplementedError

	def seek(self, offset: int, whence: int):
		""" Adjust cursor position """
		raise NotImplementedError


class BaseLinker(BaseFlashable):
	name: ClassVar[str]
	serial: str
	card: Optional["BaseCard"] = None
	clock_speed: int  # MHz

	reader: ClassVar[Type[BaseReader]] = BaseReader

	_buffering = False

	def __init__(self, handle: Handle, **kwargs):
		self.handle = handle

	@classmethod
	def from_usb(cls, device: UsbDevice) -> "BaseLinker":
		raise NotImplementedError

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
		protocol_data("<", ret)
		return ret

	def write_out(self, data: bytes):
		""" Write bytes over the wire """
		protocol_data(">", data)
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

	def _get_wait(self, wait: int):
		prepare_wait = getattr(self, "prepare_wait", None)
		if wait and (not prepare_wait or wait >= 0.001 and not self._buffering):
			# Cannot buffer if there's no prepare_wait TODO: log warning (once)
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


class BaseCard(BaseFlashable):
	chip: str
	memory: int  # Size available in bytes
	block_size: int
	packet_size: ClassVar[int]

	def __init__(self, linker: BaseLinker):
		self.linker = linker

	# Top level methods
	def blocks(self, start: int = 0, size: int = 0):
		memory = self.memory
		block_size = self.block_size

		if not size:
			end = memory
		elif start + size > memory:
			warn("Requested to dump more than the available size, truncating request.")
			end = memory
		else:
			end = start + size

		for addr in range(start, end, block_size):
			yield addr, min(end - addr, block_size)

	def flash(self, stream: BinaryIO):
		""" Flash a ROM to the card """
		# Get file size
		stream.seek(0, SEEK_END)
		size = stream.tell()
		if (size > self.memory):
			raise DeviceError("The input file is too large! Max. size is {} KiB!".format(self.memory))
		stream.seek(0, SEEK_SET)

		# Chip erase or sector erase
		self.erase_data(0, size)

		# Programming
		for addr, s in self.blocks(0, size):
			self.write_data(addr, stream.read(s))

	def verify(self, stream: BinaryIO) -> bool:
		""" Verify the ROM on the card is correct """
		stream.seek(0, SEEK_SET)
		block_size = self.block_size
		read = block_size
		bads = []
		while read == block_size:
			addr = stream.tell()
			orig = stream.read(block_size)
			read = len(orig)
			dump = self.read_data(addr, read)
			if orig != dump:
				count = len([i for i, (o, d) in enumerate(zip(orig, dump)) if o != d])
				bads.append(count)

		if any(bads):
			verbose("Verification failed with bad bytes in the following blocks:")
			for i, c in enumerate(bads):
				verbose("  Block {block}: {count}", block=i, count=c)
			return False
		return True

	def dump(self, stream: BinaryIO, size: int = 0):
		""" Dump a ROM from the card """
		for addr, s in self.blocks(0, size):
			stream.write(self.read_data(addr, s))

	# Methods you must implement
	def get_device_info(self) -> Tuple[int, int, Optional[int]]:
		""" Return the device manufacture, code, and possibly extended code """
		raise NotImplementedError

	def deconstruct_packet(self, packet: bytes) -> Tuple[int, int]:
		""" Return the addr, data from a raw packet """
		raise NotImplementedError

	def write_data(self, addr: int, data: bytes):
		""" Prepare the write command(s) for some data """
		raise NotImplementedError

	def read_data(self, addr: int, size: int) -> bytes:
		""" Prepare the read command(s) for some data """
		raise NotImplementedError

	def erase_data(self, addr: int, size: int):
		""" Prepare erase command(s) for some section """
		raise NotImplementedError


class BaseFtdiLinker(BaseLinker):
	handle: FTD2XX

	clock_divisor: int

	TSK_SK = 1 << 0
	TDI_DO = 1 << 1
	TDO_DI = 1 << 2
	TMS_CS = 1 << 3
	GPIOL0 = 1 << 4
	GPIOL1 = 1 << 5
	GPIOL2 = 1 << 6
	GPIOL3 = 1 << 7
	# GPIOH0~GPIOH7 would go here if supported

	# Note this currently only supports the low byte
	ftdi_port_state: int
	ftdi_port_direction: ClassVar[int] = TSK_SK | TDI_DO | TMS_CS

	def __init__(self, handle: FTD2XX, clock_divisor: Optional[int] = None, **kwargs):
		super().__init__(handle)
		self.serial = handle.getDeviceInfo()["serial"]
		if clock_divisor is not None:
			self.clock_divisor = clock_divisor

	def init(self):
		handle = self.handle
		protocol("* ==== FTDI device ====")

		with clarify("Unable to reset device"):
			handle.resetDevice()
			protocol("* reset device")

		# Clear the input buffer
		self.read_all()

		# Disable event and error characters
		with clarify("Unable to reset event/error chars"):
			handle.setChars(0, 0, 0, 0)
			protocol("* set EventChar=disabled ErrorChar=disabled")

		# Set USB request transfer size to 64KiB
		with clarify("Unable to set request transfer size"):
			handle.setUSBParameters(65536, 65536)
			protocol("* set RequestTransferSize In={} Out={} (bytes)", 65536, 65536)

		# Sets the read and write timeouts in 10 sec
		handle.setTimeouts(10000, 10000)
		protocol("* set TransferTimeout Read={} Write={} (ms)", 10000, 10000)

		# Setup latency
		with clarify("Set USB Device Latency Timer failed!"):
			handle.setLatencyTimer(255)
			protocol("* set LatencyTimer {} (ms)", 255)

		# Reset controller
		with clarify("Device reset failed!"):
			handle.setBitMode(0x0, 0x0)
			protocol("* set BitMode Mask=0 Mode=0 (reset)")

		# Set the port to MPSSE mode
		with clarify("Set to MPSSE mode failed!"):
			handle.setBitMode(0x0, 0x2)
			protocol("* set BitMode Mask=0 Mode=2 (MPSSE)")

		sleep(0.050)

		# Check sync...
		with clarify("Unable to synchronise the MPSSE write/read cycle!"):
			self.sync_to_mpsse()

		with clarify("Unable to configure MPSSE for SPI!"):
			self.configure_mpsse_for_spi()

	def sync_to_mpsse(self):
		# https://www.ftdichip.com/Support/Documents/AppNotes/AN_108_Command_Processor_for_MPSSE_and_MCU_Host_Bus_Emulation_Modes.pdf
		handle = self.handle

		# Clear input buffer
		self.read_all()

		# Enable loopback (TODO: pokecard test)
		self.write_out(b"\x84")
		assert handle.getQueueStatus() == 0

		# Put a bad command to the command processor (AA or AB)
		self.write_out(b"\xaa")

		# Wait for a response and confirm MPSSE says it's a bad command
		if self.wait_read(2) != b"\xfa\xaa":
			raise DeviceError("MPSSE Sync Failed")

	def configure_mpsse_for_spi(self):
		handle = self.handle

		# Ditto mini does not support these but the example suggests them
		# The example: https://www.ftdichip.com/Support/Documents/AppNotes/AN_114_FTDI_Hi_Speed_USB_To_SPI_Example.pdf
		# Only PokeCard supports 8A and Ditto mini doesn't even have adaptive clocking
		self.write_out(
			b"\x8a"  # Use 60MHz master clock (disable divide by 5)
			b"\x97"  # Turn off adaptive clocking
		# 	b"\x8d"  # Disable three phase clocking
			b"\x87"
		)
		sleep(0.010)

		# Check if the features were compatible with this chip
		tmp = self.read_all()
		slow_clock = tmp and b"\xfa\x8a" in tmp

		self.write_out(bytes([
			# Command to set directions of lower 8 pins and force value on bits set as output
			0x80,  # Command
			self.ftdi_port_state,
			self.ftdi_port_direction,
			# Set SK Clock divisor
			# TCK/SK period = master_clock  /  (( 1 + clock_divisor ) * 2)
			# master_clock is 12MHz normally, or 60MHz with "divide by 5" disabled
			# The FT2232D (Ditto mini flasher) is stuck with 12MHz
			# The FT2232H (PokeCard flasher) can disable divide by 5 and use 60MHz
			0x86,  # Command
			*self.clock_divisor.to_bytes(2, "little")
		]))
		self.clock_speed = (12 if slow_clock else 60) / (( 1 + self.clock_divisor) * 2)  # MHz

		# Disable loopback
		self.write_out(b"\x85")
		assert handle.getQueueStatus() == 0

	def port_state(self, set: int = -1, *, on: int = 0, off: int = 0):
		if set >= 0:
			new_state = set
		else:
			new_state = (self.ftdi_port_state & ~off) | on
		if new_state != self.ftdi_port_state:
			self.write_out(bytes([
				0x80,  # Command
				new_state,
				self.ftdi_port_direction
			]))
			self.ftdi_port_state = new_state

	def read_in(self, size: int) -> bytes:
		packet_size = self.card.packet_size
		data = self.wait_read(packet_size * size, exact=False)
		protocol_data("<", data)
		return bytes(
			self.card.deconstruct_packet(p)[1]
			for p in chunked(packet_size, data)
		)

	def read_data(self, data: BytesOrSequence, size: int, *, wait: int = 0, transform: Optional[Transform] = None) -> BaseReader:
		""" Write commands to the card and read the response """
		if not data:
			return self.reader(self, 0)

		if not wait:
			if not isinstance(data, bytes):
				data = b"".join(data)
			buffer = b"\x35" + (len(data) - 1).to_bytes(2, "little") + data + b"\x87"
			self._write_out_or_buffer(buffer)
		else:
			# Add waits between each read
			write_and_wait = self._get_wait(wait)
			if isinstance(data, bytes):
				buffer = b"\x35" + (len(data) - 1).to_bytes(2, "little") + data + b"\x87"
				write_and_wait(buffer)
			else:
				for d in data:
					buffer = b"\x35" + (len(d) - 1).to_bytes(2, "little") + d
					write_and_wait(buffer)
				self._write_out_or_buffer(b"\x87")
		return self.reader(self, size, transform)

	def read_all(self):
		""" Read the entire input buffer """
		size = self.handle.getQueueStatus()
		if size:
			ret = cast(bytes, self.handle.read(size))
			protocol_data("<", ret)
			return ret
		return b""

	def wait_read(self, size: int, secs: float = 20, exact: bool = True):
		handle = self.handle
		start = time()
		while handle.getQueueStatus() < size and time() - start < secs:
			pass
		queued = handle.getQueueStatus()
		if exact and queued > size:
			raise DeviceError(
				"Device queued an unexpected amount of data."
				" Wanted {} but queued {}".format(size, queued))
		if queued < size:
			raise DeviceError(
				"Device took too long to queue data."
				" Wanted {} but queued {}".format(size, queued))
		
		if queued:
			ret = cast(bytes, handle.read(size))
			protocol_data("<", ret)
			return ret
		return b""

	@property
	def vendor_id(self):
		return self.handle.id >> 16

	@property
	def product_id(self):
		return self.handle.id & 0xffff


class BaseSstCard(BaseCard):
	packet_size = 4
	erased = (0, 0)

	# method, size (bytes), speed (seconds)
	# Order by shortest size first
	erase_modes: Sequence[Tuple[Callable, int, float]]

	# Software Data Protection
	buffer_sdp: bytes = b""

	def erase_data(self, addr: int = 0, size: int = 0):
		if not size:
			size = self.memory
		if addr == 0 and size == self.memory:
			# Do a full chip erase.
			self.sst_chip_erase()
			self._wait_for_erased(0, 20)
		# elif addr % 0x04000 == 0 and size % 0x04000 == 0:
		# 	# Sector erase
		# 	for a in range(addr, addr + size, 0x04000):
		# 		self.sst_sector_erase(a)
		# 		self._wait_for_erased(a, 5)
		else:
			# Overwrite memory manually
			# onset .. sectors .. coda
			shortest = self.erase_modes[0][1]
			onset = addr % shortest
			if onset:
				onset = shortest - onset
			coda = (addr + size) % shortest

		# 	# Erase parts which are valid sectors
		# 	sectors_start = addr + onset
		# 	sectors_end = addr + size - coda
		# 	for a in range(sectors_start, sectors_end, 0x04000):
		# 		self.sst_sector_erase(a)
		# 		self._wait_for_erased(a, 5)

		# 	# Overwrite onset and coda (the bookends)
		# 	self.write_data(addr, b"\xff" * onset)
		# 	self.write_data(sectors_end, b"\xff" * coda)
		self.erased = (addr, addr + size)

	def _wait_for_erased(self, addr: int, secs: int):
		start = time()
		while self.read_data(addr, 1)[0] != 0xff and time() - start < 5:
			sleep(0.050)

	def write_data(self, addr: int, data: bytes):
		size = len(data)
		assert size <= self.block_size
		self.linker.start_buffering()
		for a, d in zip(range(addr, addr + size), data):
			self.sst_byte_program(a, d)
		self.linker.end_buffering()

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
