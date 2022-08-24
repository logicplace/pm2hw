# Contributing to pm2hw

## Building

```sh
# Install build deps
pipx install whey
pipx inject whey whey-mixin Babel
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

# Build exe
whey -b
```

## Style

No real style restrictions yet, might set up yapf rules later.

I prefer imports ordered by length over alphabet because it's more aesthetically pleasing to me. Standard internal, third-party, this-lib blocks for imports first. Then within those essentially `import x` types first then `from x import y` types where we sort by number of .s first (in from type) then the length of x (rather than the whole line) second, then alphabetical order of x if there's a length tie. This may change.

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

TODO
