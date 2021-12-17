from io import BytesIO
import sys
import argparse
from time import time

import cProfile
from pstats import Stats
from typing import List

from . import get_connected_linkers, logger
from .base import BaseFlashable
from .logger import log, error, exception, progress, verbose, LogRecord
from .locales import natural_size
from .exceptions import DeviceError

def completed_progess_only(record: LogRecord):
	if isinstance(record.msg, progress):
		if record.msg.is_complete():
			record.msg.final_form = "  {1}"
			ct = record.created = record.msg.time
			record.msecs = (ct - int(ct)) * 1000
			return True
		elif record.msg.current == 0 and isinstance(record.msg.msg, progress.prefixed):
			record.msg.msg = f"  {record.msg.msg.prefix}"
			return True
		return False
	return True

logger.set_level(logger.INFO)
handler = logger.Handler(logger.INFO, handler=lambda m: sys.stderr.write(f"{m}\n"))
handler.add_filter(completed_progess_only)
logger.nice_formatter.default_shortlevelname = {
	f"{logger.INFO}.LOG": "",
	f"{logger.INFO}.PROGRESS": "",
}
default_shortlevelname_format = "{}: "
handler.set_formatter(logger.nice_formatter)
logger.add_handler(handler)

parser = argparse.ArgumentParser(
	"pm2hw",
	description="Flash Pokémon mini ROMs to any card.")

group = parser.add_mutually_exclusive_group()
group.add_argument("-l", "--linker", metavar="name", dest="linker_global",
	help="Specify a linker by name. Fail if that linker is not connected.")
group.add_argument("-a", "--all", action="store_true", dest="all_global",
	help="Perform the action against all connected linkers.")
parser.add_argument("-v", "--verbose", action="count", dest="verbose_global", default=0,
	help="Output verbose information.")
parser.add_argument("--profile", action="store_true", dest="profile_global",
	help=argparse.SUPPRESS)

def add_common_flags(cmd: argparse.ArgumentParser):
	group = cmd.add_mutually_exclusive_group()
	group.add_argument("-l", "--linker", help=argparse.SUPPRESS)
	group.add_argument("-a", "--all", action="store_true", help=argparse.SUPPRESS)
	cmd.add_argument("-v", "--verbose", action="count", default=0, help=argparse.SUPPRESS)
	cmd.add_argument("--profile", action="store_true", help=argparse.SUPPRESS)
	cmd.add_argument("-c", "--clock", type=int, metavar="div", default=1,
		help="Set clock divider (higher=slower). Valid value range depends on card.")

subparsers = parser.add_subparsers(dest="cmd", title="actions")

flash_cmd = subparsers.add_parser("flash", aliases=["f"], help="Flash to cart.")
add_common_flags(flash_cmd)
# flash_cmd.add_argument("-m", "--multicart", metavar="id", default="",
# 	help="Choose the multicart system to use when flashing multiple ROMs")
flash_cmd.add_argument("-E", "--no-erase", action="store_false", dest="erase",
	help="Don't erase the cart before flashing.")
flash_cmd.add_argument("-V", "--no-verify", action="store_false", dest="verify",
	help="Don't verify the contents after flashing.")
flash_cmd.add_argument("roms", metavar="file", # nargs=argparse.ONE_OR_MORE,
	help="Flash the given file or use - to read from stdin.")

dump_cmd = subparsers.add_parser("dump", aliases=["d"], help="Dump from cart.")
add_common_flags(dump_cmd)
# group = parser.add_mutually_exclusive_group()
# group.add_argument("-s", "--split-all", action="store_true",
# 	help="Split all the ROMs out of a multicart.")
# group.add_argument("-S", "--split",
# 	help="Select which ROMs to split out of a multicart. May be one of:\n"
# 	" * menu - Pick from an interactive menu.\n"
# 	" * all - Split out all the ROMs.\n"
# 	" * 1 - Pick the first only.\n"
# 	" * 1,2 - Pick the first and second.\n"
# 	" * 1-3 - Pick the first three.\n"
# 	" * HW - Pick only the Hello World demo (code)."
# )
dump_cmd.add_argument("-p", "--partial", metavar="{size,offset:size}",
	help="Extract only part of the ROM. Specify either just the size in bytes or"
	" specify the offset and size in bytes.")
dump_cmd.add_argument("dest", metavar="file", nargs="?", default="{i:02d}-{code}-{name}.min",
	help="Dump the contents of the card to the given filename or use - to pipe to stdout.\n"
	"The filename may be templated as a Python format string using the following variables:\n"
	" * i - Index of the linker (integer)\n"
	" * linker - Linker name\n"
	" * code - Four-character code in the ROM (ASCII)\n"
	" * name - Internal name in the ROM (SHIFT-JIS)\n"
	"By default uses the format: {i:02d}-{code}-{name}.min\n"
	"This would be rendered as, for example: 00-MPZE-Puzzle.min"
)

erase_cmd = subparsers.add_parser("erase", aliases=["e"], help="Erase a flash cart.")
add_common_flags(erase_cmd)
erase_cmd.add_argument("-p", "--partial", metavar="{size,offset:size}",
	help="Erase only part of the ROM. Specify either just the size in bytes or"
	" specify the offset and size in bytes.")

# # TODO: info-gathering command(s)

def connect(args):
	log("Searching for device...")
	logger.enable("verbose", update_logger=True)
	linkers = get_connected_linkers()
	if not linkers:
		raise DeviceError("No linkers connected!")
	elif len(linkers) > 1 and not args.all:
		valid_choices = ["a", "A"]
		print("Select a linker to connect to:", file=sys.stderr)
		for i, l in enumerate(linkers):
			print(f" {i}) {l.name}", file=sys.stderr)
			valid_choices.append(str(i))
		print(" a) All", file=sys.stderr)
		choice = ""
		while choice not in valid_choices:
			print("Selection: ", file=sys.stderr, end="")
			choice = input()

		try:
			c = int(choice)
			linkers = [linkers[c]]
		except ValueError:
			# Assume "all"
			pass

	flashables: List[BaseFlashable] = []
	for linker in linkers:
		flashable = linker.init()
		flashables.append(flashable)
		log("Connected! Discovered a {name}", name=flashable.name)
		try:
			verbose("  Specifically, a {chip} {size} card",
				chip=flashable.chip, size=natural_size(flashable.memory))
		except AttributeError:
			pass

	return flashables, time()

def main(args):
	if args.cmd in {"f", "flash"}:
		flashables, start = connect(args)
		log("Flashing...")
		data = BytesIO(sys.stdin.buffer.read())
		for flashable in flashables:
			# TODO: multithreaded
			if not args.erase:
				# Delete the erase method
				flashable.erase_data = lambda *a: None

			if args.roms == "-":
				flashable.flash(data)
			else:
				with open(args.roms, "rb") as f:
					flashable.flash(f)
					if args.verify:
						log("Verifying write...")
						if flashable.verify(f):
							log("...write ok")
						else:
							log("...write failed")
		if len(flashables) > 1:
			log("Flashing complete! Completed in {secs:.3f}", secs=time() - start)
		return flashables
	elif args.cmd in {"d", "dump"}:
		flashables, start = connect(args)
		log("Dumping...")
		for i, flashable in enumerate(flashables):
			# TODO: multithreaded, partial
			if args.dest == "-":
				flashable.dump(sys.stdout.buffer)
			else:
				kw = {"i": i, "linker": getattr(flashable, "linker", flashable).name}
				for search, key, addr, size, enc in [
					("{code", "code", 0x021ac, 4, "ascii"),
					("{name", "name", 0x021b0, 12, "shift-jis"),
				]:
					if search in args.dest:
						flashable.seek(addr)
						try:
							kw[key] = flashable.read(size).rstrip(b"\0").decode(enc)
						except UnicodeDecodeError:
							kw[key] = "x" * size
				with open(args.dest.format(**kw), "wb") as f:
					flashable.dump(f)
		if len(flashables) > 1:
			log("Dumping complete! Completed in {secs:.3f}", secs=time() - start)
		return flashables
	elif args.cmd in {"e", "erase"}:
		flashables, start = connect(args)
		log("Erasing...")
		for i, flashable in enumerate(flashables):
			# TODO: multithreaded, partial
			flashable.erase()
		if len(flashables) > 1:
			log("Erasing complete! Completed in {secs:.3f}", secs=time() - start)
		return flashables
	else:
		parser.print_help()

try:
	args = parser.parse_args()
	# Normalize globals
	args.all = args.all_global or args.all
	args.linker = args.linker_global or args.linker
	args.profile = args.profile_global or args.profile
	args.verbose += args.verbose_global

	if args.profile:
		with cProfile.Profile() as pr:
			flashables = main(args)
		if flashables:
			if len(flashables) == 1:
				classname = type(flashables[0]).__name__
				name = f"{classname}-{args.cmd}"
			else:
				name = f"multiple-linkers-{args.cmd}"
		else:
			name = "main"
		stats = Stats(pr)
		stats.strip_dirs()
		stats.sort_stats("time")
		stats.dump_stats(name + ".prof")
	else:
		main(args)
except DeviceError as err:
	error("A device error occurred: {errmsg}", errmsg=str(err))
	sys.exit(1)
except Exception as err:
	exception("An error occurred", err)
	sys.exit(2)
