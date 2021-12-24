# Any copyright is dedicated to the Public Domain.
# https://creativecommons.org/publicdomain/zero/1.0/

from .base import ROM, Boxing, Game, GameMode, Developer, Feature, Status, FourMbit

ZanyCards = Game(
	"Pokémon Zany Cards",
	[
		ROM(
			Status.released,
			code=b"MACJ",
			internal="ｱﾆﾒｶｰﾄﾞ",
			crc32=0xA5668F32,
			size=FourMbit,
			languages=["ja"],
			modes=[
				GameMode("マッチ＆ゲット", players=(1, 5)),
				GameMode("ポケモンページワン", players=(1, 5)),
				GameMode("バトル10(テン)", players=(2, 2)),
				GameMode("フォーキングス", players=(1, 1))
			],
			features=[Feature.rumble, Feature.infrared],
			boxings=[
				Boxing(
					"ポケモンアニメカード大作戦",
					release="2001-12-04",  # Denyusha site says November
					serial="MIN-P-MACJ (JPN)",
					# also reported as MIN-MACJ-JPN
					# On box flap: GB-MIN-MACJ\n-JPN
					# Manual: IM-MIN-MACJ-JPN
					# Cart: L-MIN-MACJ-JPN
					barcode="4521329011158",
					box_languages=["ja"],
					manual_languages=["ja"],
					sales={"JPN":"1200円"}
				)
			]
		),
		ROM(
			Status.released,
			code=b"MACE",
			internal="Zany Cards",
			crc32=0x36D435E0,
			size=FourMbit,
			languages=["en"],
			modes=[
				GameMode("Wild Match", players=(1, 5)),
				GameMode("Special Seven", players=(1, 5)),
				GameMode("Card Duel", players=(2, 2)),
				GameMode("Four Kings", players=(1, 1))
			],
			features=[Feature.rumble, Feature.infrared],
			boxings=[
				Boxing(
					"Pokémon Zany Cards",
					producer="Nintendo of America, Inc.",
					release="2001-11-16",
					serial="MIN-P-MACE(USA)",
					# also reported as MIN-MACE-USA
					# On box flap: GB-MIN-MACE\n-USA
					# Manual: IM-MIN-MACE-USA
					# Cart: L-MIN-MACE-USA
					# Board: MIN-KCM1-01
					barcode="820650123498",
					box_languages=["en"],  
					manual_languages=["en"],
					sales={"USA": "$20.00", "CAN": ""}
				),
				Boxing(
					"Pokémon Zany Cards",
					producer="Nintendo",  # ?
					release="2001-11-16",  # ?
					serial="MIN-MACE-AUS",
					barcode="820650123498",  # ?
					sales={"AUS": ""}
				),
				Boxing(
					# https://www.nintendo.co.uk/Games/Pokemon-mini/Pokemon-Zany-Cards-276036.html
					"Pokémon Zany Cards",
					release="2002-03-15",  # ?
					# TODO: info
					sales={"GBR": "£15.00"}
				)
			]
		),
		ROM(
			Status.released,
			code=b"MACD",
			internal="Zany Cards",
			crc32=0x7CF22082,
			size=FourMbit,
			languages=["de"],
			modes=[
				GameMode("Kombo-King", players=(1, 5)),
				GameMode("Sieg Sieben", players=(1, 5)),
				GameMode("Duo-Duell", players=(2, 2)),
				GameMode("Königs-Solo", players=(1, 1))
			],
			features=[Feature.rumble, Feature.infrared],
			boxings=[
				Boxing(
					"Pokémon Zany Cards",
					release="2002",
					serial="MIN-MACD-NOE",
					barcode="045496461027",
					sales={"DEU":""}
				)
			]
		),
		ROM(
			Status.released,
			code=b"MACF",
			internal="Zany Cards",
			crc32=0x3FF65CD4,
			size=FourMbit,
			languages=["fr"],
			modes=[
				GameMode("Match Sauvage", players=(1, 5)),
				GameMode("Special Sept", players=(1, 5)),
				GameMode("Bataille", players=(2, 2)),
				GameMode("Carre de Rois", players=(1, 1))
			],
			features=[Feature.rumble, Feature.infrared],
			boxings=[
				Boxing(
					"Pokémon Zany Cards",
					release="2002",
					serial="MIN-P-MACF",
					barcode="045496461034",  # first digit may be wrong
					sales={"FRA":""}
				)
			]
		),
	],
	developer=Developer.denyusha,
	genre="strategy"
)
