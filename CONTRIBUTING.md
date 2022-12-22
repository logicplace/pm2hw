# Contributing to pm2hw

## Building

```sh
# Install build deps
pipx install whey
pipx inject whey whey-mixin Babel $(cat requirements.txt)
```

### pypi wheel

```sh
# via pipx
whey -ws
```

### Windows exe

```ps1
# Download and install UPX onto your path from https://github.com/upx/upx/releases/
# Install to a more permanent location and update your system environment variables
# to not have to re-add to path etc...
Invoke-WebRequest 'https://github.com/upx/upx/releases/download/v3.96/upx-3.96-win64.zip' -OutFile 'upx.zip'
Expand-Archive -Path 'upx.zip' -DestinationPath '.'
$env:PATH = "$env:PATH;$(pwd)\upx-3.96-win64"

# Additional deps
pipx inject whey PyInstaller

# Build exe
whey -b
```

## Style

No real style restrictions yet, might set up yapf rules later.

I prefer imports ordered by length over alphabet because it's more aesthetically pleasing to me. Standard internal, third-party, this-lib blocks for imports first. Then within those essentially `import x` types first then `from x import y` types where we sort by the length of of each dot-separate part of x (rather than the whole line) second, then alphabetical order of x if there's a length tie. This may change.

## Design

I've tried very hard to keep information (including methods) in owning classes. So that encapsulation that's imposed by the card's flash memory is in the card class and linker chip commands to pass that data are stored in the linker. This way, if a linker can be hacked to support other cards (which I would very much like to do) or after the new DITTO mini Flasher is released while using the same card, it _should_ be relatively sane to make the appropriate parts and integrate them seamlessly.

However, because of this, it can be very difficult to track program flow, because it bounces around the card and linker quite a bit. Ctrl+Click should work fine in VS Code so hopefully that helps. The debugger works as well.

The system works by first finding `BaseLinker`s which are connected to the computer, then asks those for the `BaseCard` connected to it. It technically does not have to be either, they just need to be a `BaseFlashable` which is welcome to return itself on init, for cases where they're the same thing or whatever.

The system calls the commands like `flash` and `dump` on the `BaseCard` returned from the init. These will call out to the linker as needed. Encapsulating write and read commands can take several back and forth between the two, but most other commands are simpler (erasing or etc).

### GUI

TODO

### Localization

TODO

### Game info database

First of all please be aware that all data in the info database is public domain and you must agree to release it that way. This is because while we're organizing the information, it is not information we've created in any real sense. The only copyrighted part is `base.py` which is the code that runs the DB.

At the top level you have a `Game` class which represents information which is relevant to all releases and versions of a game. It contains a default, English name, a list of ROMs, the original developer (company), and the genre. Other things that could show up here but don't yet, for example, would be individual developers or graphics artists for the original game.

Each `ROM` refers to a single unique (by bytes, ignoring < $2100) version of the game. Typically for official games this means different language releases. For homebrew, this could mean different release versions as development progresses. We'll discuss each part in the [ROM](#rom) section.

Inside of each ROM is a list of `Boxing`s which is likely the most confusing concept on its face. For physical releases, this refers to a certain box that was sold. Its uniqueness is determined by the box art/shape/etc, the manual(s) it comes with, and any other inserts. For Pokémon Channel games, this refers to the cart image(s) and instructions view, and can also refer to each Pokémon Channel release itself (boxings are recursive).

#### Game

* `en_name` - English name with proper casing. Same as you'll find in the English `.po` file. This is mainly supposed to be a fallback.
* `roms` - List of [ROMs](#rom) ordered by release date (earliest first).
* `developer` - The official registered name of the developing company in its original language. For official PM games, there's a `Developer` enum you can import.
* `genre` - Genre string from pokemon-mini.net No idea where these came from originally and I cannot find any official genre assignment anywhere. Still need to investigate in order to decide on normalized terms.

#### ROM

* `status` - The release status, from the `Status` enum.
  * `released` - officially published games
  * `unofficial` - for bootlegs or unofficial translations of official games
  * `unidentified` - a catchall no one will use
  * `hb_final` - for completed homebrew (no more releases planned) which the author reasonably considers a complete and playable game
  * `hb_demo` - all other homebrew.
* `code` - The (up to) four character code from the ROM. This is a bytes type, so if the code is less than four characters, you should still include the `\0`s
* `internal` - The SHIFT-JIS decoded internal name of the ROM. Up to 12 characters, null terminated (don't include the nulls).
* `crc32` - The CRC32 checksum from $2100 to the end of the file. If I can do some verified good dumps of the ROMs I may add another field for the $0000 ~ $2100 part.
* `size` - Total size in bytes
* `versions` - Versions of libraries used in the construction of this ROM. For official games this is (as far as we know) only MINLIB which you can specify like `Version("minlib", "1.35")` if the version is known. All official games use MINLIB, so if the version isn't in the DB then it's simply not known yet.
* `translator` - The name of the translator. For official translations this would probably be a company, but none are known (afaik). For unofficial translations this is just that person's credits. (TODO: Maybe this should be a list?)
* `languages` - Languages offered _in this specific ROM_ for ROMs with multi-language support. For most games it will be a list of one element. As per usual these are IETF language tags. Should be in the same order as the in-game selector (left to right, top to bottom).
* `modes` - These are the game modes listed on the back of the game boxes, for official games. Additionally, you can take them from in-game menus or something. They should be in the same order as they are on the back of the box.
  * Example: `GameMode("ポケモン グランプリ", players=(1, 1))` - "Grand Prix" mode from Race, for at least and at most 1 player.
* `features` - Features of the PM hardware which are used. You can use the `Feature` enum. They're shown on the official boxes as little icons, and should be listed in the same order as they are on the box. If these is no box (Snorlax's Lunch Time), just try to keep to whatever order is most common. (TODO: list that here, and respect it in the enum's order)
* `save_slots` - How many save slots the game uses. If a game does not use any, then leave it blank (defaults to 0). For most games which do use it this will be a 1, but it's a 2 for Pokémon Race mini.
* `boxings` - A list of collections this ROM was released in. See [Boxing](#boxing) below.

#### Boxing

* `name` - Name of the game as presented on the box
* `type` - Type of boxing from the `BoxType` (default is `physical`)
* `producer` - Official registered name of the producer _in this region_. Likely noted on the box itself.
* `release` - Initial release date as YYYY-MM-DD. Do not put any portion you're unsure about. If you only know the year (for example, 2001) then write `2001`. If you know the month is August but not the day, then write `2001-08` with no day. You may at a comment about any hearsay or research you've done. I encourage you to add convincing links (sale ads, magazines) as this value has proven very difficult to pin down accurately.
* `serial` - The serial code written on the top of the box.
* `barcode` - The barcode number as a string, no spacing.
* `box_languages` - List of languages present on the box, without being too pedantic. For example, you should probably only consider the primary language(s) used on the back to describe the content, and don't even think to consider ja-Latn just because it says "Pokémon". Order this by the descriptions on the back (take a look at the Tetris EU box if you don't know what I mean).
* `manual_languages` - For all releases I'm aware of, there are separate manuals per language, so there will be multiple in a multilingual box. So just consider this as one language tag per manual. No real order.
* `contains` - If this is a collection of other boxes (for instance it was officially sold as a bundle or it's just Pokémon Channel), you may link to other boxings in this list. Use the sanest order you can (for example, the order the games were listed in on the Pokémon Center website's sale page), and ideally leave a comment about it.
* `icon` - Icon filename for use in the game list in the GUI.
* `preview` - Preview banner filename for use in the info pane in the GUI.
* `sales` - Dict of ISO 3166 Alpha-3 country code to MSRP/initial sale price of the item, including the official currency marker and other punctuation in the correct position for that region. For example, for all JPN releases of the games this value is `1200円`
  * Note that the box and its contents must be _exactly the same_ for each country of sale to be included in this dict. If something is different, it needs to be a new boxing.
