import sys
import argparse
from time import time

import cProfile
from pstats import Stats

from . import get_connected_linkers
from .logger import log, error, exception, enable, logger, nice_formatter, Handler, INFO
from .exceptions import DeviceError

# add_log_only_handler().set_handler(print)
handler = Handler(INFO, handler=lambda m: sys.stderr.write(f"{m}\n"))
handler.setFormatter(nice_formatter)
logger.addHandler(handler)

parser = argparse.ArgumentParser(
	"pm2hw",
	description="Flash Pokemon mini ROMs to any card.")

command = parser.add_mutually_exclusive_group()
command.add_argument("-f", "--flash", metavar="file",
	help="Flash the given file or use - to read from stdin")
command.add_argument("-d", "--dump", metavar="file",
	help="Dump the contents of the card to the given filename or use - to pipe to stdout")
parser.add_argument("-c", "--clock", type=int, metavar="div", default=1,
	help="Set clock divider (higher=slower); Valid value range depends on card")
parser.add_argument("-p", "--profile", action="store_true", help=argparse.SUPPRESS)

def main(args):
	if args.flash or args.dump:
		log("Searching for device...")
		enable("verbose")
		linkers = get_connected_linkers()
		if not linkers:
			raise DeviceError("No linkers connected!")
		linker = linkers[0]
		flashable = linker.init()
		try:
			log("Connected! Discovered a {chip} {size} KiB card", chip=flashable.chip, size=flashable.memory // 1024)
		except AttributeError:
			log("Connected!")

	start = time()
	if args.flash:
		log("Flashing...")
		if args.flash == "-":
			flashable.flash(sys.stdin.buffer)
		else:
			with open(args.flash, "rb") as f:
				flashable.flash(f)
				log("Verifying write...")
				if flashable.verify(f):
					log("...write ok")
				else:
					log("...write failed")
		log("Flashing complete! Completed in {:.3f}", time() - start)
		return flashable
	elif args.dump:
		log("Dumping...")
		if args.dump == "-":
			flashable.dump(sys.stdout.buffer)
		else:
			with open(args.dump, "wb") as f:
				flashable.dump(f)
		log("Dump complete! Completed in {:.3f}", time() - start)
		return flashable
	else:
		parser.print_help()

try:
	args = parser.parse_args()
	if args.profile:
		with cProfile.Profile() as pr:
			flashable = main(args)
		if flashable:
			name = flashable.__class__.__name__ + ("-flash" if args.flash else "-dump")
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
