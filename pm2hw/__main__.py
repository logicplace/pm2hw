import sys
import argparse
from time import time

import cProfile
from pstats import Stats

from . import get_connected_linkers
from .logger import log, error, enable
from .exceptions import DeviceError


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
		# TODO: discover card type
		log("Searching for device...")
		enable("verbose")
		linkers = get_connected_linkers()
		if not linkers:
			raise DeviceError("No linkers connected!")
		linker = linkers[0]
		linker.init()
		card = linker.detect_card()
		# card = PokeCard()
		log("Connected! Discovered a {chip} {size} KiB card", chip=card.chip, size=card.memory // 1024)

	start = time()
	if args.flash:
		log("Flashing...")
		if args.flash == "-":
			card.flash(sys.stdin.buffer)
		else:
			with open(args.flash, "rb") as f:
				card.flash(f)
				log("Verifying write...")
				if card.verify(f):
					log("...write ok")
				else:
					log("...write failed")
		log("Flashing complete! Completed in {:.3f}", time() - start)
		return card
	elif args.dump:
		log("Dumping...")
		if args.dump == "-":
			card.dump(sys.stdout.buffer)
		else:
			with open(args.dump, "wb") as f:
				card.dump(f)
		log("Dump complete! Completed in {:.3f}", time() - start)
		return card
	else:
		parser.print_help()

try:
	args = parser.parse_args()
	if args.profile:
		with cProfile.Profile() as pr:
			card = main(args)
		if card:
			name = card.__class__.__name__ + ("-flash" if args.flash else "-dump")
		else:
			name = "main"
		stats = Stats(pr)
		stats.strip_dirs()
		stats.sort_stats("time")
		stats.dump_stats(name + ".prof")
	else:
		main(args)
except DeviceError as err:
	error("An error occurred: {}", str(err))
	sys.exit(1)
