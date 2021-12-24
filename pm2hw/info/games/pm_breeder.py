# Any copyright is dedicated to the Public Domain.
# https://creativecommons.org/publicdomain/zero/1.0/

from .base import ROM, Boxing, Game, GameMode, Developer, Feature, Status, Version

Race = Game(
	"Pokémon Breeder mini",
	[
		ROM(
			status=Status.released,
			code=b"MSDJ",
			internal="ｿﾀﾞﾃﾔｻﾝ",
			crc32=0x69A4314B,
			versions=[
				Version("minlib", "1.35")
			],
			languages=["ja"],
			modes=[
				# TODO: Not sure there are game modes...
				GameMode("all", players=(1, 1)),
			],
			features=[Feature.infrared, Feature.shock, Feature.rumble, Feature.backup, Feature.clock],
			save_slots=1,
			boxings=[
				Boxing(
					"ポケモンそだてやさんミニ",
					producer="Nintendo Co.,Ltd.",
					release="2002-12-14",
					serial="MIN-P-MSDJ (JPN)",
					# also reported as MIN-MSDJ-JPN
					# On box flap: GB-MIN-MSDJ\n-JPN
					# Manual: IM-MIN-MSDJ-JPN
					# Cart: L-MIN-MSDJ-JPN
					# Board: MIN-KCM1-01
					barcode="4521329019949",
					box_languages=["ja"],
					manual_languages=["ja"],
					icon="",  # TODO: Torchic, probably? on the swing or in the bed would be ideal
					preview="mini_so_sodate.gif",
					sales={"JPN":"1200円"}
				)
			]
		)
	],
	developer=Developer.jupiter,
	genre="Simulation",
)
