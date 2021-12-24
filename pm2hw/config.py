# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from locale import getdefaultlocale
from configparser import ConfigParser

import appdirs

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
config_dir = appdirs.user_config_dir("pm2hw", False, roaming=False)
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
