# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import argparse
from io import BytesIO
from enum import Enum
from time import time
from typing import List

from . import get_connected_linkers, logger, BaseFlashable
from .info import games
from .info.games.base import ROM
from .config import config, save as save_config
from .logger import log, error, exception, progress, verbose, LogRecord
from .linkers import extra_options
from .locales import __ as _, natural_size, parse_natural_size
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
	return group

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

info_cmd = subparsers.add_parser("info", aliases=["i"],
	help=_("cli.help.command.info"))
group = add_common_flags(info_cmd)
group.add_argument("rom", metavar="file", nargs="?",
	help=_("cli.help.param.info.rom"))

config_cmd = subparsers.add_parser("config",
	help=_("cli.help.command.config"), add_help=False)
group = config_cmd.add_mutually_exclusive_group(required=True)
group.add_argument("-s", "--set", action="store_true",
	help=_("cli.help.param.config.set"))
group.add_argument("-g", "--get", action="store_true",
	help=_("cli.help.param.config.get"))
group.add_argument("-l", "--list", action="store_true",
	help=_("cli.help.param.config.list"))
group.add_argument("-h", "--help", action="store_true",
	help=_("cli.help.param.config.help"))
config_cmd.add_argument("settings", nargs="*",
	help=_("cli.help.param.config.settings"))

from .locales import _

def parse_partial(x):
	if ":" in x:
		offset, size = x.split(":", 1)
		return parse_natural_size(offset), parse_natural_size(size)
	else:
		return 0, parse_natural_size(x)


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

def _main(args):
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
			# TODO: multithreaded
			kwargs = {}
			if args.partial:
				kwargs["offset"], kwargs["size"] = parse_partial(args.partial)

			if args.dest == "-":
				flashable.dump(sys.stdout.buffer, **kwargs)
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
					flashable.dump(f, **kwargs)
		if len(flashables) > 1:
			log(_("cli.dump.complete"), secs=time() - start)
		return flashables
	elif args.cmd in {"e", "erase"}:
		flashables, start = connect(args)
		log(_("cli.erase.intro"))
		for i, flashable in enumerate(flashables):
			# TODO: multithreaded
			kwargs = {}
			if args.partial:
				kwargs["offset"], kwargs["size"] = parse_partial(args.partial)
			flashable.erase(**kwargs)
		if len(flashables) > 1:
			log(_("cli.erase.complete"), secs=time() - start)
		return flashables
	elif args.cmd in {"i", "info"}:
		def print_info_line(name, rhs):
			print(
				"{lhs}: {rhs}".format(
					lhs=(_)(name, key=f"info.rom.details.{name}"),
					rhs=rhs
				)
			)

		def rhs(value, pfx):
			if isinstance(value, Enum):
				return (_)(value.value, key=f"{pfx}.{value.name}")
			return (_)(value, key=f"{pfx}.{value}")

		def print_info(info: ROM):
			print_info_line("code", info.acode)
			print_info_line("internal", info.internal)
			if info.game:
				if info.game.developer:
					print_info_line("developer", rhs(info.game.developer, "game.developer"))
				if info.game.genre:
					print_info_line("genre", rhs(info.game.genre, "game.genre"))
			if info.size:
				print_info_line("size", natural_size(info.size, "bits"))
			if info.modes:
				print_info_line("players", "{}~{}".format(*info.players))
				# TODO: detailed play mode info
			if info.features:
				# TODO: localized lists
				print_info_line("features", ", ".join(
					rhs(x, "info.rom.details.features")
					for x in info.features
				))
			if info.save_slots:
				print_info_line("save slots", str(info.save_slots))
			for version in info.versions:
				print_info_line(version.of, version.number)
			if info.crc32 >= 0:
				print_info_line("crc32", f"{info.crc32:08x}")
			# TODO: select release based on config

		if args.rom:
			with open(args.rom, "rb") as f:
				info = games.lookup(f, check_crc=True)
				print_info(info)
		else:
			flashables, start = connect(args)
			for f in flashables:
				info = games.lookup(f)
				print_info(info)
	elif args.cmd == "config":
		x: str
		if args.set:
			for x in args.settings:
				if "=" in x:
					attr, value = x.split("=")
					if attr in {"language", "box-languages"}:
						# TODO: validate
						config.set("general", attr, value)
					elif "." in attr:
						cat, name = attr.split(".", 1)
						fmt = extra_options.get(cat, {}).get(name)
						ok, expected = False, ""
						if fmt is not None:
							# Linker option
							typing = fmt[2]
							if typing is int:
								try:
									int(value)
									ok = True
								except ValueError:
									expected="int"
							elif typing is bool:
								ok = value in config.BOOLEAN_STATES
								expected = "boolean"
							elif typing is str:
								ok = True

						if ok:
							config.set(cat, name, value)
						elif expected:
							print(_("cli.config.setting.set.bad-value").format(setting=x, expected=expected))
						else:
							print(_("cli.config.setting.unknown").format(setting=x))
					else:
						print(_("cli.config.setting.unknown").format(setting=x))
				else:
					print(_("cli.config.setting.set.bad-format").format(setting=x))
			save_config()
		elif args.get:
			for x in args.settings:
				if x in {"language", "box-languages"}:
					print(f"{x}:", config.get("general", x))
				elif "." in x:
					cat, name = x.split(".", 1)
					if name in extra_options.get(cat, {}):
						# Linker option
						print(f"{x}:", config.get(cat, name))
					else:
						print(_("cli.config.setting.unknown").format(setting=x))
				else:
					print(_("cli.config.setting.unknown").format(setting=x))
		elif args.list:
			for x in ["language", "box-languages"]:
				print(f"{x}:", config.get("CLI", x))
			for ln, opts in extra_options.items():
				for opt, fmt in opts.items():
					default = fmt[3]
					print(f"{ln}.{opt}:", config.get(ln, opt, fallback=default))
		elif args.help:
			if args.settings:
				for x in args.settings:
					if x in {"language", "box-languages"}:
						print(f"{x}:", (_)(f"cli.config.setting.help.{x}"))
					elif "." in x:
						cat, name = x.split(".", 1)
						fmt = extra_options.get(cat, {}).get(name)
						if fmt is not None:
							# Linker option
							desc, default = fmt[1::2]
							print(f"{x}:", desc, f"(Default: {default})")
						else:
							print(_("cli.config.setting.unknown").format(setting=x))
					else:
						print(_("cli.config.setting.unknown").format(setting=x))
			else:
				config_cmd.print_help()
	else:
		parser.print_help()


def main():
	try:
		args = parser.parse_args()
		# Normalize globals
		args.all = args.all_global or getattr(args, "all", False)
		args.linker = args.linker_global or getattr(args, "linker", False)
		args.profile = args.profile_global or getattr(args, "profile", False)
		args.verbose = args.verbose_global + getattr(args, "verbose", 0)

		if args.profile:	
			import cProfile
			from pstats import Stats

			with cProfile.Profile() as pr:
				flashables = _main(args)
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
			_main(args)
		return 0
	except DeviceError as err:
		error(_("cli.error.device"), errmsg=str(err))
		return 1
	except Exception as err:
		exception(_("cli.error.exception"), err)
		return 2


if __name__ == "__main__":
	sys.exit(main())
