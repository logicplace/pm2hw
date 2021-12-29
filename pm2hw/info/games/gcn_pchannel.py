# Any copyright is dedicated to the Public Domain.
# https://creativecommons.org/publicdomain/zero/1.0/

from .base import Game, ROM, Boxing, Status
from .pm_lunch import LunchTimeJP, LunchTimeEN1, LunchTimeEN2

""" Pokémon Channel """

Channel = Game(
	"Pokémon Channel",
	[
		ROM(
			Status.released,
			code=b"", internal="",  # Not PM
			crc32=0x0,
			size=0,
			languages=["ja"],
			boxings=[
				Boxing(
					"ポケモンチャンネル ～ピカチュウといっしょ！～",
					release="2003-07-18",
					serial="DL-DOL-GPAJ-JPN",
					barcode="4902370506617",
					contains=[
						LunchTimeJP,
						# TODO: PM ROMs
					],
					sales={"JPN": "5524円"}
				)
			]
		),
		ROM(
			Status.released,
			code=b"", internal="",  # Not PM
			crc32=0x0,
			size=0,
			languages=["en-US"],
			boxings=[
				Boxing(
					"Pokémon Channel",
					release="2003-12-01",
					serial="DL-DOL-GPAE-USA",
					barcode="04549696146600100",
					contains=[
						LunchTimeEN1,
						# TODO: PM ROMs
					],
					sales={"USA": ""}
				)
			]
		),
		ROM(
			Status.released,
			code=b"", internal="",  # Not PM
			crc32=0x0,
			size=0,
			languages=["en", "es-ES", "fr-FR", "de-DE", "it"],  # TODO: confirm if en is GB or US
			boxings=[
				Boxing(
					"Pokémon Channel",
					release="2004-04-01",  # Many say 2nd, official site says 1st
					serial="DL-DOL-GPAP-EUR",
					# Only manual scan I can find is French, not sure if it's in this box or a separate one
					barcode="045496391904",
					contains=[
						LunchTimeEN1,  # en
						LunchTimeEN2,  # other languages
						# TODO: PM ROMs
					],
					sales={"DEU": "", "ESP": "", "FRA": "", "GBR": "", "ITA": ""}
				)
				# MSRB in South Africa of R 399.00 (which ISO? probs EUR) - https://www.nag.co.za/wp-content/archives/2004/004NAG%20April%202004.pdf
			]
		),
		ROM(
			Status.released,
			code=b"", internal="",  # Not PM
			crc32=0x0,
			size=0,
			languages=["en"],  # Probably en-US
			boxings=[
				Boxing(
					"Pokémon Channel",
					release="2004-04",  # After the 16th according to news posts, tho Dolphin says the 1st
					serial="DL-DOL-GPAU-AUS",
					contains=[
						LunchTimeEN1,
						# TODO: PM ROMs
					],
					sales={"AUS": ""}
				)
			]
		)
	],
	developer="株式会社アムブレラ",  # Ambrella
	genre="Adventure",
)
