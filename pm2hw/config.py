# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from locale import getdefaultlocale
from pathlib import Path
from configparser import ConfigParser

from . import __version__ as pm2hw_version

try:
	import appdirs
	config_dir = Path(appdirs.user_config_dir("pm2hw", False, roaming=False))
	log_dir = Path(appdirs.user_log_dir("pm2hw", None, pm2hw_version))
	resource_dir = Path(appdirs.user_data_dir("pm2hw", None))
except ImportError:
	# Portable version, use the same dir
	import sys
	base = Path(
		sys.executable
		if getattr(sys, "frozen", False) else
		sys.argv[0]
	).parent

	config_dir = base
	log_dir = base / "logs" / pm2hw_version
	resource_dir = base / "resources"


default_language = getdefaultlocale()[0]

def getstrlist(s: str):
	return [x.strip() for x in s.split(",") if x]

def getlines(s: str):
	return [x for x in s.lstrip("\n").split("\n") if x]

config = ConfigParser(
	{
		"language": default_language,
		"box-languages": ", ".join([default_language, "en", "jp", "fr", "de"]),
	},
	default_section="general",
	delimiters=("=",),
	comment_prefixes=("#",),
	interpolation=None,
	converters={
		"strlist": getstrlist,
		"lines": getlines,
	}
)

config_file = os.path.join(config_dir, "pm2hw.cfg")

def reload():
	config.clear()
	try:
		with open(config_file, "rt", encoding="UTF-8") as f:
			config.read_file(f)
	except FileNotFoundError:
		pass

	config.setdefault("CLI", {})
	config.setdefault("GUI", {})
reload()

def save():
	os.makedirs(config_dir, exist_ok=True)
	with open(config_file, "wt", encoding="UTF-8") as f:
		config.write(f, space_around_delimiters=True)
