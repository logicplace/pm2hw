import sys
import argparse
from time import time

import cProfile
from pstats import Stats

from . import get_connected_linkers, logger
from .logger import log, error, exception, progress
from .locales import natural_size
from .exceptions import DeviceError

def completed_progess_only(record):
	if isinstance(record.msg, progress):
		if record.msg.is_complete():
			record.msg.final_form = "{1}"
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
		logger.enable("verbose", update_logger=True)
		linkers = get_connected_linkers()
		if not linkers:
			raise DeviceError("No linkers connected!")
		linker = linkers[0]
		flashable = linker.init()
		try:
			log("Connected! Discovered a {chip} {size} card", chip=flashable.chip, size=natural_size(flashable.memory))
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
		log("Flashing complete! Completed in {secs:.3f}", secs=time() - start)
		return flashable
	elif args.dump:
		log("Dumping...")
		if args.dump == "-":
			flashable.dump(sys.stdout.buffer)
		else:
			with open(args.dump, "wb") as f:
				flashable.dump(f)
		log("Dump complete! Completed in {secs:.3f}", secs=time() - start)
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
