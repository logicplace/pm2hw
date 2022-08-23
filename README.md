# pm2hw

[![PyPI version](https://img.shields.io/pypi/v/pm2hw.svg)](https://pypi.python.org/pypi/pm2hw/)
[![PyPI status](https://img.shields.io/pypi/status/pm2hw.svg)](https://pypi.python.org/pypi/pm2hw/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pm2hw.svg)](https://pypi.python.org/pypi/pm2hw/)
![Platforms](https://img.shields.io/badge/platforms-windows%20linux%20macOS-green.svg)
[![GitHub license](https://img.shields.io/github/license/logicplace/pm2hw.svg)](https://github.com/logicplace/pm2hw/blob/master/LICENSE)
[![Discord](https://img.shields.io/discord/549770771963314216.svg?color=7289da&label=Pokemon-mini.net&logo=discord)](https://discord.gg/rAgt26Wknw)

A flasher for all Pokemon mini Flash Cards (that I can actually test).

This is a work in progress, PokeUSB will come soon.

## Installation

It would be best to install this via `pipx` rather than plain pip; but of course, both are possible.

### Windows

The system has been tested on Windows 10 with Python 3.9

1. Download and install the [FTD2XX drivers](https://ftdichip.com/drivers/d2xx-drivers/) for Windows (Desktop).
2. Install pipx if it's not installed: `py -m pip install pipx --user`  
   Note you will very likely need to add the folder to your PATH variable (it will warn you post-install).
3. Install pm2hw: `pipx install pm2hw`

### Linux/MacOS X

The system has not been tested on these OSes, but it should work.

1. Download and install the [FTD2XX drivers](https://ftdichip.com/drivers/d2xx-drivers/) for Linux or Mac OS X as appropriate.
2. Install pipx if it's not installed: `python3 -m pip install pipx --user`
3. Install pm2hw: `pipx install pm2hw`

## Usage

* CLI: `pm2hw --help`
* Open GUI: `pm2hw-gui`
  * Navigate to Help -> How to Use

## Comparison

All tests run on Python 3.10.5. Write times do not include verification (add the read time for that).

### PokeCard 512 v2

| Utility           | Read   | Write   |
| ----------------- | ------:| -------:|
| PokeFlash (Win10) | 1.344s | 10.109s |
| pm2hw (Win10)     | 1.481s | 14.771s |

### Ditto mini

| Utility             | Read 512 KiB | Read 2 MiB | Write 512 KiB | Write 2 MiB |
| ------------------- | ------------:| ----------:| -------------:| -----------:|
| Ditto Flash (Win10) | 7.610s       |            | 16.497s       |             |
| pm2hw (Win10)       | 7.370s       | 29.209s    | 18.706s       | 20.331s     |
