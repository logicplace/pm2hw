# Any copyright is dedicated to the Public Domain.
# https://creativecommons.org/publicdomain/zero/1.0/

from .base import ROM, Boxing, Game, GameMode, BoxType, Developer, Feature, Status, Version, FourMbit

RacePetit = Boxing(
	"ポケモンレースミニ",
	type=BoxType.virtual,
	icon="mini_race_icon.gif",
)

Race = Game(
	"Pokémon Race mini",
	[
		ROM(
			Status.released,
			code=b"MRCJ",
			internal="ﾎﾟｹﾓﾝﾚｰｽ",
			crc32=0x4433B736,
			size=FourMbit,
			versions=[
				Version("minlib", "1.34")
			],
			languages=["ja"],
			modes=[
				GameMode("ポケモン グランプリ", players=(1, 1)),
				GameMode("チャレンジ", players=(1, 1)),
				GameMode("タイムアタック", players=(1, 1)),
				GameMode("メタモン バトル", players=(2, 2)),  # passive
			],
			features=[Feature.rumble, Feature.infrared, Feature.clock, Feature.backup],
			save_slots=2,
			boxings=[
				Boxing(
					"ポケモンレースミニ",
					producer="Nintendo Co.,Ltd.",
					release="2002-07-19",
					serial="MIN-P-MRCJ (JPN)",
					barcode="4521329016566",
					box_languages=["ja"],
					manual_languages=["ja"],
					icon="mini_race_icon.gif",
					preview="mini_so_race.gif",
					sales={"JPN":"1200円"}
				)
			]
		),
		
		ROM(
			Status.released,
			code=b"MRCJ",
			internal="ﾎﾟｹﾓﾝﾚｰｽ",
			crc32=0x3388EDB3,
			size=FourMbit,
			versions=[
				Version("minlib", "1.34")
			],
			languages=["ja"],
			modes=[
				GameMode("ポケモン グランプリ", players=(1, 1)),
			],
			features=[Feature.rumble, Feature.clock, Feature.backup],
			save_slots=2,
			boxings=[RacePetit]
		)
	],
	developer=Developer.jupiter,
	genre="Racing",
)
