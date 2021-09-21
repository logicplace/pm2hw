# pm2hw

A flasher for all Pokemon mini Flash Cards (that I can actually test).

This is a work in progress, Ditto support is a bit slow and PokeUSB will come soon.

## Installation

TODO

## Usage

```sh
python -m pm2hw --help
```

## Comparison

All pm2hw tests run on Python 3.9.6

### PokeCard 512 v2

| Utility           | Read   | Write  |
| ----------------- | ------:| ------:|
| PokeFlash (Win10) | 1.883s | 4.509s |
| pm2hw (Win10)     | 2.529s | 6.031s |

### Ditto mini

| Utility           | Read    | Write    |
| ----------------- | -------:| --------:|
| pm2hw (Win10)     | 33.732s | 191.411s |
