# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import argparse
from io import BytesIO
from time import time
from typing import List

from . import get_connected_linkers, logger, BaseFlashable
from .logger import log, error, exception, progress, verbose, LogRecord
from .locales import _, natural_size
from .exceptions import DeviceError

logger.view = "cli"
last_progress = time()

def some_progess_only(record: LogRecord):
	global last_progress
	if isinstance(record.msg, progress):
		now = time()
		if record.msg.is_complete() or record.msg.current == 0 or now - last_progress >= 10:
			record.created = record.msg.updated
			last_progress = now
			return True
		return False
	return True

logger.set_level(logger.INFO)
handler = logger.Handler(logger.NOTSET, handler=lambda m: sys.stderr.write(f"{m}\n"))
handler.add_filter(some_progess_only)
logger.add_handler(handler)

logger.nice_formatter.default_shortlevelname = {
	f"{logger.INFO}.LOG": "",
	f"{logger.INFO}.PROGRESS": "",
	str(logger.VERBOSE): "",
}
logger.nice_formatter.default_shortlevelname_format = "{}: "
handler.set_formatter(logger.nice_formatter)

parser = argparse.ArgumentParser("pm2hw", description=_("cli.description"))

group = parser.add_mutually_exclusive_group()
group.add_argument("-l", "--linker", metavar="name", dest="linker_global",
	help=_("cli.help.param.linker"))
group.add_argument("-a", "--all", action="store_true", dest="all_global",
	help=_("cli.help.param.all"))
parser.add_argument("-v", "--verbose", action="count", dest="verbose_global", default=0,
	help=_("cli.help.param.verbose"))
parser.add_argument("--profile", action="store_true", dest="profile_global",
	help=argparse.SUPPRESS)

def add_common_flags(cmd: argparse.ArgumentParser):
	group = cmd.add_mutually_exclusive_group()
	group.add_argument("-l", "--linker", help=argparse.SUPPRESS)
	group.add_argument("-a", "--all", action="store_true", help=argparse.SUPPRESS)
	cmd.add_argument("-v", "--verbose", action="count", default=0, help=argparse.SUPPRESS)
	cmd.add_argument("--profile", action="store_true", help=argparse.SUPPRESS)
	cmd.add_argument("-c", "--clock", type=int, metavar="div", default=1,
		help="cli.help.param.clock")

subparsers = parser.add_subparsers(dest="cmd", title="actions")

flash_cmd = subparsers.add_parser("flash", aliases=["f"],
	help=_("cli.help.command.flash"))
add_common_flags(flash_cmd)
# flash_cmd.add_argument("-m", "--multicart", metavar="id", default="",
# 	help=_("cli.help.param.flash.multicart"))
flash_cmd.add_argument("-E", "--no-erase", action="store_false", dest="erase",
	help=_("cli.help.param.flash.no-erase"))
flash_cmd.add_argument("-V", "--no-verify", action="store_false", dest="verify",
	help=_("cli.help.param.flash.no-verify"))
flash_cmd.add_argument("roms", metavar="file", # nargs=argparse.ONE_OR_MORE,
	help=_("cli.help.param.flash.roms"))

dump_cmd = subparsers.add_parser("dump", aliases=["d"],
	help=_("cli.help.command.dump"))
add_common_flags(dump_cmd)
# group = parser.add_mutually_exclusive_group()
# group.add_argument("-s", "--split-all", action="store_true",
# 	help=_("cli.help.param.dump.split-all"))
# group.add_argument("-S", "--split",
# 	help=_("cli.help.param.dump.split"))
dump_cmd.add_argument("-p", "--partial", metavar="{size,offset:size}",
	help=_("cli.help.param.dump.partial"))
dump_cmd.add_argument("dest", metavar="file", nargs="?", default="{i:02d}-{code}-{name}.min",
	help=_("cli.help.param.dump.dest"))

erase_cmd = subparsers.add_parser("erase", aliases=["e"],
	help=_("cli.help.command.erase"))
add_common_flags(erase_cmd)
erase_cmd.add_argument("-p", "--partial", metavar="{size,offset:size}",
	help=_("cli.help.param.erase.partial"))

# TODO: info-gathering command(s)

def connect(args):
	log(_("cli.connect.search"))
	linkers = get_connected_linkers()
	if not linkers:
		raise DeviceError(_("cli.connect.no-linkers"))
	elif len(linkers) > 1 and not args.all:
		valid_choices = ["a", "A"]
		print(_("cli.connect.select-linker.title"), file=sys.stderr)
		for i, l in enumerate(linkers):
			print(_("cli.connect.select-linker.option").format(i=i, name=l.name), file=sys.stderr)
			valid_choices.append(str(i))
		print(" a) " + _("cli.connect.select-linker.all"), file=sys.stderr)
		choice = ""
		while choice not in valid_choices:
			print(_("cli.connect.select-linker.prompt"), file=sys.stderr, end="")
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
		log(_("cli.connect.connected"), name=flashable.name)
		try:
			verbose(_("cli.connect.connected.details"),
				chip=flashable.chip, size=natural_size(flashable.memory))
		except AttributeError:
			pass

	return flashables, time()

def main(args):
	if args.verbose:
		logger.set_level([logger.VERBOSE, logger.DEBUG, logger.PROTOCOL][min(args.verbose - 1, 2)])

	if args.cmd in {"f", "flash"}:
		flashables, start = connect(args)
		log(_("cli.flash.intro"))
		if args.roms == "-":
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
						log(_("cli.flash.verify.intro"))
						if flashable.verify(f):
							log(_("cli.flash.verify.success"))
						else:
							log(_("cli.flash.verify.failure"))
		if len(flashables) > 1:
			log(_("cli.flash.complete"), secs=time() - start)
		return flashables
	elif args.cmd in {"d", "dump"}:
		flashables, start = connect(args)
		log(_("cli.dump.intro"))
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
			log(_("cli.dump.complete"), secs=time() - start)
		return flashables
	elif args.cmd in {"e", "erase"}:
		flashables, start = connect(args)
		log(_("cli.erase.intro"))
		for i, flashable in enumerate(flashables):
			# TODO: multithreaded, partial
			flashable.erase()
		if len(flashables) > 1:
			log(_("cli.erase.complete"), secs=time() - start)
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
		import cProfile
		from pstats import Stats

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
	error(_("cli.error.device"), errmsg=str(err))
	sys.exit(1)
except Exception as err:
	exception(_("cli.error.exception"), err)
	sys.exit(2)
