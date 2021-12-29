# Any copyright is dedicated to the Public Domain.
# https://creativecommons.org/publicdomain/zero/1.0/

from .base import ROM, Boxing, Game, GameMode, Feature, BoxType, Status, Version
from .gcn_pchannel import PokemonChannelJP

LunchTimeJP = Boxing(
	"カビゴンのランチタイム",
	type=BoxType.virtual
)

LunchTimeEN1 = Boxing(
	"Snorlax's Lunch Time",
	type=BoxType.virtual
)

LunchTimeEN2 = Boxing(
	"Lunch Time",
	type=BoxType.virtual
)

LunchTime = Game(
	"Snorlax's Lunch Time",
	[
		ROM(
			Status.released,
			code=b"MLTJ",
			internal="ﾗﾝﾁﾀｲﾑ",
			crc32=0xBD7D1FF3,
			versions=[
				Version("minlib", "1.34")
			],
			languages=["ja"],
			modes=[
				# TODO: check if mode is named in-game
				GameMode("all", players=(1, 1)),
			],
			# TODO: features, save_slots
			boxings=[LunchTimeJP]
		),
		ROM(
			Status.released,
			code=b"MLTE",
			internal="LUNCH TIME",
			crc32=0x05C9BAB3,
			versions=[
				Version("minlib", "1.34")
			],
			languages=["en"],
			modes=[
				# TODO: check if mode is named in-game
				GameMode("all", players=(1, 1)),
			],
			# TODO: features
			boxings=[LunchTimeEN1]
			# Regions: AUS, en_EU, USA
		),
		ROM(
			Status.released,
			code=b"MLTE",
			internal="LUNCH TIME",
			crc32=0xB93E34A5,
			versions=[
				Version("minlib", "1.34")
			],
			languages=["en"],
			modes=[
				# TODO: check if mode is named in-game
				GameMode("all", players=(1, 1)),
			],
			# TODO: features
			boxings=[LunchTimeEN2]
			# Regions: de_EU, fr_EU, it_EU, es_EU
		)
	],
	genre="Arcade",
)
