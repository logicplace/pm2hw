from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

FourMbit = 4 * 1024 * 1024 / 8

class Developer(Enum):
	denyusha = "電遊社"
	jupiter = "Jupiter Corporation"
	nintendo = "Nintendo"  # uhh is this really even true?

# TODO: Producers, translators

class Status(Enum):
	released = "released"
	unofficial = "unofficial"
	unidentified = "unidentified"
	hb_final = "homebrew final"
	hb_demo = "homebrew demo"

class Feature(Enum):
	rumble = "rumble"
	infrared = "infrared"
	shock = "shock"
	clock = "clock"
	backup = "save"

class BoxType(Enum):
	physical = "physical, individual box"
	virtual = "virtual collection of typical box components"
	abstract = "loose collection of some kind (e.g. bundles)"

@dataclass
class Game:
	en_name: str
	roms: List["ROM"]  # Sort by release date
	developer: Union[Developer, str] = ""
	genre: str = ""

	def __post_init__(self):
		for rom in self.roms:
			rom.game = self

@dataclass
class ROM:
	status: Status
	code: bytes
	internal: str
	crc32: int = -1
	size: int = 0  # bytes
	versions: List["Version"] = field(default_factory=list)
	translator: str = ""
	languages: List[str] = field(default_factory=list)

	modes: List["GameMode"] = field(default_factory=list)
	features: List[Feature] = field(default_factory=list)
	save_slots: int = 0

	# Sort by release date
	boxings: List["Boxing"] = field(default_factory=list)

	game: Optional[Game] = field(default=None, init=False, repr=False)

	def __post_init__(self):
		for box in self.boxings:
			box.rom = self
	
	@property
	def acode(self):
		return self.code.rstrip(b"\0").decode("ascii", errors="replace")

	@property
	def players(self):
		if not self.modes:
			return None
		mn, mx = self.modes[0].players
		for mode in self.modes[1:]:
			n, x = mode.players
			if n < mn:
				mn = n
			if x > mx:
				mx = x
		return mn, mx


class Version(NamedTuple):
	of: str
	number: str


class GameMode(NamedTuple):
	name: str
	players: Tuple[int, int]


@dataclass
class Boxing:
	name: str
	type: BoxType = BoxType.physical
	producer: str = ""
	release: str = ""  # YYYY[-MM[-DD]]
	serial: str = ""
	barcode: str = ""
	box_languages: List[str] = field(default_factory=list)
	manual_languages: List[str] = field(default_factory=list)
	contains: List["Boxing"] = field(default_factory=list)
	icon: str = ""
	preview: str = ""

	sales: Dict[str, str] = field(default_factory=dict)  # country -> msrp

	rom: ROM = field(init=False, repr=False)
