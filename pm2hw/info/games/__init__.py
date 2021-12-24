# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import binascii
from typing import BinaryIO, Dict, List, Tuple
from collections import defaultdict

from .base import Boxing, Game, ROM, Status
from .pm_race import Race
from .pm_zanycards import ZanyCards

# Pokémon mini games
games: List[Game] = [
	Race,
	ZanyCards,
	# TODO: double-check with old site
]

games_by_rom: Dict[Tuple[bytes, str], List[ROM]] = defaultdict(list)

for game in games:
	for rom in game.roms:
		games_by_rom[(rom.code, rom.internal)].append(rom)

# TODO: reform list to have (code, internal) lookup
# TODO: design and parse header that can be written to flash carts
# TODO: check for whether start contains BIOS or junk or header

def lookup_all(f: BinaryIO):
	f.seek(0x021ac)
	code = f.read(4)
	name = f.read(12).rstrip(b"\0").decode("shift-jis", errors="replace")
	# TODO: check for and use header if it exists

	infos = games_by_rom.get((code, name))

	if not infos:
		return [ROM(Status.unidentified, code, name)]

	return infos


def lookup(f: BinaryIO, check_crc: bool = False):
	infos = lookup_all(f)
	code = infos[0].code
	name = infos[0].internal

	if check_crc:
		f.seek(0x02100)
		crc = binascii.crc32(f.read())
		size = f.tell()
		for info in infos:
			if info.crc32 == crc:
				return info
		# Nothing matched
		return ROM(Status.unidentified, code, name, crc, size)

	# TODO: guess at likelihoods for name, or accept region or something

	return ROM(
		Status.unidentified, code, name, boxings=[
			Boxing(
				"potential versions (CRC not checked)",
				contains=[b for r in infos for b in r.boxings]
			)
		]
	)


def dump_info(f: BinaryIO):
	f.seek(0x02100)
	contents = f.read()
	info = {
		"code": contents[0xac:0xb0],
		"internal": contents[0xb0:0xbc].rstrip(b"\0").decode("shift-jis"),
		"crc32": binascii.crc32(contents),
	}

	idx = contents.find(b"MINLIB VERSION ")
	if idx >= 0:
		info["minlib"] = contents[idx+15:idx+19].decode("ascii")

	return info
