# <str name=help.topic.basics.title/>

In this section you will learn about what hardware is available for the Pokémon mini, how they're used, and how to use this software to interact with them, if possible.

## ROMs and other files

A ROM, short for Read Only Memory, is a copy of the contents of an official game cartridge. The game cartridges use a ROM chip inside in order to store the game code and resources (but not the save data, it's read-only!) which gives them the name. However, when we use this term, we're not talking about the chip but rather the copy of those contents. It may also refer to unofficial software as well, so long as it's able to run on the console if provided to said console.

ROM files for the Pokémon mini use the extension `.min` and save files use the extension `.eep`. The PokeMini emulator also has `.minc` files which provide color information, but they're not useful for pm2hw, or the Pokémon mini hardware in general.

`.min` files are 512 KiB and `.eep` files are 8 KiB (containing 6 save slots).

Remember: It may or may not be legal to backup or restore ROMs of copyrighted games in your country, but it is always illegal to share them with others or receive them from others. Please consult your country's copyright laws and international agreements it has signed or seek counsel from a copyright lawyer in order to be familiar with your rights.

## Linkers

Linkers (aka flashers, programmers, or proggers) sit in the middle between your computer and your flash cart. While some systems may not require linkers, all released flash carts for the PM do.

## Flash carts

Flash cartridges (aka flash cards) are devices which replicate the functionality of an official game cartridge, at least from the perspective of the console it runs on. In order to transfer a game, to the cart we usually use what's called a linker. All of the PM's flash carts have a specific linker which only works with that flash cart.

The only carts mentioned here are ones people could actually buy.

The contents of this section is largely based on [this document](https://www.pokemon-mini.net/flash-carts/).

### DITTO mini (rev 3.0)

DITTO mini is currently the only flash cart still in production. Buy it from [here](http://dittomini.com/). You can write to and read from it with the DITTO mini Flasher, purchasable at the same link.

There is a 3D-printable case available [here](https://www.thingiverse.com/thing:3592237). A label for which is shipped with the flash cart.

#### Features and information

* Designed by zoranc, developed by Plamen.
* Sold for $90 (USD) as a set (cart/linker) or $50 for just the cart or linker.
* 2 MiB storage, capable of storing 3 official games with some space left over.
* Fits in an official case with no modification.
* Software can write to the card from within the PM, allowing backup and restoration of save files as well as dumping the BIOS.
* Official flashing tool is Ditto Flash.
* Must be used in a case, board will not make contact loose.

#### Support in pm2hw

Status: Good

Supports basic operations (read, write, erase).

#### Technical specifications

* Size: 2 MiB
* Theoretical flashing speeds: 30s (512 KiB), 2m (2 MiB)
* Flash memory: [SST39VF1681](http://ww1.microchip.com/downloads/en/devicedoc/25040a.pdf)
* Bridge chip: [XC9572XL-10VQ64C](https://www.xilinx.com/support/documentation/data_sheets/ds057.pdf)
* Linker: DITTO mini Flasher
  * Connector: USB 2.0 Micro-B
  * Chip: [FT2232D](http://www.ftdichip.com/Support/Documents/DataSheets/ICs/DS_FT2232D.pdf)

### PokeCard512 (rev 2.1)

Fan made sticker by palkone available [here](https://www.pokemon-mini.net/forum/viewtopic.php?f=11&t=1025).

#### Features and information

* Designed by Lupin.
* Sold for €35 for just the cart and €55 for the linker.
* 512 KiB storage, capable of storing 1 official game.
* Fits in an official case with some modification.
  * Requires a hole in the top for the connector and a cutout in the back for the flash memory chip.
* Software can write to the card from within the PM, allowing backup and restoration of save files as well as dumping the BIOS.
* Official flashing tool is PokeFlash.

#### Support in pm2hw

Status: Good

Supports basic operations (read, write, erase).

#### Technical specifications

* Size: 512 KiB
* Flash memory: [SST39VF040](https://ww1.microchip.com/downloads/en/DeviceDoc/20005023B.pdf)
* Bridge: [XC9572XL-10VQ64C](https://www.xilinx.com/support/documentation/data_sheets/ds057.pdf)
* Linker
  * Connector: USB 2.0 Mini-B
  * Chip: [FT2232HL](http://www.ftdichip.com/Support/Documents/DataSheets/ICs/DS_FT2232H.pdf)

#### Differences from rev 2

* The CPLD (bridge chip) is rotated with a different pin layout for PCB routing reasons.
* Card layout has a mounting position for both the old/long flash and new/short flash package.
* The programming connector now protrudes from the card.
* Debug pins on the back of the card for easier manufacturing / programming of CPLD.
* Slightly reduced component count on flasher cable, some layout optimizations (e.g. all small components are on the bottom now, only the USB connector and IC are on the top).

### PokeCard512 (rev 2)

Despite both being considered rev 2, there were two versions of this card. The differentiator is the code flashed onto the CPLD, which was updated on carts created after 2011-04-17.

The CPLD of the early versions can be updated by following the steps [here](http://mrblinky.net/pm/togepi/pokecard/index.htm). This will allow running software to write to the card, in order to back up the save data or dump the BIOS.

#### Features and information

* Designed by Lupin.
* 512 KiB storage, capable of storing 1 official game.
* Fits in an official case with some modification.
  * Requires a cutout in the back for the flash memory chip.
* Software can write to the card from within the PM, allowing backup and restoration of save files as well as dumping the BIOS.
  * Only for versions created after 2011-04-17 or early ones with an updated CPLD.
* Official flashing tool is PokeFlash.

#### Support in pm2hw

Status: untested
The code for revision 2.1 was taken from the PokeFlash source, so the code for interfacing with 2 should exist, but it may not be detected properly.

#### Technical specifications

* Size: 512 KiB
* Flash memory: [AT49BV040A-70TI](https://www.mouser.com/catalog/specsheets/atmel_AT49BV040A.pdf)
  * Possibly also [AM29LV040B](http://instrumentation.obs.carnegiescience.edu/ccd/parts/AM29LV040B.pdf)
* Bridge: [XC9572XL-10VQ64C](https://www.xilinx.com/support/documentation/data_sheets/ds057.pdf)
* Linker
  * Connector: USB 2.0 Mini-B
  * Chip: [FT2232HL](http://www.ftdichip.com/Support/Documents/DataSheets/ICs/DS_FT2232H.pdf)

### PokeCard512 (rev 1)

#### Features and information

* Designed by Lupin.
* Sold for €30 for just the cart.
* Software can**not** write to the card from within the PM.
* Official flashing tool is PokeUSB.

#### Support in pm2hw

Status: in development

#### Technical specifications

* Size: 512 KiB
* Flash memory: [AT49LV040-90TC](https://www.mouser.com/datasheet/2/268/Atmel_AT49BV040-1180265.pdf)
* Bridge: [XC9536XL-10VQ44C](https://www.xilinx.com/support/documentation/data_sheets/ds058.pdf)
* Linker: PokeUSB
  * Connector: USB 2.0(?) Type B
  * Chip: [ATMEGA162-16DIP](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-2513-8-bit-AVR-Microntroller-ATmega162_Datasheet.pdf)
* Linker: [PokeUSB 1.2](http://mrblinky.net/pm/PokeUSB/index.htm)
  * Connector: USB 2.0(?) Type B
  * Chip: [ATMEGA162-16PI](https://ww1.microchip.com/downloads/en/DeviceDoc/2466S.pdf)

### JustBurn's Flashcart

Did this not have a better name?

#### Features and information

* Designed by JustBurn.
* Sold for $40 (USD) for just the cart in 2004.
* Sold for $59/€49 for the cart and $69/€59 for the link.
  * $20/€15 discount on the linker for sending in a PM to be sacrificed.
* Software can**not** write to the card from within the PM.

#### Support in pm2hw

Status: unplanned (contact me if you have one)

#### Technical specifications

* Size: 512 KiB
* Bridge: XC9536(?)
* Linker
  * Connector: EPP-enabled LPT.
  * Chip: ???

## Pokémon Channel

Pokémon Channel was a GameCube game released worldwide which contained a built-in Pokémon mini emulator. The emulation quality is not great, but it's enough to play the official games and some homebrew. Through the use of an injector, one can play arbitrary PM ROMs on GameCube through the Pokémon Channel emulator.

### Features and information

* Divide by 0 exception flag not seen in hardware.
* TODO: broken features in the emulator.
* No infrared support obviously!

### Support in pm2hw

Status: no support

## Multicarts

Multicarts are a way of compiling multiple games into a single ROM along with a menu to select which game you want to play. Generally, official games will need to be patched in order to run properly from a multicart.
